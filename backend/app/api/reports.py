"""Сводный отчёт по часам для роли «Отчёт».

Строки: ФИО / часы с табеля (TabelFill, итог за месяц) /
фактические часы по СКУД (timesheet_records) / сверхурочно = факт - табель.
"""
import calendar
import re
from datetime import date

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

router = APIRouter(prefix="/reports", tags=["Reports"])


def require_report_user(user: User = Depends(get_current_user)) -> User:
    """Доступ к сводному отчёту: роль «Отчёт», а также администратор/кадровик."""
    if not (user.is_report or user.is_admin or user.is_hr):
        raise HTTPException(status_code=403, detail="Требуется роль «Отчёт»")
    return user


NUM_RE = re.compile(r"^\d{1,2}([.,]\d{1,2})?$")
HM_RE = re.compile(r"^(\d+)\s*ч\s*(\d+)?\s*м?$")


def cell_hours(value: str, codes: dict) -> float:
    """Часы из значения ячейки табеля: число или код из справочника.»"""
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
        return (c.hours_day or 0.0) + (c.hours_night or 0.0)
    return 0.0


class ReportRow(BaseModel):
    employee_id: int
    full_name: str
    tab_number: str
    department_name: str = ""
    tabel_hours: float = 0.0      # отработано часов с табеля
    fact_hours: float = 0.0       # отработано часов фактически (СКУД)
    overtime_planned: float = 0.0  # сверхурочно с табеля (КДУ: рабочие + выходные дни)
    overtime_hours: float = 0.0   # сверхурочно факт = факт - табель (не меньше 0)


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

    # --- часы с табелей за период + КДУ (сверхурочно с табеля) ---
    tabel_q = db.query(TabelEntry).join(Tabel, Tabel.id == TabelEntry.tabel_id).filter(
        Tabel.year == year, Tabel.month == month)
    tabel_hours: dict[int, float] = {}
    kdu_hours: dict[int, float] = {}

    for e in tabel_q.all():
        emp = e.employee
        if emp is None:
            continue
        if not _in_dept(emp.department_id):
            continue
        h = 0.0
        for d in range(1, dim + 1):
            h += cell_hours(getattr(e, f"day_{d}", None), codes)
        tabel_hours[e.employee_id] = tabel_hours.get(e.employee_id, 0.0) + h
        kdu = float(e.kdu_work_days or 0) + float(e.kdu_weekend_days or 0)
        if kdu:
            kdu_hours[e.employee_id] = kdu_hours.get(e.employee_id, 0.0) + kdu

    # --- фактические часы по СКУД за период ---
    fact_q = db.query(
        TimesheetRecord.employee_id,
        TimesheetRecord.date,
        TimesheetRecord.fact_hours,
    ).filter(TimesheetRecord.date >= period_start, TimesheetRecord.date <= period_end)

    # одна запись на сотрудника+день (на случай дублей берём максимум)
    fact_day: dict[tuple[int, date], float] = {}
    for emp_id, dday, fh in fact_q.all():
        key = (emp_id, dday)
        fact_day[key] = max(fact_day.get(key, 0.0), fh or 0.0)
    fact_hours: dict[int, float] = {}
    for (emp_id, _dd), v in fact_day.items():
        fact_hours[emp_id] = fact_hours.get(emp_id, 0.0) + v

    # --- объединяем ---
    from app.models.employee import Employee

    emp_ids = set(tabel_hours) | set(fact_hours) | set(kdu_hours)
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
        ot = round(max(fh - th, 0.0), 2)
        otp = round(kdu_hours.get(emp.id, 0.0), 2)
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
