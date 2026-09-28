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


class UnrecognizedDayItem(BaseModel):
    date: str          # "2026-09-15"
    employee_id: int


class LinkUnrecognizedRequest(BaseModel):
    raw_name: str
    items: List[UnrecognizedDayItem]


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


@router.get("/unrecognized-events")
def get_unrecognized_events(raw_name: str, db: Session = Depends(get_db)):
    """Список проходов нераспознанного ФИО, сгруппированных по датам.

    Возвращает для каждой даты: время первого входа, время последнего выхода
    и количество событий за день.
    """
    events = db.query(TurnstileEvent).filter(
        TurnstileEvent.employee_id.is_(None),
        func.trim(TurnstileEvent.raw_name) == raw_name.strip(),
    ).order_by(TurnstileEvent.datetime).all()

    by_day = {}
    for e in events:
        day = e.datetime.date().isoformat()
        d = by_day.setdefault(day, {"date": day, "count": 0, "first_in": None, "last_out": None})
        d["count"] += 1
        t = e.datetime.strftime("%H:%M")
        if e.event_type == "in" and (d["first_in"] is None or t < d["first_in"]):
            d["first_in"] = t
        if e.event_type == "out" and (d["last_out"] is None or t > d["last_out"]):
            d["last_out"] = t

    return sorted(by_day.values(), key=lambda x: x["date"], reverse=True)


@router.post("/link-unrecognized")
def link_unrecognized(request: LinkUnrecognizedRequest, db: Session = Depends(get_db)):
    """Привязать события нераспознанного ФИО к сотрудникам по датам.

    Тело: { "raw_name": "Забывчивый 1", "items": [{ "date": "2026-09-28", "employee_id": 123 }, ...] }
    Для каждой даты все нераспознанные события этого ФИО за этот день привязываются
    к указанному сотруднику. Дни без привязки остаются нераспознанными.
    """
    if not request.items:
        raise HTTPException(status_code=400, detail="Пустой список привязок")

    # Проверим существование всех сотрудников заранее
    emp_ids = {item.employee_id for item in request.items}
    found = {e.id for e in db.query(Employee).filter(Employee.id.in_(emp_ids)).all()}
    missing = emp_ids - found
    if missing:
        raise HTTPException(status_code=404, detail=f"Сотрудники не найдены: {sorted(missing)}")

    events = db.query(TurnstileEvent).filter(
        TurnstileEvent.employee_id.is_(None),
        func.trim(TurnstileEvent.raw_name) == request.raw_name.strip(),
    ).all()

    # Индекс: дата -> employee_id
    day_map = {item.date: item.employee_id for item in request.items}
    updated = 0
    for event in events:
        day = event.datetime.date().isoformat()
        if day in day_map:
            event.employee_id = day_map[day]
            event.is_recognized = True
            updated += 1

    db.commit()
    return {"status": "ok", "updated": updated, "requested_days": len(day_map)}


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