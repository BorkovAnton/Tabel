"""Сводный отчёт по часам для роли «Отчёт».

Строки: ФИО / часы с табеля (TabelFill, итог за месяц) /
фактические часы по СКУД (timesheet_records) / сверхурочно = факт - табель.
"""
import calendar
import re
from datetime import date
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import allowed_department_id_set, get_current_user
from app.database import get_db
from app.models.department import Department
from app.models.tabel import Tabel, TabelEntry
from app.models.time_code import TimeCode
from app.models.timesheet_record import TimesheetRecord
from app.models.user import User
from app.models.work_schedule import WorkScheduleDay
from app.api.schedules import calculate_day_norm

router = APIRouter(prefix="/reports", tags=["Reports"])


def require_report_user(user: User = Depends(get_current_user)) -> User:
    """Доступ к сводному отчёту: роль «Отчёт», а также администратор/кадровик."""
    if not (user.is_report or user.is_admin or user.is_hr):
        raise HTTPException(status_code=403, detail="Требуется роль «Отчёт»")
    return user


NUM_RE = re.compile(r"^\d{1,2}([.,]\d{1,2})?$")
HM_RE = re.compile(r"^(\d+)\s*ч\s*(\d+)?\s*м?$")


def raw_to_hours(value: str) -> float | None:
    """Разбор числового значения ячейки («8.5», «8ч15м», «8:15») в часы.

    Зеркалирует фронтенд-функцию rawToHours из TabelFill.vue — чтобы отчёт
    считал часы табеля так же, как итоговые колонки, которые заполняет
    пользователь руками.
    """
    s = str(value or "").strip().replace(",", ".")
    if not s:
        return None
    m = HM_RE.match(s)
    if m:
        return int(m.group(1)) + (int(m.group(2) or 0) / 60.0)
    m = NUM_RE.match(s)
    if m:
        return float(s.replace(",", "."))
    m = re.match(r"^(\d{1,2})\s*:\s*(\d{2})$", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 60.0
    return None


def cell_hours(value: str, codes: dict, day_norm: float | None = None) -> float:
    """Часы из значения ячейки табеля: число или код из справочника.»

    day_norm — норма графика на этот день (если известна): нужна для кодов
    с «Время по графику» (use_schedule_hours), чтобы часы совпадали с табелем.
    """
    s = str(value or "").strip().lower().replace(",", ".")
    if not s:
        return 0.0
    m = HM_RE.match(s)
    if m:
        return int(m.group(1)) + (int(m.group(2) or 0) / 60.0)
    if NUM_RE.match(s):
        return float(s)
    c = codes.get(s)
    if c:
        if getattr(c, "use_schedule_hours", False) and day_norm is not None:
            return code_effective_hours(c, day_norm)[2]
        return (c.hours_day or 0.0) + (c.hours_night or 0.0)
    return 0.0


def code_effective_hours(code, day_norm: float) -> tuple[float, float, float]:
    """Эффективные (day, night, total) часы кода для конкретного дня.

    Зеркалирует фронтенд-функцию codeHoursForDay из TabelFill.vue:
    если у кода включено «Время по графику» (use_schedule_hours) — часы
    берутся из нормы графика на этот день; в выходной/праздник (норма = 0)
    используются фиксированные weekend_hours из справочника (например, 8 для
    «К»). Иначе — фиксированные hours_day/hours_night из справочника.
    """
    if getattr(code, "use_schedule_hours", False):
        n = float(day_norm or 0.0)
        if n <= 0:
            we = getattr(code, "weekend_hours", None)
            try:
                we = float(we) if we is not None else 0.0
            except (TypeError, ValueError):
                we = 0.0
            we = we if we > 0 else 0.0
            return we, 0.0, we
        return n, 0.0, n
    day = float(code.hours_day or 0.0)
    night = float(code.hours_night or 0.0)
    return day, night, day + night


def summary_overtime_hours(entry, dim: int, codes: dict, norms_by_dow: dict,
                           year: int, month: int, emp_norm: float) -> float:
    """Сумма сверхурочных ЧАСОВ за месяц из заполненного вручную табеля.

    Повторяет логику calculateSummary() из frontend/src/views/TabelFill.vue:
      - числовой ввод ячейки («10», «8ч15м»): ot = max(0, часы − норма дня);
      - код справочника с направлением overtime_hours (например «8с») —
        сверхурочный код: ВСЕ его часы идут в сверхурочные;
      - обычный код справочника: ot = max(0, эффективные часы − норма дня),
        только для кодов БЕЗ собственных направлений overtime_* и без
        use_schedule_hours;
      - КДУ (ручные колонки «КДУ»/«КДУ вых. дня») прибавляется к сверхурочным —
        это ручная отметка переработок со стабильно старых табелей.
    Норма дня — из графика работы по дню недели (fallback: employees.norm_hours/8).
    """
    def day_norm(d: int) -> float:
        dow = date(year, month, d).weekday()  # 0=Пн ... 6=Вс
        if norms_by_dow is not None:
            return float(norms_by_dow.get(dow, 0.0))
        return emp_norm

    total_ot = 0.0
    for d in range(1, dim + 1):
        val = str(getattr(entry, f"day_{d}", None) or "").strip().lower().replace(",", ".")
        if not val:
            continue
        norm = day_norm(d)
        code = codes.get(val)
        if code is not None:
            _, _, total_h = code_effective_hours(code, norm)
            dests = list(code.destinations or [])
            is_ot_code = ("overtime_hours" in dests) or ("overtime_days" in dests)
            if "overtime_hours" in dests:
                # ИСПРАВЛЕНО: код сам является сверхурочным (например «8с» с
                # направлением overtime_hours) — ВСЕ его часы идут в
                # «Сверхурочно с табеля» (как в calculateSummary на фронтенде).
                total_ot += total_h
            elif (getattr(code, "use_schedule_hours", False) and not is_ot_code
                  and norm <= 0 and total_h > 0):
                # НОВОЕ: «Время по графику» + «Часы для выходного дня»
                # (weekend_hours): работа в законный выходной (норма = 0) —
                # ВСЕ эти часы считаются сверхурочными (зеркало фронтенда).
                total_ot += total_h
            elif total_h > 0 and not is_ot_code and not getattr(code, "use_schedule_hours", False):
                total_ot += max(0.0, total_h - norm)
        else:
            h = raw_to_hours(val)
            if h is not None and h > 0:
                total_ot += max(0.0, h - norm)
    # КДУ — ручное поле табеля (переработки, отмеченные составителем вручную)
    total_ot += float(entry.kdu_work_days or 0) + float(entry.kdu_weekend_days or 0)
    return round(total_ot, 2)


class ReportRow(BaseModel):
    employee_id: int
    full_name: str
    tab_number: str
    department_name: str = ""
    tabel_hours: float = 0.0      # отработано часов с табеля
    fact_hours: float = 0.0       # отработано часов фактически (СКУД)
    overtime_planned: float = 0.0  # сверхурочно с табеля (из итогов заполненного вручную табеля: превышение нормы + КДУ)
    overtime_hours: float = 0.0   # сверхурочно факт = сумма ежедневных overtime из TimesheetRecord


class ReportOut(BaseModel):
    year: int
    month: int
    rows: list[ReportRow]


@router.get("/hours", response_model=ReportOut)
def hours_report(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    department_id: int | None = Query(None, description="Фильтр по подразделению"),
    db: Session = Depends(get_db),
    user: User = Depends(require_report_user),
):
    """Сводный отчёт часов за месяц: табель vs факт (СКУД).

    department_id — дополнительная фильтрация по конкретному подразделению
    (в пределах подразделений, доступных пользователю).
    """
    dim = calendar.monthrange(year, month)[1]
    period_start = date(year, month, 1)
    period_end = date(year, month, dim)

    # Ограничение по подразделениям пользователя (как в остальных модулях)
    allowed = allowed_department_id_set(user, db)

    # Фильтр по выбранному подразделению: проверяем доступность и раскрываем
    # подподразделения, чтобы отчёт включал всю ветку дерева.
    dept_filter: set[int] | None = None
    if department_id is not None:
        if allowed is not None and department_id not in allowed:
            raise HTTPException(status_code=403, detail="Подразделение недоступно")
        if db.query(Department.id).filter(Department.id == department_id).first() is None:
            raise HTTPException(status_code=404, detail="Подразделение не найдено")
        dept_filter = {department_id}
        # раскрываем всё дерево потомков (через parent_id)
        parents = {d.id: d.parent_id for d in db.query(Department.id, Department.parent_id).all()}
        for did in list(parents.keys()):
            p = parents.get(did)
            while p is not None:
                if p == department_id:
                    dept_filter.add(did)
                    break
                p = parents.get(p)

    def _in_dept(dep_id) -> bool:
        if allowed is not None and (dep_id is None or dep_id not in allowed):
            return False
        if dept_filter is not None and dep_id not in dept_filter:
            return False
        return True

    codes = {c.code.lower(): c for c in db.query(TimeCode).all()}

    # --- нормы часов по дням недели из графиков работы (0=Пн ... 6=Вс) ---
    sched_norms: Dict[int, Dict[int, float]] = {}
    sched_rows = db.query(WorkScheduleDay).all()
    for r in sched_rows:
        sched_norms.setdefault(r.schedule_id, {})[r.day_of_week] = calculate_day_norm(
            r.start_time, r.end_time, r.lunch_minutes, r.is_day_off
        )

    # --- часы с табелей за период + сверхурочно с табеля (из заполненного вручную табеля) ---
    tabel_q = db.query(TabelEntry).join(Tabel, Tabel.id == TabelEntry.tabel_id).filter(
        Tabel.year == year, Tabel.month == month)
    tabel_hours: dict[int, float] = {}
    overtime_tab: dict[int, float] = {}

    # Активные «Документы и приказы» за период — по сотрудникам. Если код дня
    # табеля совпадает с кодом документа, в отчёт берутся часы из документа.
    from app.models.document import Document
    docs_by_emp: dict[int, list] = {}
    for dc in db.query(Document).filter(
            Document.is_active.is_(True),
            Document.start_date <= period_end,
            Document.end_date >= period_start).all():
        docs_by_emp.setdefault(dc.employee_id, []).append(dc)

    for e in tabel_q.all():
        emp = e.employee
        if emp is None:
            continue
        if not _in_dept(emp.department_id):
            continue
        # «Сверхурочно с табеля» — из колонок, которые пользователь считает руками
        # в табеле (превышение над нормой графика + КДУ), а не только из ручного КДУ.
        norms_by_dow = None
        if emp.schedule_id and emp.schedule_id in sched_norms:
            norms_by_dow = sched_norms[emp.schedule_id]
        emp_norm = float(emp.norm_hours) if (emp.norm_hours is not None and float(emp.norm_hours) > 0) else 8.0

        def _norm_for_day(d: int, _nb=norms_by_dow, _en=emp_norm) -> float | None:
            """Норма дня сотрудника из его графика (0=Пн ... 6=Вс)."""
            if _nb is not None:
                return float(_nb.get(date(year, month, d).weekday(), 0.0))
            return _en

        # ИСПРАВЛЕНО: «Часы с табеля» считаются ИЗ РУЧНОГО ТАБЕЛЯ (TabelEntry)
        # с учётом индивидуального графика сотрудника: для кодов с
        # use_schedule_hours (например «8ч15м», «К») передаётся day_norm —
        # в будни берутся часы по графику, в выходной (норма=0) — фиксированные
        # weekend_hours. Без day_norm такие коды давали 0 часов, поэтому в
        # отчёте у Поцелуйкина было 74ч15м вместо ~200ч из табеля.
        # Дни активных «Документов и приказов» (отпуск/командировка/больничный):
        # если код дня совпадает с кодом документа — берём часы из документа
        # (field hours, проставляются из справочника «Коды часов»), что даёт
        # корректный результат даже когда день ещё не внесён в табель вручную.
        h = 0.0
        emp_docs = docs_by_emp.get(e.employee_id, [])
        for d in range(1, dim + 1):
            val = str(getattr(e, f"day_{d}", None) or "").strip().lower()
            doc_hit = None
            dtoday = date(year, month, d)
            for dc in emp_docs:
                if dc.start_date <= dtoday <= dc.end_date and \
                        str(dc.code or "").strip().lower() == val:
                    doc_hit = dc
                    break
            if doc_hit is not None and doc_hit.hours is not None:
                h += float(doc_hit.hours)
            else:
                h += cell_hours(getattr(e, f"day_{d}", None), codes, _norm_for_day(d))
        tabel_hours[e.employee_id] = tabel_hours.get(e.employee_id, 0.0) + h
        ot = summary_overtime_hours(e, dim, codes, norms_by_dow, year, month, emp_norm)
        if ot > 0:
            overtime_tab[e.employee_id] = overtime_tab.get(e.employee_id, 0.0) + ot

    # --- фактические часы по СКУД за период ---
    fact_q = db.query(
        TimesheetRecord.employee_id,
        TimesheetRecord.date,
        TimesheetRecord.fact_hours,
        TimesheetRecord.overtime,
    ).filter(TimesheetRecord.date >= period_start, TimesheetRecord.date <= period_end)

    # одна запись на сотрудника+день (на случай дублей берём максимум)
    fact_day: dict[tuple[int, date], float] = {}
    ot_day: dict[tuple[int, date], float] = {}
    for emp_id, dday, fh, otv in fact_q.all():
        key = (emp_id, dday)
        if (fh or 0.0) >= fact_day.get(key, 0.0):
            fact_day[key] = fh or 0.0
        # «Сверхурочно факт» — ежедневные сверхурочные из поля overtime
        # (превышение над нормой дня). Суммируются ПО ДНЯМ, а не как
        # max(0, общий факт - общая норма): даже если суммарный факт <
        # нормы месяца (недоотработанные дни), переработки в отдельные
        # дни считаются корректно.
        ot_day[key] = max(ot_day.get(key, 0.0), otv or 0.0)
    fact_hours: dict[int, float] = {}
    overtime_fact: dict[int, float] = {}
    for (emp_id, _dd), v in fact_day.items():
        fact_hours[emp_id] = fact_hours.get(emp_id, 0.0) + v
    for (emp_id, _dd), v in ot_day.items():
        if v > 0:
            overtime_fact[emp_id] = overtime_fact.get(emp_id, 0.0) + v

    # --- объединяем ---
    from app.models.employee import Employee

    emp_ids = set(tabel_hours) | set(fact_hours) | set(overtime_tab) | set(overtime_fact)
    if not emp_ids:
        return ReportOut(year=year, month=month, rows=[])

    emps = db.query(Employee).filter(Employee.id.in_(emp_ids)).all()
    dept_names = {d.id: d.name for d in db.query(Department).all()}

    rows: list[ReportRow] = []
    for emp in emps:
        if not _in_dept(emp.department_id):
            continue
        th = round(tabel_hours.get(emp.id, 0.0), 2)
        fh = round(fact_hours.get(emp.id, 0.0), 2)
        # «Сверхурочно факт» = сумма ежедневных сверхурочных (поле overtime
        # в TimesheetRecord), а НЕ max(0, общий факт - табель): переработки
        # по отдельным дням не «съедаются» недоотработкой за другие дни.
        ot = round(overtime_fact.get(emp.id, 0.0), 2)
        otp = round(overtime_tab.get(emp.id, 0.0), 2)
        rows.append(ReportRow(
            employee_id=emp.id,
            full_name=emp.full_name or "",
            tab_number=emp.tab_number or "",
            department_name=dept_names.get(emp.department_id, ""),
            tabel_hours=th,
            fact_hours=fh,
            overtime_planned=otp,
            overtime_hours=ot,
        ))

    rows.sort(key=lambda r: r.full_name)
    return ReportOut(year=year, month=month, rows=rows)
