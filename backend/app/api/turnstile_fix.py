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

# Ночная смена: вход вечером (после этого часа) может закрываться выходом
# следующего дня до полудня.
NIGHT_IN_HOUR = 20
NIGHT_OUT_MAX_HOUR = 12
# Если выхода нет в течение стольких часов после входа — считаем, что выхода нет.
MAX_SHIFT_HOURS = 16


def _pair_shifts(events):
    """Связать события «вход-выход» в смены с учётом ночных переходов через полночь.

    Логика:
      * События для каждого сотрудника сортируются по времени.
      * Вход после NIGHT_IN_HOUR (20:00) ожидает выход до NIGHT_OUT_MAX_HOUR (12:00)
        следующего дня — это одна ночная смена (например, 22:47 -> 07:02).
      * Обычный вход закрывается ближайшим выходом; если выход найден позже чем
        через MAX_SHIFT_HOURS часов (или не найден) — помечаем «Нет выхода».
      * Выход без предшествующего входа — «Нет входа».

    Возвращает список смен, отсортированных по дате начала и сотруднику.
    """
    by_emp = {}
    for e in events:
        if e.employee_id is None:
            continue
        by_emp.setdefault(e.employee_id, []).append(e)

    shifts = []
    for emp_id, evs in by_emp.items():
        evs = sorted(evs, key=lambda e: e.datetime)
        open_in = None       # datetime незакрытого входа
        open_events = []     # события текущей открытой смены
        pending_outs = []    # выходы, не нашедшие свой вход

        def close_shift(start, end, shift_events, is_night):
            duration = round((end - start).total_seconds() / 3600.0, 2) if end else None
            shifts.append({
                "employee_id": emp_id,
                "date": start.date().isoformat(),
                "shift_start": start,
                "first_in": start,
                "last_out": end,
                "has_in": True,
                "has_out": end is not None,
                "is_night": is_night,
                "duration_hours": duration,
                "events": shift_events,
            })

        for e in evs:
            dt = e.datetime
            if e.event_type == "in":
                if open_in is not None:
                    # Новый вход раньше закрытия предыдущей смены — фиксируем
                    # предыдущую как «нет выхода» и открываем новую.
                    close_shift(open_in, None, open_events, open_in.hour >= NIGHT_IN_HOUR)
                open_in = dt
                open_events = [e]
                # Присоединяем ранее «висящие» выходы этой же ночной смены
                for pe in list(pending_outs):
                    if pe.datetime > open_in and pe.datetime.hour < NIGHT_OUT_MAX_HOUR \
                            and (pe.datetime - open_in) <= timedelta(hours=MAX_SHIFT_HOURS):
                        open_events.append(pe)
                        close_shift(open_in, pe.datetime, open_events, True)
                        pending_outs.remove(pe)
                        open_in = None
                        open_events = []
                        break
            elif e.event_type == "out":
                if open_in is not None and dt > open_in \
                        and (dt - open_in) <= timedelta(hours=MAX_SHIFT_HOURS):
                    is_night = (dt.date() > open_in.date() and dt.hour < NIGHT_OUT_MAX_HOUR) \
                        or open_in.hour >= NIGHT_IN_HOUR
                    open_events.append(e)
                    close_shift(open_in, dt, open_events, is_night)
                    open_in = None
                    open_events = []
                elif open_in is None:
                    pending_outs.append(e)
                # если dt <= open_in — случайный выброс, игнорируем в составе смены

        if open_in is not None:
            close_shift(open_in, None, open_events, open_in.hour >= NIGHT_IN_HOUR)

        for pe in pending_outs:
            shifts.append({
                "employee_id": emp_id,
                "date": pe.datetime.date().isoformat(),
                "shift_start": pe.datetime,
                "first_in": None,
                "last_out": pe.datetime,
                "has_in": False,
                "has_out": True,
                "is_night": pe.datetime.hour < NIGHT_OUT_MAX_HOUR,
                "duration_hours": None,
                "events": [pe],
            })

    return sorted(shifts, key=lambda s: (s["shift_start"], s["employee_id"]))


class LinkRequest(BaseModel):
    employee_id: int


class BulkLinkRequest(BaseModel):
    raw_name: str
    employee_id: int


class FixMissingRequest(BaseModel):
    employee_id: int
    datetime: str
    event_type: Optional[str] = None  # "in" | "out"; если не указан — тип определится автоматически


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
    
    elif issue_type in ("missing_entry", "missing_exit"):
        want_entry = issue_type == "missing_entry"
        # События берём с запасом на сутки назад — чтобы находить вход ночной смены
        # предыдущим вечером.
        events = db.query(TurnstileEvent).filter(
            TurnstileEvent.datetime >= from_date - timedelta(days=1),
            TurnstileEvent.datetime < to_date
        ).order_by(TurnstileEvent.datetime).all()

        # Исключаем нераспознанные ФИО («Гость 1», «Забывчивый 2» и т.п.) —
        # у них нет employee_id; они обрабатываются на вкладке «Нераспознанные ФИО».
        recognized_events = [e for e in events if e.employee_id is not None]

        # Ручные отметки (is_manual=True) — это исправления, внесённые
        # пользователем через диалог «Добавить пропущенную отметку». Они не
        # участвуют в спаривании смен, а служат для закрытия проблем:
        # ручной вход закрывает «Нет входа», ручной выход — «Нет выхода».
        manual_ins = {}   # (emp_id, date) -> True
        manual_outs = {}  # (emp_id, date) -> True
        for e in recognized_events:
            if not getattr(e, "is_manual", False):
                continue
            d = e.datetime.date().isoformat()
            if e.event_type == "in":
                manual_ins[(e.employee_id, d)] = True
            elif e.event_type == "out":
                manual_outs[(e.employee_id, d)] = True

        shifts = _pair_shifts([e for e in recognized_events if not getattr(e, "is_manual", False)])

        # Группируем проблемы по сотруднику + дата + тип: одна строка на
        # сотрудника за день вместо множества строк с разными минутами.
        grouped = {}
        for s in shifts:
            # Ночная смена может начаться вчера — не показываем её как проблему сегодня
            if s["shift_start"].date() < from_date.date():
                continue
            emp_key = (s["employee_id"], s["date"])
            if want_entry:
                if s["has_in"]:
                    continue
                # Проблема решена, если для этого дня добавлен ручной вход
                if emp_key in manual_ins:
                    continue
            else:
                if not (s["has_in"] and not s["has_out"]):
                    continue
                # Проблема решена, если для этого дня добавлен ручной выход
                if emp_key in manual_outs:
                    continue

            times = set(
                e.datetime.strftime("%H:%M:%S")
                for e in s["events"]
                if e.event_type == ("out" if want_entry else "in")
            )
            key = (s["employee_id"], s["date"], "Нет входа" if want_entry else "Нет выхода")
            g = grouped.setdefault(key, {
                "employee_id": s["employee_id"],
                "date": s["date"],
                "is_night": s["is_night"],
                "duration_hours": s["duration_hours"],
                "first_in": None,
                "last_out": None,
                "issue": key[2],
                "_times": set(),
                "_count": 0,
            })
            g["_times"].update(times)
            g["_count"] += len(s["events"])
            if want_entry:
                if s["last_out"]:
                    lo = s["last_out"].strftime("%H:%M:%S")
                    g["last_out"] = max(filter(None, [g["last_out"], lo]))
            else:
                if s["first_in"]:
                    fi = s["first_in"].strftime("%H:%M:%S")
                    g["first_in"] = min(filter(None, [g["first_in"], fi]))

        result = []
        for g in grouped.values():
            times = sorted(g.pop("_times"))
            count = g.pop("_count")
            existing_type = "out" if want_entry else "in"
            # Не перегружаем строку: показываем первые несколько времен + количество
            shown = times[:5]
            existing_time = " | ".join(shown)
            if len(times) > 5:
                existing_time += f" … ({len(times)} отметок)"
            g["existing_time"] = existing_time
            g["existing_type"] = existing_type
            g["event_count"] = count
            result.append(g)
        return sorted(result, key=lambda r: (r["date"], r["employee_id"]))

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


@router.get("/shifts")
def get_shifts(
    date_from: str = Query(...),
    date_to: str = Query(...),
    db: Session = Depends(get_db)
):
    """Список смен (пар вход-выход) с учётом ночных переходов через полночь."""
    from_date = datetime.fromisoformat(date_from)
    to_date = datetime.fromisoformat(date_to) + timedelta(days=1)

    events = db.query(TurnstileEvent).filter(
        TurnstileEvent.datetime >= from_date - timedelta(days=1),
        TurnstileEvent.datetime < to_date
    ).order_by(TurnstileEvent.datetime).all()

    emp_names = {
        e.id: e.full_name
        for e in db.query(Employee).filter(Employee.id.isnot(None)).all()
    }

    result = []
    for s in _pair_shifts(events):
        if s["shift_start"].date() < from_date.date():
            continue
        if s["has_in"] and s["has_out"]:
            status, ok = "OK", True
        elif s["has_in"]:
            status, ok = "Нет выхода", False
        else:
            status, ok = "Нет входа", False
        result.append({
            "employee_id": s["employee_id"],
            "employee_name": emp_names.get(s["employee_id"], f"ID: {s['employee_id']}"),
            "date": s["date"],
            "is_night": s["is_night"],
            "first_in": s["first_in"].strftime("%d.%m %H:%M:%S") if s["first_in"] else None,
            "last_out": s["last_out"].strftime("%d.%m %H:%M:%S") if s["last_out"] else None,
            "duration_hours": s["duration_hours"],
            "status": status,
            "ok": ok,
        })
    return result


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

    try:
        event_datetime = datetime.fromisoformat(request.datetime)
    except ValueError:
        raise HTTPException(status_code=400, detail="Некорректный формат даты и времени")

    if request.event_type not in (None, "", "in", "out"):
        raise HTTPException(status_code=400, detail="Тип отметки должен быть 'in' или 'out'")

    event_type = request.event_type
    if not event_type:
        # Автоопределение: до полудня — вход, после — выход.
        event_type = "in" if event_datetime.hour < 12 else "out"

    # Защита от дубля: такое же событие уже есть (та же секунда).
    dup = db.query(TurnstileEvent).filter(
        TurnstileEvent.employee_id == request.employee_id,
        TurnstileEvent.datetime == event_datetime,
        TurnstileEvent.event_type == event_type,
    ).first()
    if dup:
        raise HTTPException(status_code=409, detail="Такое событие уже существует")

    event = TurnstileEvent(
        raw_name=employee.full_name,
        employee_id=request.employee_id,
        event_type=event_type,
        datetime=event_datetime,
        is_manual=True,
        is_recognized=True,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return {"status": "ok", "id": event.id, "event_type": event_type}


@router.delete("/{event_id}")
def delete_event(event_id: int, db: Session = Depends(get_db)):
    event = db.query(TurnstileEvent).filter(TurnstileEvent.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    db.delete(event)
    db.commit()
    return {"status": "ok"}