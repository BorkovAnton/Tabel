from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date, timedelta
from pydantic import BaseModel
from sqlalchemy import func

from app.database import get_db
from app.models.turnstile_event import TurnstileEvent
from app.models.employee import Employee
from app.models.department import Department

router = APIRouter(prefix="/api/turnstile-fix", tags=["Turnstile Fix"])


class LinkRequest(BaseModel):
    employee_id: int


class BulkLinkRequest(BaseModel):
    raw_name: str
    employee_id: int


class FixMissingRequest(BaseModel):
    employee_id: int
    datetime: str
    event_type: str


@router.get("/unrecognized-names")
def get_unrecognized_names(db: Session = Depends(get_db)):
    """Получить список нераспознанных ФИО с количеством"""
    events = db.query(TurnstileEvent).filter(
        TurnstileEvent.employee_id.is_(None),
        TurnstileEvent.raw_name.isnot(None)
    ).all()
    
    name_count = {}
    for event in events:
        name = event.raw_name.strip()
        if name:
            name_count[name] = name_count.get(name, 0) + 1
    
    result = [{"raw_name": name, "count": count} for name, count in name_count.items()]
    return sorted(result, key=lambda x: x["count"], reverse=True)


@router.get("/issues")
def get_issues(
    date_from: str = Query(...),
    date_to: str = Query(...),
    issue_type: str = Query(...),
    db: Session = Depends(get_db)
):
    """Получить проблемы разных типов"""
    
    from_date = datetime.fromisoformat(date_from)
    to_date = datetime.fromisoformat(date_to) + timedelta(days=1)
    
    if issue_type == "unrecognized":
        events = db.query(TurnstileEvent).filter(
            TurnstileEvent.employee_id.is_(None),
            TurnstileEvent.datetime >= from_date,
            TurnstileEvent.datetime < to_date
        ).all()
        
        return [{
            "id": e.id,
            "raw_name": e.raw_name,
            "datetime": e.datetime.isoformat(),
            "event_type": e.event_type
        } for e in events]
    
    elif issue_type == "missing_entry":
        events = db.query(TurnstileEvent).filter(
            TurnstileEvent.datetime >= from_date,
            TurnstileEvent.datetime < to_date
        ).all()
        
        by_employee_day = {}
        for e in events:
            day = e.datetime.date()
            key = (e.employee_id, day)
            if key not in by_employee_day:
                by_employee_day[key] = {"in": [], "out": []}
            by_employee_day[key][e.event_type].append(e)
        
        result = []
        for (emp_id, day), data in by_employee_day.items():
            if data["out"] and not data["in"]:
                out_times = sorted(list(set(e.datetime.strftime("%H:%M:%S") for e in data["out"])))
                result.append({
                    "employee_id": emp_id,
                    "date": day.isoformat(),
                    "issue": "Нет входа",
                    "existing_time": " | ".join(out_times),
                    "existing_type": "out"
                })
        return result
    
    elif issue_type == "missing_exit":
        events = db.query(TurnstileEvent).filter(
            TurnstileEvent.datetime >= from_date,
            TurnstileEvent.datetime < to_date
        ).all()
        
        by_employee_day = {}
        for e in events:
            day = e.datetime.date()
            key = (e.employee_id, day)
            if key not in by_employee_day:
                by_employee_day[key] = {"in": [], "out": []}
            by_employee_day[key][e.event_type].append(e)
        
        result = []
        for (emp_id, day), data in by_employee_day.items():
            if data["in"] and not data["out"]:
                in_times = sorted(list(set(e.datetime.strftime("%H:%M:%S") for e in data["in"])))
                result.append({
                    "employee_id": emp_id,
                    "date": day.isoformat(),
                    "issue": "Нет выхода",
                    "existing_time": " | ".join(in_times),
                    "existing_type": "in"
                })
        return result
    
    elif issue_type == "duplicate":
        events = db.query(TurnstileEvent).filter(
            TurnstileEvent.datetime >= from_date,
            TurnstileEvent.datetime < to_date
        ).all()
        
        seen = {}
        duplicates = []
        for e in events:
            key = (e.employee_id, e.event_type, e.datetime.replace(second=0, microsecond=0))
            if key in seen:
                duplicates.append({
                    "id": e.id,
                    "employee_id": e.employee_id,
                    "datetime": e.datetime.isoformat(),
                    "event_type": e.event_type,
                    "duplicate_of": seen[key]
                })
            else:
                seen[key] = e.id
        
        return duplicates
    
    return []


@router.patch("/{event_id}/link")
def link_event(event_id: int, request: LinkRequest, db: Session = Depends(get_db)):
    event = db.query(TurnstileEvent).filter(TurnstileEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    employee = db.query(Employee).filter(Employee.id == request.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    
    event.employee_id = request.employee_id
    event.is_recognized = True
    db.commit()
    return {"status": "ok"}


@router.patch("/bulk-link")
def bulk_link(request: BulkLinkRequest, db: Session = Depends(get_db)):
    events = db.query(TurnstileEvent).filter(
        TurnstileEvent.raw_name == request.raw_name
    ).all()
    
    count = len(events)
    for event in events:
        event.employee_id = request.employee_id
        event.is_recognized = True
    
    db.commit()
    return {"status": "ok", "updated": count}


@router.post("/fix-missing")
def fix_missing(request: FixMissingRequest, db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(Employee.id == request.employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    
    event_datetime = datetime.fromisoformat(request.datetime)
    
    event = TurnstileEvent(
        raw_name=employee.full_name,
        employee_id=request.employee_id,
        event_type=request.event_type,
        datetime=event_datetime,
        is_recognized=True
    )
    
    db.add(event)
    db.commit()
    db.refresh(event)
    
    return {"status": "ok", "id": event.id}


@router.delete("/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(TurnstileEvent).filter(TurnstileEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    db.delete(event)
    db.commit()
    return {"status": "ok"}