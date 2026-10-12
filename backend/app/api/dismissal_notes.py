from datetime import datetime, time as dtime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.employee import Employee
from app.models.department import Department
from app.models.dismissal_note import DismissalNote, DismissalEntry, DismissalDayRecord
from app.schemas.dismissal_note import (
    DismissalNoteCreate, DismissalNoteResponse,
    DismissalEntryResponse, DismissalDayRecordResponse
)

router = APIRouter(prefix="/dismissal-notes", tags=["DismissalNotes"])


def time_to_str(t) -> Optional[str]:
    return t.strftime("%H:%M") if t else None


def str_to_time(s: Optional[str]) -> Optional[dtime]:
    if not s:
        return None
    parts = s.split(":")
    try:
        return dtime(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None


def calculate_hours(time_out_str: Optional[str], time_in_str: Optional[str]) -> float:
    """Рассчитать часы между временем ухода и возврата"""
    if not time_out_str or not time_in_str:
        return 0.0

    t_out = str_to_time(time_out_str)
    t_in = str_to_time(time_in_str)

    if not t_out or not t_in:
        return 0.0

    # Если time_in меньше time_out — значит переход через полночь (редко, но возможно)
    dt_out = datetime.combine(datetime.today(), t_out)
    dt_in = datetime.combine(datetime.today(), t_in)

    if dt_in <= dt_out:
        dt_in += timedelta(days=1)

    delta = dt_in - dt_out
    return round(delta.total_seconds() / 3600, 2)


def build_note_response(note: DismissalNote, db: Session) -> DismissalNoteResponse:
    """Собрать отклик записки (заголовок + строки сотрудников + дневные записи)"""
    dept = db.get(Department, note.department_id) if note.department_id else None
    entries = []
    total_hours = 0.0

    for entry in note.entries:
        emp = db.get(Employee, entry.employee_id)
        day_records = []
        entry_total = 0.0

        for dr in sorted(entry.day_records, key=lambda r: r.day):
            day_records.append(DismissalDayRecordResponse(
                id=dr.id, day=dr.day,
                time_out=time_to_str(dr.time_out),
                time_in=time_to_str(dr.time_in),
                hours=float(dr.hours or 0),
                comment=dr.comment
            ))
            entry_total += float(dr.hours or 0)

        entries.append(DismissalEntryResponse(
            id=entry.id,
            employee_id=entry.employee_id,
            employee_name=emp.full_name if emp else None,
            employee_tab_number=emp.tab_number if emp else None,
            department_name=emp.department.name if emp and emp.department else None,
            day_records=day_records,
            total_hours=round(entry_total, 2)
        ))
        total_hours += entry_total

    return DismissalNoteResponse(
        id=note.id,
        period_start=note.period_start,
        period_end=note.period_end,
        department_id=note.department_id,
        department_name=dept.name if dept else None,
        comment=note.comment,
        created_at=note.created_at.isoformat() if note.created_at else None,
        entries=entries,
        total_hours=round(total_hours, 2)
    )


@router.get("/", response_model=List[DismissalNoteResponse])
def list_notes(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    department_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Список увольнительных записок"""
    query = db.query(DismissalNote)

    if date_from:
        query = query.filter(DismissalNote.period_end >= date_from)
    if date_to:
        query = query.filter(DismissalNote.period_start <= date_to)
    if department_id:
        query = query.filter(DismissalNote.department_id == department_id)

    notes = query.order_by(DismissalNote.period_start.desc()).all()

    return [build_note_response(note, db) for note in notes]


@router.get("/{note_id}", response_model=DismissalNoteResponse)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Получить одну увольнительную записку"""
    note = db.get(DismissalNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Записка не найдена")

    return build_note_response(note, db)


def _write_entries(db: Session, note: DismissalNote, payload: DismissalNoteCreate):
    """Создать строки сотрудников и дневные записи для записки"""
    for entry_data in payload.entries:
        entry = DismissalEntry(
            note_id=note.id,
            employee_id=entry_data.employee_id
        )
        db.add(entry)
        db.flush()

        for dr_data in entry_data.day_records:
            hours = calculate_hours(dr_data.time_out, dr_data.time_in)
            day_record = DismissalDayRecord(
                entry_id=entry.id,
                day=dr_data.day,
                time_out=str_to_time(dr_data.time_out),
                time_in=str_to_time(dr_data.time_in),
                hours=hours,
                comment=dr_data.comment
            )
            db.add(day_record)


@router.post("/", response_model=DismissalNoteResponse)
def create_note(
    payload: DismissalNoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Создать увольнительную записку"""
    note = DismissalNote(
        period_start=payload.period_start,
        period_end=payload.period_end,
        department_id=payload.department_id,
        created_by=user.id,
        comment=payload.comment
    )
    db.add(note)
    db.flush()

    _write_entries(db, note, payload)

    db.commit()
    db.refresh(note)

    return build_note_response(note, db)


@router.put("/{note_id}", response_model=DismissalNoteResponse)
def update_note(
    note_id: int,
    payload: DismissalNoteCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Обновить увольнительную записку (полная замена строк)"""
    note = db.get(DismissalNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Записка не найдена")

    # Удаляем старые записи (ORM-удаление, чтобы ORM-кэш сессии остался корректным;
    # дневные записи удаляются каскадом по связи relationship)
    for old_entry in list(note.entries):
        db.delete(old_entry)
    db.flush()

    # Обновляем заголовок
    note.period_start = payload.period_start
    note.period_end = payload.period_end
    note.department_id = payload.department_id
    note.comment = payload.comment

    db.flush()

    # Создаём новые записи
    _write_entries(db, note, payload)

    db.commit()
    db.refresh(note)

    return build_note_response(note, db)


@router.delete("/{note_id}")
def delete_note(
    note_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    """Удалить увольнительную записку"""
    note = db.get(DismissalNote, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Записка не найдена")

    db.delete(note)
    db.commit()
    return {"ok": True}
