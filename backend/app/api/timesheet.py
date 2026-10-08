import io
import calendar
import urllib.parse
from datetime import date, datetime, time, timedelta
from typing import List, Optional


from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from urllib.parse import quote

from app.database import get_db
from app.core.security import allowed_department_id_set, get_current_user, require_admin
from app.models.user import User
from app.models.employee import Employee
from app.models.turnstile_event import TurnstileEvent
from app.models.work_schedule import WorkSchedule
from app.models.timesheet_record import TimesheetRecord
from app.models.department import Department
from app.models.document import Document
from app.models.time_code import TimeCode
from app.api.company_settings import get_overtime_threshold, apply_overtime_threshold
from app.schemas.timesheet import (
    TimesheetRecordResponse,
    TimesheetCalculateRequest,
    TimesheetCalculateResponse,
    TimesheetUpdateRequest,
    TimesheetReportResponse,
)

def get_all_department_ids(department_id: int, db: Session) -> List[int]:
    """Рекурсивно получает ID подразделения и всех его дочерних подразделений"""
    from app.models.department import Department
    
    result = [department_id]
    children = db.query(Department).filter(Department.parent_id == department_id).all()
    
    for child in children:
        result.extend(get_all_department_ids(child.id, db))
    
    return result

router = APIRouter(prefix="/api/timesheet", tags=["Timesheet"])

# Если время между входом и выходом больше этого значения (в часах) —
# считаем, что сотрудник забыл сделать отметку и смена помечается для проверки.
MAX_NORMAL_SHIFT_HOURS = 13

DEFAULT_LUNCH_MINUTES = 60
DEFAULT_NORM_HOURS = 8.0


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def parse_date(value: str, field_name: str) -> date:
    """Парсит дату в формате YYYY-MM-DD, иначе бросает HTTPException(400)."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=400,
            detail=f"Неверный формат {field_name}. Ожидается YYYY-MM-DD",
        )


def daterange(start: date, end: date):
    """Генератор дней от start до end включительно."""
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def schedule_lunch_minutes(schedule: Optional[WorkSchedule], day: date) -> int:
    """Обеденный перерыв по графику для конкретного дня недели."""
    if not schedule:
        return DEFAULT_LUNCH_MINUTES
    
    day_of_week = day.weekday()  # 0=Пн, 6=Вс
    
    day_schedule = next(
        (d for d in schedule.days if d.day_of_week == day_of_week),
        None
    )
    
    if day_schedule and day_schedule.is_day_off:
        return 0
    
    if day_schedule:
        return day_schedule.lunch_minutes
    
    return DEFAULT_LUNCH_MINUTES


def schedule_norm_hours(schedule: Optional[WorkSchedule], day: date) -> float:
    """Норма часов за день по графику."""
    if not schedule:
        return DEFAULT_NORM_HOURS
    
    day_of_week = day.weekday()
    
    day_schedule = next(
        (d for d in schedule.days if d.day_of_week == day_of_week),
        None
    )
    
    if not day_schedule or day_schedule.is_day_off:
        return 0.0
    
    if not day_schedule.start_time or not day_schedule.end_time:
        return 0.0
    
    from datetime import datetime, timedelta
    start_dt = datetime.combine(day, day_schedule.start_time)
    end_dt = datetime.combine(day, day_schedule.end_time)
    
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    
    gross = (end_dt - start_dt).total_seconds() / 3600
    net = gross - day_schedule.lunch_minutes / 60
    return round(max(net, 0.0), 2)


def calculate_day_record(events: List[TurnstileEvent], lunch_minutes: int):
    """Вычисляет first_in, last_out, fact_hours, needs_review, review_reason
    по списку событий проходной за один день."""

    in_events = [e for e in events if e.event_type == "in"]
    out_events = [e for e in events if e.event_type == "out"]

    first_in = min((e.datetime for e in in_events), default=None)
    last_out = max((e.datetime for e in out_events), default=None)

    fact_hours = 0.0
    needs_review = False
    review_reason = None

    if first_in and not last_out:
        needs_review = True
        review_reason = "Нет отметки выхода"
    elif last_out and not first_in:
        needs_review = True
        review_reason = "Нет отметки входа"
    elif first_in and last_out:
        if last_out < first_in:
            # Смена перешла через полночь
            worked_seconds = (last_out + timedelta(days=1) - first_in).total_seconds()
        else:
            worked_seconds = (last_out - first_in).total_seconds()

        fact_hours = worked_seconds / 3600

        if fact_hours > MAX_NORMAL_SHIFT_HOURS:
            needs_review = True
            review_reason = (
                f"Слишком длинная смена: {fact_hours:.2f} ч. "
                f"(возможно, пропущена отметка)"
            )
        else:
            needs_review = False
            review_reason = None

        fact_hours -= lunch_minutes / 60
        fact_hours = round(fact_hours, 2)
        if fact_hours < 0:
            fact_hours = 0.0

    return first_in, last_out, fact_hours, needs_review, review_reason


def is_vacation_document(active_doc, code: TimeCode) -> bool:
    """Документ-отпуск («О» / категория vacation).

    В отличие от командировки «К», отпуск НЕ блокирует учёт проходной:
    если сотрудник в период отпуска фактически приходил на работу, его
    фактические часы считаются по проходной и попадают в «Итого»
    (оплата отработанных часов), при этом код «О» сохраняется для
    начисления отпускных.
    """
    category = getattr(active_doc, "doc_type_category", None)
    if category == "vacation":
        return True
    if category in ("business_trip", "sick"):
        return False
    # Категории нет — ориентируемся на код/название документа
    candidates = (active_doc.code, active_doc.doc_type, code.code, code.name or "")
    return any(
        str(c).strip().upper() in ("О", "ОТ", "ВАКАНТА") or "отпуск" in str(c).lower()
        for c in candidates
        if c
    )


# ---------------------------------------------------------------------------
# Эндпоинты
# ---------------------------------------------------------------------------

@router.post("/calculate", response_model=TimesheetCalculateResponse)
def calculate_timesheet(
    payload: TimesheetCalculateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Рассчитывает табель на основе событий проходной за указанный период.

    Доступ только для Администратора (служебная операция).
    """

    date_from = parse_date(payload.date_from, "date_from")
    date_to = parse_date(payload.date_to, "date_to")

    if date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="date_from не может быть позже date_to",
        )

    # Определяем список сотрудников для расчёта
    if payload.employee_id is not None:
        employee = db.query(Employee).filter(Employee.id == payload.employee_id).first()
        if not employee:
            raise HTTPException(
                status_code=404,
                detail=f"Сотрудник с ID {payload.employee_id} не найден",
            )
        employees = [employee]
    else:
        employees = db.query(Employee).all()

    # ПРЕДЗАГРУЖАЕМ все активные документы за период (один запрос вместо N)
    active_docs = (
        db.query(Document)
        .filter(
            Document.is_active == True,  # noqa: E712
            Document.start_date <= date_to,
            Document.end_date >= date_from,
        )
        .all()
    )
    docs_by_employee: dict[int, list[Document]] = {}
    for doc in active_docs:
        docs_by_employee.setdefault(doc.employee_id, []).append(doc)

    # Справочник активных кодов часов
    time_codes = {
        c.code: c
        for c in db.query(TimeCode).filter(TimeCode.is_active == True).all()  # noqa: E712
    }

    total_days = 0
    records_created = 0
    records_updated = 0
    needs_review_count = 0
    documents_applied = 0

    # Общий порог переработки (минуты) из настроек системы — применяется ко всем графикам.
    # Превышение нормы <= порога не считается сверхурочным; 0 = считать любую переработку.
    ot_threshold = get_overtime_threshold(db)

    for employee in employees:
        schedule = employee.schedule  # может быть None
        employee_docs = docs_by_employee.get(employee.id, [])

        for day in daterange(date_from, date_to):
            total_days += 1

            # ПРАВИЛЬНОЕ МЕСТО: внутри цикла по дням!
            lunch_minutes = schedule_lunch_minutes(schedule, day)
            default_hours = schedule_norm_hours(schedule, day)

            # === УЧЁТ ДОКУМЕНТОВ («Документы и приказы») ===
            # Командировка «К» и другие документы-присутствия: день заполняется
            # ТОЛЬКО по документу (часы по графику), проходная игнорируется.
            # Отпуск «О»: если сотрудник фактически приходил на работу (есть
            # события проходной), считаются фактические часы по проходной +
            # сохраняется код «О» (для отпускных); без проходов — стандартное «О».
            active_doc = next(
                (d for d in employee_docs if d.start_date <= day <= d.end_date), None
            )
            doc_code_obj = None
            if active_doc is not None:
                doc_code_obj = time_codes.get(active_doc.code) or time_codes.get(active_doc.doc_type)

            # Исключение из правила «документ блокирует проходную»: отпуск.
            is_vacation_doc = (
                active_doc is not None
                and doc_code_obj is not None
                and is_vacation_document(active_doc, doc_code_obj)
            )

            # События проходной запрашиваем, если день НЕ закрыт документом
            # (или это отпуск — тогда проверяем, был ли сотрудник на работе)
            events = []
            if doc_code_obj is None or is_vacation_doc:
                day_start = datetime.combine(day, time.min)
                day_end = datetime.combine(day, time.max)
                events = (
                    db.query(TurnstileEvent)
                    .filter(
                        TurnstileEvent.employee_id == employee.id,
                        TurnstileEvent.datetime >= day_start,
                        TurnstileEvent.datetime <= day_end,
                    )
                    .order_by(TurnstileEvent.datetime)
                    .all()
                )

            # Отпуск + есть фактические приходы → считаем день по проходной,
            # но сохраняем код документа («О») для начисления отпускных.
            if is_vacation_doc and events:
                first_in, last_out, fact_hours, needs_review, review_reason = (
                    calculate_day_record(events, lunch_minutes)
                )
                if review_reason:
                    review_reason += " (работа в период отпуска)"
                else:
                    review_reason = "Работа в период отпуска"

                existing = (
                    db.query(TimesheetRecord)
                    .filter(
                        TimesheetRecord.employee_id == employee.id,
                        TimesheetRecord.date == day,
                    )
                    .first()
                )
                planned_hours = existing.planned_hours if existing else None
                overtime = apply_overtime_threshold(
                    fact_hours,
                    planned_hours if planned_hours is not None else default_hours,
                    ot_threshold,
                )

                if existing:
                    existing.first_in = first_in
                    existing.last_out = last_out
                    existing.fact_hours = fact_hours
                    existing.default_hours = default_hours
                    existing.overtime = overtime
                    existing.lunch_minutes = lunch_minutes
                    existing.needs_review = needs_review
                    existing.review_reason = review_reason
                    existing.document_code = doc_code_obj.code
                    records_updated += 1
                else:
                    db.add(TimesheetRecord(
                        employee_id=employee.id,
                        date=day,
                        first_in=first_in,
                        last_out=last_out,
                        fact_hours=fact_hours,
                        planned_hours=None,
                        default_hours=default_hours,
                        overtime=overtime,
                        lunch_minutes=lunch_minutes,
                        needs_review=needs_review,
                        review_reason=review_reason,
                        document_code=doc_code_obj.code,
                    ))
                    records_created += 1
                documents_applied += 1
                if needs_review:
                    needs_review_count += 1
                continue  # переходим к следующему дню

            if active_doc is not None and doc_code_obj is not None:
                code = doc_code_obj
                # Тип 1: отсутствие (hours_day=0, hours_night=0, без use_schedule_hours)
                #   → ставим код без часов, fact_hours = 0 (например «О», «Б»).
                # Тип 2: присутствие (use_schedule_hours или hours_day/hours_night > 0)
                #   → будний день: часы по графику; выходной: weekend_hours кода
                #   (например «К» — командировка). Проходная игнорируется.
                is_absence = (
                    not code.use_schedule_hours
                    and not (code.hours_day or 0)
                    and not (code.hours_night or 0)
                )

                if is_absence:
                    doc_fact_hours = 0.0
                elif code.use_schedule_hours:
                    if default_hours > 0:
                        doc_fact_hours = default_hours
                    else:
                        doc_fact_hours = float(code.weekend_hours or 0.0)
                else:
                    doc_fact_hours = round(
                        float(code.hours_day or 0.0) + float(code.hours_night or 0.0), 2
                    )

                existing = (
                    db.query(TimesheetRecord)
                    .filter(
                        TimesheetRecord.employee_id == employee.id,
                        TimesheetRecord.date == day,
                    )
                    .first()
                )
                planned_hours = existing.planned_hours if existing else None
                if is_absence:
                    overtime = 0.0
                elif code.use_schedule_hours and default_hours == 0:
                    # Работа в законный выходной — всё сверхурочно (порог не применяется)
                    overtime = round(doc_fact_hours, 2)
                elif planned_hours is not None:
                    overtime = apply_overtime_threshold(doc_fact_hours, planned_hours, ot_threshold)
                else:
                    overtime = apply_overtime_threshold(doc_fact_hours, default_hours, ot_threshold)

                if existing:
                    existing.first_in = None
                    existing.last_out = None
                    existing.fact_hours = doc_fact_hours
                    existing.default_hours = default_hours
                    existing.overtime = overtime
                    existing.lunch_minutes = lunch_minutes
                    existing.needs_review = False
                    existing.review_reason = f"Документ: {code.name}"
                    existing.document_code = code.code
                    records_updated += 1
                else:
                    db.add(TimesheetRecord(
                        employee_id=employee.id,
                        date=day,
                        first_in=None,
                        last_out=None,
                        fact_hours=doc_fact_hours,
                        planned_hours=None,
                        default_hours=default_hours,
                        overtime=overtime,
                        lunch_minutes=lunch_minutes,
                        needs_review=False,
                        review_reason=f"Документ: {code.name}",
                        document_code=code.code,
                    ))
                    records_created += 1
                documents_applied += 1
                continue  # переходим к следующему дню, проходная НЕ обрабатывается
            # Если код документа отсутствует/неактивен в справочнике —
            # падаем на обычную логику по проходной.

            if not events:
                # Нет событий за день — запись не создаётся
                continue

            first_in, last_out, fact_hours, needs_review, review_reason = calculate_day_record(
                events, lunch_minutes
            )

            existing = (
                db.query(TimesheetRecord)
                .filter(
                    TimesheetRecord.employee_id == employee.id,
                    TimesheetRecord.date == day,
                )
                .first()
            )

            # Плановые часы заполняются вручную начальником и не должны
            # сбрасываться при пересчёте по данным проходной.
            planned_hours = existing.planned_hours if existing else None

            if planned_hours is not None:
                overtime = apply_overtime_threshold(fact_hours, planned_hours, ot_threshold)
            else:
                # Предварительный расчёт сверхурочных по норме из графика
                # с учётом общего порога переработки из настроек
                overtime = apply_overtime_threshold(fact_hours, default_hours, ot_threshold)

            if existing:
                existing.first_in = first_in
                existing.last_out = last_out
                existing.fact_hours = fact_hours
                existing.default_hours = default_hours
                existing.overtime = overtime
                existing.lunch_minutes = lunch_minutes
                existing.needs_review = needs_review
                existing.review_reason = review_reason
                records_updated += 1
                if needs_review:
                    needs_review_count += 1
            else:
                new_record = TimesheetRecord(
                    employee_id=employee.id,
                    date=day,
                    first_in=first_in,
                    last_out=last_out,
                    fact_hours=fact_hours,
                    planned_hours=None,
                    default_hours=default_hours,
                    overtime=overtime,
                    lunch_minutes=lunch_minutes,
                    needs_review=needs_review,
                    review_reason=review_reason,
                )
                db.add(new_record)
                records_created += 1
                if needs_review:
                    needs_review_count += 1

    db.commit()

    return TimesheetCalculateResponse(
        total_days=total_days,
        employees_processed=len(employees),
        records_created=records_created,
        records_updated=records_updated,
        needs_review_count=needs_review_count,
        documents_applied=documents_applied,
    )


@router.get("", response_model=List[TimesheetRecordResponse])
def get_timesheet(
    employee_id: Optional[int] = Query(None, description="ID сотрудника"),
    date_from: Optional[str] = Query(None, description="Дата начала периода YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Дата конца периода YYYY-MM-DD"),
    needs_review: Optional[bool] = Query(None, description="Только записи, требующие проверки"),
    db: Session = Depends(get_db),
):
    """Получить список записей табеля с фильтрацией."""

    query = db.query(TimesheetRecord)

    if employee_id is not None:
        query = query.filter(TimesheetRecord.employee_id == employee_id)

    if date_from:
        query = query.filter(TimesheetRecord.date >= parse_date(date_from, "date_from"))

    if date_to:
        query = query.filter(TimesheetRecord.date <= parse_date(date_to, "date_to"))

    if needs_review is not None:
        query = query.filter(TimesheetRecord.needs_review == needs_review)

    records = query.order_by(TimesheetRecord.date, TimesheetRecord.employee_id).all()
    return records


@router.patch("/{record_id}", response_model=TimesheetRecordResponse)
def update_timesheet(
    record_id: int,
    payload: TimesheetUpdateRequest,
    db: Session = Depends(get_db),
):
    """Ручное заполнение плановых часов и снятие пометки о проверке."""

    record = db.query(TimesheetRecord).filter(TimesheetRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail=f"Запись табеля с ID {record_id} не найдена")

    if payload.planned_hours is not None:
        record.planned_hours = payload.planned_hours
        # Сверхурочные с учётом общего порога переработки из настроек
        ot_threshold = get_overtime_threshold(db)
        record.overtime = apply_overtime_threshold(record.fact_hours, payload.planned_hours, ot_threshold)

    if payload.needs_review is not None:
        record.needs_review = payload.needs_review

    if payload.review_reason is not None:
        record.review_reason = payload.review_reason

    db.commit()
    db.refresh(record)

    return record

# ============================================================================
# ЭНДПОИНТЫ ДЛЯ ОТЧЕТА ТАБЕЛЯ
# ============================================================================

from datetime import date
from calendar import monthrange
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


@router.get("/report")
def get_timesheet_report(
    month: int = Query(..., ge=1, le=12, description="Месяц (1-12)"),
    year: int = Query(..., ge=2020, description="Год"),
    department_id: Optional[int] = Query(None, description="ID подразделения"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Получить отчет табеля за месяц"""
    
    _, days_in_month = monthrange(year, month)
    
    # Получаем сотрудников
    query = db.query(Employee)
    allowed = allowed_department_id_set(user, db)
    if allowed is not None:
        # роль «Пользователь»: только сотрудники назначенных подразделений
        if not allowed:
            employees = []
        else:
            query = query.filter(Employee.department_id.in_(allowed))
            if department_id and int(department_id) not in allowed:
                raise HTTPException(
                    status_code=403,
                    detail="Нет прав на это подразделение (права выдаёт администратор)")
            if department_id:
                all_dept_ids = get_all_department_ids(department_id, db)
                query = query.filter(Employee.department_id.in_(all_dept_ids))
            employees = query.order_by(Employee.full_name).all()
    else:
        if department_id:
            all_dept_ids = get_all_department_ids(department_id, db)
            query = query.filter(Employee.department_id.in_(all_dept_ids))
        employees = query.order_by(Employee.full_name).all()
    
    
    employee_reports = []
    
    for idx, emp in enumerate(employees, start=1):
        # Получаем записи табеля за месяц
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1)
        else:
            month_end = date(year, month + 1, 1)
        
        records = db.query(TimesheetRecord).filter(
            TimesheetRecord.employee_id == emp.id,
            TimesheetRecord.date >= month_start,
            TimesheetRecord.date < month_end
        ).all()
        
        records_by_day = {record.date.day: record for record in records}
        
        days_data = {}
        total_hours = 0.0
        
        for day in range(1, days_in_month + 1):
            record = records_by_day.get(day)
            
            if record:
                if record.needs_review:
                    value = "О6"
                elif record.document_code and not (record.first_in or record.fact_hours):
                    # День заполнен по документу («Документы и приказы»):
                    # показываем код документа (например «К», «Б»), а для
                    # документов-присутствий с часами — код + часы. Проходная
                    # в такие дни не учитывается.
                    value = record.document_code
                    if record.fact_hours and record.fact_hours > 0:
                        if record.overtime and record.overtime > 0:
                            value = f"{record.document_code} ({round(record.overtime, 2)}с)"
                elif record.document_code and record.fact_hours:
                    # Отпуск + фактический приход: показываем фактические часы
                    # (попадают в «Итого»); код «О» сохраняется отдельно для tooltip.
                    if record.overtime and record.overtime > 0:
                        fact = round(record.fact_hours, 2)
                        overtime = round(record.overtime, 2)
                        value = f"{fact} ({overtime}с)"
                    else:
                        value = str(round(record.fact_hours, 2))
                elif record.overtime and record.overtime > 0:
                    # Формат: "10.25 (2.25с)" — фактические часы + сверхурочные в скобках
                    fact = round(record.fact_hours, 2)
                    overtime = round(record.overtime, 2)
                    value = f"{fact} ({overtime}с)"
                elif record.fact_hours > 0:
                    value = str(round(record.fact_hours, 2))
                else:
                    value = "в"
                
                days_data[str(day)] = {
                    "value": value,
                    "hours": record.fact_hours,
                    # Норма по графику (default_hours) — нужна фронтенду для
                    # подсветки «норма выполнена» (|факт − норма| ≤ допуска)
                    "default_hours": record.default_hours,
                    "needs_review": record.needs_review,
                    # Детали для tooltip на фронтенде: время входа/выхода, сверхурочные
                    "first_in": record.first_in.strftime("%H:%M") if record.first_in else None,
                    "last_out": record.last_out.strftime("%H:%M") if record.last_out else None,
                    "overtime": round(record.overtime, 2) if record.overtime else None,
                    "document_code": record.document_code,
                    "review_reason": record.review_reason,
                }
                
                if not record.needs_review:
                    total_hours += record.fact_hours
            else:
                days_data[str(day)] = {
                    "value": "в",
                    "hours": 0.0,
                    "default_hours": None,
                    "needs_review": False,
                    "first_in": None,
                    "last_out": None,
                    "overtime": None,
                    "document_code": None,
                    "review_reason": None,
                }
        
        # Получаем название подразделения
        dept_name = "-"
        if emp.department_id:
            dept = db.query(Department).filter(Department.id == emp.department_id).first()
            if dept:
                dept_name = dept.name
        
        employee_reports.append({
            "index": idx,
            "full_name": emp.full_name,
            "department": dept_name,
            "days": days_data,
            "total_hours": round(total_hours, 2)
        })
    
    return {
        "month": month,
        "year": year,
        "days_in_month": days_in_month,
        "employees": employee_reports
    }

@router.get("/report/excel")
def export_timesheet_excel(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2020),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Экспорт отчета табеля в Excel"""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import PatternFill, Font, Alignment
        import io
        from datetime import date
        from calendar import monthrange
        import urllib.parse
        
        _, days_in_month = monthrange(year, month)
        
        # Функция форматирования времени в ЧЧ:ММ (как в веб-версии)
        def format_time(decimal_hours):
            hours = int(decimal_hours)
            minutes = round((decimal_hours - hours) * 60)
            if minutes == 60:
                hours += 1
                minutes = 0
            return f"{hours}:{str(minutes).zfill(2)}"
        
        # Получаем сотрудников (та же логика, что в /report)
        query = db.query(Employee)
        allowed = allowed_department_id_set(user, db)
        if allowed is not None:
            if not allowed:
                employees = []
            else:
                query = query.filter(Employee.department_id.in_(allowed))
                if department_id and int(department_id) not in allowed:
                    raise HTTPException(status_code=403, detail="Нет прав на это подразделение")
                if department_id:
                    all_dept_ids = get_all_department_ids(department_id, db)
                    query = query.filter(Employee.department_id.in_(all_dept_ids))
                employees = query.order_by(Employee.full_name).all()
        else:
            if department_id:
                all_dept_ids = get_all_department_ids(department_id, db)
                query = query.filter(Employee.department_id.in_(all_dept_ids))
            employees = query.order_by(Employee.full_name).all()
        
        # Создаем Excel
        wb = Workbook()
        ws = wb.active
        ws.title = f"Табель {month}.{year}"

        # Стили
        header_fill = PatternFill(start_color="D3D3D3", end_color="D3D3D3", fill_type="solid")
        weekend_fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
        overtime_fill = PatternFill(start_color="FFF9C4", end_color="FFF9C4", fill_type="solid")
        review_fill = PatternFill(start_color="FFCDD2", end_color="FFCDD2", fill_type="solid")
        bold_font = Font(bold=True)
        center_align = Alignment(horizontal="center", vertical="center")

        # Заголовки
        headers = ["№", "Ф.И.О.", "Подразделение"]
        for day in range(1, days_in_month + 1):
            headers.append(str(day))
        headers.append("Итого часов")
        
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.fill = header_fill
            cell.font = bold_font
            cell.alignment = center_align

        # Данные
        for idx, emp in enumerate(employees, start=1):
            month_start = date(year, month, 1)
            if month == 12:
                month_end = date(year + 1, 1, 1)
            else:
                month_end = date(year, month + 1, 1)
            
            records = db.query(TimesheetRecord).filter(
                TimesheetRecord.employee_id == emp.id,
                TimesheetRecord.date >= month_start,
                TimesheetRecord.date < month_end
            ).all()
            
            records_by_day = {record.date.day: record for record in records}
            
            # Формируем строку
            row_num = idx + 1  # +1 потому что первая строка - заголовки
            ws.cell(row=row_num, column=1, value=idx).alignment = center_align
            ws.cell(row=row_num, column=2, value=emp.full_name)
            
            dept_name = emp.department.name if emp.department else "-"
            ws.cell(row=row_num, column=3, value=dept_name)
            
            total_hours = 0.0
            
            for day in range(1, days_in_month + 1):
                col_num = day + 3  # +3 потому что первые 3 колонки: №, ФИО, Подразделение
                record = records_by_day.get(day)
                
                cell = ws.cell(row=row_num, column=col_num)
                cell.alignment = center_align
                
                if record:
                    if record.needs_review:
                        value = "О6"
                        cell.fill = review_fill
                    elif record.document_code and not (record.first_in or record.fact_hours):
                        # День по документу: код («К», «Б», «О» без приходов). Для
                        # документов-присутствий часы идут по графику и
                        # учитываются в итоге; проходная игнорируется.
                        value = record.document_code
                        if record.fact_hours and record.fact_hours > 0:
                            total_hours += round(record.fact_hours, 2)
                            if record.overtime and record.overtime > 0:
                                value = (
                                    f"{record.document_code} "
                                    f"({format_time(round(record.overtime, 2))}с)"
                                )
                    elif record.document_code and record.fact_hours:
                        # Отпуск + фактический приход: показываем фактические
                        # часы (Ч:ММ), они учитываются в «Итого»; цвет — как у
                        # обычных рабочих ячеек. Код «О» виден в tooltip/данных.
                        fact = round(record.fact_hours, 2)
                        if record.overtime and record.overtime > 0:
                            value = f"{format_time(fact)} ({format_time(round(record.overtime, 2))}с)"
                            cell.fill = overtime_fill
                        else:
                            value = format_time(fact)
                        total_hours += fact
                    elif record.overtime and record.overtime > 0:
                        fact = round(record.fact_hours, 2)
                        overtime = round(record.overtime, 2)
                        value = f"{format_time(fact)} ({format_time(overtime)}с)"
                        cell.fill = overtime_fill
                        if not record.needs_review:
                            total_hours += fact
                    elif record.fact_hours > 0:
                        value = format_time(round(record.fact_hours, 2))
                        if not record.needs_review:
                            total_hours += record.fact_hours
                    else:
                        value = "в"
                else:
                    value = "в"
                
                # Подсветка выходных
                day_of_week = date(year, month, day).weekday()
                if day_of_week >= 5:  # Суббота или Воскресенье
                    if not cell.fill or cell.fill.start_color.rgb == "00000000":
                        cell.fill = weekend_fill
                
                cell.value = value
            
            # Итого часов
            total_cell = ws.cell(row=row_num, column=days_in_month + 4, value=round(total_hours, 2))
            total_cell.font = bold_font
            total_cell.alignment = center_align

        # Автоподбор ширины колонок
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value and len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 30)  # Максимум 30 символов
            ws.column_dimensions[column_letter].width = adjusted_width

        # Сохраняем в BytesIO
        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)

        month_names = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
                       "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        filename = f"Табель_{month_names[month]}_{year}.xlsx"
        safe_filename = urllib.parse.quote(filename)

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}"
            }
        )
        
    except Exception as e:
        import traceback
        print(f"Ошибка экспорта Excel: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Ошибка генерации Excel: {str(e)}")