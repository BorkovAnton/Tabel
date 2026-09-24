import calendar
import re
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Dict, List, Optional

from app.core.security import get_current_user, require_timesheet_inspector, require_admin, can_manage_tabels
from app.database import get_db
from app.models.department import Department
from app.models.employee import Employee
from app.models.tabel import Tabel, TabelEntry
from app.models.time_code import TimeCode
from app.models.user import User

router = APIRouter(prefix="/tabels", tags=["Tabels"])

NUMERIC_RE = re.compile(r"^\d{1,2}([.,]\d{1,2})?$")  # часы: >0 и <= 23.59 (точность до сотых)


def validate_day_value(value: str, valid_codes: set[str]) -> str:
    """Число часов (0..23.59, сотые) либо буквенный код из справочника."""
    v = value.strip()
    if not v:
        return ""
    if NUMERIC_RE.match(v):
        num = float(v.replace(",", "."))
        if num <= 0:
            raise ValueError(f"«{v}»: значение должно быть больше 0")
        if num > 23.59:
            raise ValueError(f"«{v}»: значение не может быть больше 23.59")
        return f"{num:.2f}".rstrip("0").rstrip(".").replace(".", ".")
    if v.lower() in {c.lower() for c in valid_codes}:
        return v
    raise ValueError(f"«{v}»: введите число часов (0…23.59) или код из справочника «Коды часов»")


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


class CellUpdate(BaseModel):
    employee_id: int
    day: int
    value: str


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
    """Поиск сотрудников по фамилии/табельному для выпадающего списка."""
    query = db.query(Employee)
    term = q.strip()
    if term:
        like = f"%{term}%"
        query = query.filter(
            (Employee.full_name.ilike(like)) | (Employee.tab_number.ilike(like)))
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
    """Создать табель — могут инспекторы табелей (администратор/кадровик)."""
    if not (1 <= payload.month <= 12):
        raise HTTPException(status_code=400, detail="Некорректный месяц")
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
    entries = []
    for e in sorted(tabel.entries, key=lambda x: (x.position or 0, x.id)):
        entries.append(EntryRow(
            employee_id=e.employee_id,
            full_name=e.employee.full_name if e.employee else "",
            tab_number=e.employee.tab_number if e.employee else "",
            days=entry_days(e, dim),
        ))
    return TabelDetailOut(
        id=tabel.id, year=tabel.year, month=tabel.month, days_in_month=dim,
        department_id=tabel.department_id,
        department_name=tabel.department.name if tabel.department else None,
        responsible_user_id=tabel.responsible_user_id,
        responsible_user_name=tabel.responsible_user.full_name or tabel.responsible_user.username if tabel.responsible_user else None,
        entries=entries,
    )


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
