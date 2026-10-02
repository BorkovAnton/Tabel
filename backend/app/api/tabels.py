import calendar
import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import String, func, or_
from sqlalchemy.orm import Session
from typing import Dict, List, Optional

from app.core.security import (
    allowed_department_id_set,
    can_manage_tabels,
    check_department_access,
    get_current_user,
    require_admin,
    require_timesheet_inspector,
)
from app.database import get_db
from app.models.department import Department
from app.models.employee import Employee
from app.models.tabel import Tabel, TabelEntry
from app.models.time_code import TimeCode
from app.models.user import User

router = APIRouter(prefix="/tabels", tags=["Tabels"])

NUMERIC_RE = re.compile(r"^\d{1,2}([.,]\d{1,2})?$")  # часы: >0 и <= 23.59 (точность до сотых)
# Числовые коды из справочника допускаются как значения ячейки наравне с текстовыми
CODE_NUMERIC_RE = re.compile(r"^\d+[.,]?\d*$")


def validate_day_value(value: str, valid_codes: set[str]) -> str:
    """Значение ячейки: только код из справочника «Коды часов» (в т.ч. числовые, напр. «8с», «8н»)
    либо число часов >0 и <=23.59 (для совместимости со старыми данными)."""
    v = value.strip()
    if not v:
        return ""
    codes_lower = {c.lower() for c in valid_codes}
    # сначала проверяем точное совпадение с кодом справочника (важно для «8н», «8с» и т.п.)
    if v.lower() in codes_lower:
        return v
    if NUMERIC_RE.match(v):
        num = float(v.replace(",", "."))
        if num <= 0:
            raise ValueError(f"«{v}»: значение должно быть больше 0")
        if num > 23.59:
            raise ValueError(f"«{v}»: значение не может быть больше 23.59")
        return f"{num:.2f}".rstrip("0").rstrip(".")
    raise ValueError(f"«{v}»: выберите значение из списка «Коды часов»")


def entry_days(entry: TabelEntry, days_in_month: int) -> Dict[int, str]:
    return {d: getattr(entry, f"day_{d}") or "" for d in range(1, days_in_month + 1)}


class TabelOut(BaseModel):
    id: int
    year: int
    month: int
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    responsible_user_id: int
    responsible_user_name: Optional[str] = None
    employees_count: int = 0

    class Config:
        from_attributes = True


class TabelCreate(BaseModel):
    year: int
    month: int
    department_id: Optional[int] = None
    responsible_user_id: Optional[int] = None


class EntryRow(BaseModel):
    employee_id: int
    full_name: str
    tab_number: str
    days: Dict[int, str]
    # Ручные итоговые колонки «КДУ» (0..5, точность до сотых)
    kdu_work_days: Optional[float] = None
    kdu_weekend_days: Optional[float] = None
    # Резервная норма часов в день из сотрудника (fallback, если график не назначен); NULL => 8
    norm_hours: Optional[float] = None
    # График работы сотрудника (для норм по дням недели)
    schedule_id: Optional[int] = None
    # Норма часов для каждого дня месяца {1: 8.25, ...}; пустой dict => нет графика (используйте fallback)
    day_norms: Dict[int, float] = {}
    # «Код для автозаполнения» из графика по дням месяца {1: "8ч15м", 6: "В", ...}
    # (день недели -> auto_fill_code; дни без кода отсутствуют в словаре)
    day_auto_codes: Dict[int, str] = {}

    @field_validator("full_name", "tab_number", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        # старые записи могут содержать NULL — не роняем ответ валидацией
        return "" if v is None else v


class TabelDetailOut(BaseModel):
    id: int
    year: int
    month: int
    days_in_month: int
    department_id: Optional[int] = None
    department_name: Optional[str] = None
    responsible_user_id: int
    responsible_user_name: Optional[str] = None
    entries: List[EntryRow]
    # подсветка нерабочих дней: номера дней месяца (1..days_in_month)
    weekend_days: List[int] = []
    holiday_days: List[int] = []
    holiday_names: Dict[int, str] = {}


class CellUpdate(BaseModel):
    employee_id: int
    day: int
    value: str


class KduUpdate(BaseModel):
    """Ручное значение итоговой колонки КДУ (0..5, точность до сотых)."""
    employee_id: int
    field: str  # 'kdu_work_days' | 'kdu_weekend_days'
    value: Optional[float] = None

    @field_validator("value")
    @classmethod
    def _clamp(cls, v):
        if v is None:
            return None
        # Нормализация как на фронтенде (clampKdu): округляем до сотых и
        # обрезаем до диапазона 0..5. Это защищает колонки NUMERIC(4,2) от
        # переполнения и гарантирует, что сохранённое значение совпадает с тем,
        # что ввёл пользователь (значения вне диапазона приходят, например, из
        # sendBeacon-автосохранения со старых версий страницы).
        v = round(float(v), 2)
        return min(5.0, max(0.0, v))

    @field_validator("field")
    @classmethod
    def _allowed_field(cls, v):
        if v not in ("kdu_work_days", "kdu_weekend_days"):
            raise ValueError("Недопустимое поле КДУ")
        return v


class EntriesAdd(BaseModel):
    employee_ids: List[int]


# ---------- вспомогательные ----------

def _get_tabel_or_404(tabel_id: int, db: Session) -> Tabel:
    tabel = db.get(Tabel, tabel_id)
    if not tabel:
        raise HTTPException(status_code=404, detail="Табель не найден")
    return tabel


def _can_access(tabel: Tabel, user: User) -> bool:
    if (user.is_admin or user.is_hr) and user.timesheet_inspector:
        return True
    # Роль «Пользователь»: доступ к табелям, где он ответственный
    if user.is_user and tabel.responsible_user_id == user.id:
        return True
    return tabel.responsible_user_id == user.id


def _check_edit_access(tabel: Tabel, user: User):
    """Редактировать/удалять табель может его ответственный (в т.ч. роль «Пользователь»)
    или инспектор табелей."""
    if not _can_access(tabel, user):
        raise HTTPException(status_code=403, detail="Нет доступа к этому табелю")
    if tabel.responsible_user_id != user.id and not can_manage_tabels(user):
        raise HTTPException(status_code=403, detail="Табель может редактировать только ответственный")


def _check_access(tabel: Tabel, user: User):
    if not _can_access(tabel, user):
        raise HTTPException(status_code=403, detail="Нет доступа к этому табелю")


def _valid_codes(db: Session) -> set[str]:
    return {c.code for c in db.query(TimeCode).filter(TimeCode.is_active == True).all()}  # noqa: E712


# ---------- эндпоинты ----------
# ВАЖНО: статические пути (/search/employees) объявляются ДО динамических
# (/{tabel_id}), иначе FastAPI подставит "search" в параметр tabel_id -> 422.

@router.get("/search/employees", response_model=List[dict])
def search_employees(q: str = Query("", min_length=0), db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    """Поиск сотрудников по фамилии/табельному для выпадающего списка.

    Роль «Пользователь» видит только сотрудников своих подразделений
    (права задаёт администратор в справочнике «Пользователи»).
    """
    query = db.query(Employee)
    allowed = allowed_department_id_set(user, db)
    if allowed is not None:
        if not allowed:
            return []
        query = query.filter(Employee.department_id.in_(allowed))
    term = q.strip()
    if term:
        # Регистронезависимый поиск по подстроке (роман находит и «Романов»,
        # и «Бельков Роман»), с нормализацией Ё->Е. Поля: ФИО, табельный номер,
        # название подразделения.
        norm = lambda expr: func.lower(func.replace(expr, 'Ё', 'Е'))
        like = f"%{term.lower().replace('ё', 'е')}%"
        query = query.outerjoin(Department, Employee.department_id == Department.id).filter(
            or_(
                norm(Employee.full_name).like(like),
                norm(func.cast(Employee.tab_number, String)).like(like),
                norm(Department.name).like(like),
            )
        )
    emps = query.order_by(Employee.full_name).limit(50).all()
    return [
        {"id": e.id, "full_name": e.full_name, "tab_number": e.tab_number,
         "department_name": e.department.name if e.department else None}
        for e in emps
    ]


@router.get("/", response_model=List[TabelOut])
def list_tabels(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Список табелей.

    Обычный сотрудник видит только табели, где он ответственный.
    Администратор/кадровик с ролью «Инспектор табелей» видит все табели.
    """
    q = db.query(Tabel)
    is_inspector = (user.is_admin or user.is_hr) and user.timesheet_inspector
    if not is_inspector:
        q = q.filter(Tabel.responsible_user_id == user.id)
    if year:
        q = q.filter(Tabel.year == year)
    if month:
        q = q.filter(Tabel.month == month)

    result = []
    for t in q.order_by(Tabel.year.desc(), Tabel.month.desc()).all():
        result.append(TabelOut(
            id=t.id,
            year=t.year,
            month=t.month,
            department_id=t.department_id,
            department_name=t.department.name if t.department else None,
            responsible_user_id=t.responsible_user_id,
            responsible_user_name=t.responsible_user.full_name or t.responsible_user.username if t.responsible_user else None,
            employees_count=db.query(TabelEntry).filter(TabelEntry.tabel_id == t.id).count(),
        ))
    return result


@router.post("/", response_model=TabelOut)
def create_tabel(payload: TabelCreate, db: Session = Depends(get_db),
                 user: User = Depends(require_timesheet_inspector)):
    """Создать табель — могут инспекторы табелей и роль «Пользователь».

    Пользователь без прав на все подразделения может создавать табели
    только для своих подразделений.
    """
    if not (1 <= payload.month <= 12):
        raise HTTPException(status_code=400, detail="Некорректный месяц")
    check_department_access(user, db, payload.department_id)
    existing = db.query(Tabel).filter(
        Tabel.year == payload.year,
        Tabel.month == payload.month,
        Tabel.department_id == payload.department_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Табель за этот период/подразделение уже существует")

    responsible_id = payload.responsible_user_id or user.id
    if not db.get(User, responsible_id):
        raise HTTPException(status_code=400, detail="Ответственный пользователь не найден")

    tabel = Tabel(year=payload.year, month=payload.month,
                  department_id=payload.department_id, responsible_user_id=responsible_id)
    db.add(tabel)
    db.commit()
    db.refresh(tabel)
    return TabelOut(
        id=tabel.id, year=tabel.year, month=tabel.month,
        department_id=tabel.department_id,
        department_name=tabel.department.name if tabel.department else None,
        responsible_user_id=tabel.responsible_user_id,
        responsible_user_name=tabel.responsible_user.full_name or tabel.responsible_user.username,
        employees_count=0,
    )


@router.get("/{tabel_id}", response_model=TabelDetailOut)
def get_tabel(tabel_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    tabel = _get_tabel_or_404(tabel_id, db)
    _check_access(tabel, user)
    dim = calendar.monthrange(tabel.year, tabel.month)[1]
    # Нормы часов по дням недели из графиков работы (0=Пн ... 6=Вс)
    from app.models.work_schedule import WorkScheduleDay
    sched_ids = {e.employee.schedule_id for e in tabel.entries
                 if e.employee and e.employee.schedule_id}
    schedule_norms: Dict[int, Dict[int, float]] = {}
    schedule_codes: Dict[int, Dict[int, str]] = {}
    if sched_ids:
        from app.api.schedules import calculate_day_norm
        rows = db.query(WorkScheduleDay).filter(WorkScheduleDay.schedule_id.in_(sched_ids)).all()
        for r in rows:
            schedule_norms.setdefault(r.schedule_id, {})[r.day_of_week] = calculate_day_norm(
                r.start_time, r.end_time, r.lunch_minutes, r.is_day_off
            )
            # «Код для автозаполнения» из графика (пустой не сохраняем)
            ac = (getattr(r, "auto_fill_code", None) or "").strip()
            if ac:
                schedule_codes.setdefault(r.schedule_id, {})[r.day_of_week] = ac
    entries = []
    for e in sorted(tabel.entries, key=lambda x: (x.position or 0, x.id)):
        emp = e.employee
        # Норма для каждого дня месяца: из графика по дню недели; fallback — employees.norm_hours или 8
        day_norms: Dict[int, float] = {}
        # Коды автозаполнения по дням месяца: из графика по дню недели
        day_auto_codes: Dict[int, str] = {}
        if emp and emp.schedule_id and emp.schedule_id in schedule_norms:
            norms_by_dow = schedule_norms[emp.schedule_id]
            codes_by_dow = schedule_codes.get(emp.schedule_id, {})
            for d in range(1, dim + 1):
                dow = date(tabel.year, tabel.month, d).weekday()  # 0=Пн ... 6=Вс
                day_norms[d] = float(norms_by_dow.get(dow, 0.0))
                if dow in codes_by_dow:
                    day_auto_codes[d] = codes_by_dow[dow]
        entries.append(EntryRow(
            employee_id=e.employee_id,
            full_name=emp.full_name if emp else "",
            tab_number=emp.tab_number if emp else "",
            days=entry_days(e, dim),
            kdu_work_days=float(e.kdu_work_days) if e.kdu_work_days is not None else None,
            kdu_weekend_days=float(e.kdu_weekend_days) if e.kdu_weekend_days is not None else None,
            norm_hours=float(emp.norm_hours) if (emp and emp.norm_hours is not None) else None,
            schedule_id=emp.schedule_id if emp else None,
            day_norms=day_norms,
            day_auto_codes=day_auto_codes,
        ))
    return TabelDetailOut(
        id=tabel.id, year=tabel.year, month=tabel.month, days_in_month=dim,
        department_id=tabel.department_id,
        department_name=tabel.department.name if tabel.department else None,
        responsible_user_id=tabel.responsible_user_id,
        responsible_user_name=tabel.responsible_user.full_name or tabel.responsible_user.username if tabel.responsible_user else None,
        entries=entries,
        **nonworking_days_map(tabel.year, tabel.month, dim, db),
    )


def nonworking_days_map(year: int, month: int, dim: int, db: Session) -> dict:
    """Выходные и праздники месяца из производственного календаря (holiday_calendars).

    Если календарь за год не загружен — fallback: выходные по пятидневке (сб/вс).
    """
    from app.models.holiday_calendar import HolidayCalendar

    rows = db.query(HolidayCalendar).filter(
        HolidayCalendar.date >= date(year, month, 1),
        HolidayCalendar.date <= date(year, month, dim),
    ).all()
    weekend_days: List[int] = []
    holiday_days: List[int] = []
    holiday_names: Dict[int, str] = {}
    if rows:
        for h in rows:
            if h.is_holiday:
                holiday_days.append(h.date.day)
                if h.description:
                    holiday_names[h.date.day] = h.description
            elif h.is_weekend:
                weekend_days.append(h.date.day)
    else:
        # календарь не загружен — считаем выходные по стандартной пятидневке
        for d in range(1, dim + 1):
            if date(year, month, d).weekday() in (5, 6):
                weekend_days.append(d)
    return {
        "weekend_days": sorted(weekend_days),
        "holiday_days": sorted(holiday_days),
        "holiday_names": holiday_names,
    }


@router.post("/{tabel_id}/employees")
def add_employees(tabel_id: int, payload: EntriesAdd, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    """Добавить сотрудников в табель (выбор из списка с поиском на фронтенде)."""
    tabel = _get_tabel_or_404(tabel_id, db)
    _check_access(tabel, user)
    added = 0
    next_pos = (db.query(func.max(TabelEntry.position)).filter(
        TabelEntry.tabel_id == tabel_id).scalar() or 0) + 1
    for emp_id in payload.employee_ids:
        emp = db.get(Employee, emp_id)
        if not emp:
            continue
        exists = db.query(TabelEntry).filter(
            TabelEntry.tabel_id == tabel_id, TabelEntry.employee_id == emp_id).first()
        if exists:
            continue
        # новый сотрудник добавляется в конец списка — строки «съезжают» вниз
        db.add(TabelEntry(tabel_id=tabel_id, employee_id=emp_id, position=next_pos))
        next_pos += 1
        added += 1
    db.commit()
    return {"added": added}


@router.put("/{tabel_id}/cells")
def update_cells(tabel_id: int, updates: List[CellUpdate], db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Сохранить ячейки табеля. Значение — число часов (0…23.59) или код из справочника."""
    tabel = _get_tabel_or_404(tabel_id, db)
    _check_access(tabel, user)
    dim = calendar.monthrange(tabel.year, tabel.month)[1]
    codes = _valid_codes(db)

    errors = []
    cache: Dict[int, Optional[TabelEntry]] = {}
    for up in updates:
        if not (1 <= up.day <= dim):
            errors.append(f"День {up.day} вне диапазона месяца")
            continue
        try:
            value = validate_day_value(up.value, codes)
        except ValueError as ex:
            errors.append(str(ex))
            continue
        key = up.employee_id
        if key not in cache:
            cache[key] = db.query(TabelEntry).filter(
                TabelEntry.tabel_id == tabel_id, TabelEntry.employee_id == key).first()
        entry = cache[key]
        if not entry:
            next_pos = (db.query(func.max(TabelEntry.position)).filter(
                TabelEntry.tabel_id == tabel_id).scalar() or 0) + 1
            entry = TabelEntry(tabel_id=tabel_id, employee_id=key, position=next_pos)
            db.add(entry)
            cache[key] = entry
        setattr(entry, f"day_{up.day}", value)
    db.commit()
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    return {"saved": len(updates)}


@router.put("/{tabel_id}/kdu")
def update_kdu(tabel_id: int, updates: List[KduUpdate], db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    """Сохранить ручные значения КДУ (0..5, до сотых) для строк табеля.

    Значения нормализуются так же, как на фронтенде (clampKdu): вне диапазона
    0..5 обрезаются, округляются до сотых. Это защищает колонки NUMERIC(4,2)
    от переполнения и гарантирует, что сохранённое значение совпадает с тем,
    что ввёл пользователь.
    """
    tabel = _get_tabel_or_404(tabel_id, db)
    _check_access(tabel, user)
    # Кэш записей по employee_id: повторные изменения одного сотрудника
    # применяются к одному объекту (последнее значение побеждает).
    cache: Dict[int, TabelEntry] = {}
    saved = 0
    for up in updates:
        value = up.value
        if value is not None:
            value = min(5.0, max(0.0, float(value)))
            value = round(value + 0.0, 2)
        key = up.employee_id
        if key not in cache:
            entry = db.query(TabelEntry).filter(
                TabelEntry.tabel_id == tabel_id, TabelEntry.employee_id == key).first()
            if not entry:
                raise HTTPException(status_code=404, detail=f"Запись сотрудника {key} не найдена")
            cache[key] = entry
        setattr(cache[key], up.field, value)
        saved += 1
    try:
        db.commit()
    except Exception as exc:  # например, переполнение NUMERIC(4,2) на старых данных
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Не удалось сохранить КДУ: {exc}")
    return {"saved": saved}


@router.post("/{tabel_id}/kdu")
def update_kdu_beacon(tabel_id: int, updates: List[KduUpdate], db: Session = Depends(get_db),
                      user: User = Depends(get_current_user)):
    """Дубликат PUT /kdu для navigator.sendBeacon (закрывает несохранённое КДУ
    при закрытии вкладки; sendBeacon умеет отправлять только POST и не может
    ставить заголовок Authorization — токен передаётся query-параметром)."""
    return update_kdu(tabel_id, updates, db, user)


@router.delete("/{tabel_id}/entries/{employee_id}")
def remove_employee(tabel_id: int, employee_id: int, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    tabel = _get_tabel_or_404(tabel_id, db)
    _check_access(tabel, user)
    entry = db.query(TabelEntry).filter(
        TabelEntry.tabel_id == tabel_id, TabelEntry.employee_id == employee_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    db.delete(entry)
    db.commit()
    return {"ok": True}


@router.delete("/{tabel_id}")
def delete_tabel(tabel_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """Удалить табель — ответственный (в т.ч. роль «Пользователь») или инспектор табелей."""
    tabel = _get_tabel_or_404(tabel_id, db)
    _check_edit_access(tabel, user)
    for e in list(tabel.entries):
        db.delete(e)
    db.delete(tabel)
    db.commit()
    return {"ok": True}
