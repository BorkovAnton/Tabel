from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import time
from pydantic import BaseModel

from app.database import get_db
from app.models.work_schedule import WorkSchedule, WorkScheduleDay
from app.models.employee import Employee

router = APIRouter(prefix="/schedules", tags=["Schedules"])

DAY_NAMES = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
DAY_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


class ScheduleDayCreate(BaseModel):
    day_of_week: int  # 0-6
    start_time: Optional[str] = None  # "HH:MM" или None для выходного
    end_time: Optional[str] = None
    lunch_minutes: int = 60
    is_day_off: bool = False


class ScheduleCreate(BaseModel):
    name: str
    days: List[ScheduleDayCreate]


class ScheduleDayResponse(BaseModel):
    day_of_week: int
    day_name: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    lunch_minutes: int
    is_day_off: bool
    norm_hours: float


class ScheduleResponse(BaseModel):
    id: int
    name: str
    week_norm_hours: float
    employee_count: int
    days: List[ScheduleDayResponse]

    class Config:
        from_attributes = True


def parse_time(time_str: Optional[str]) -> Optional[time]:
    if not time_str:
        return None
    try:
        hours, minutes = map(int, time_str.split(':'))
        return time(hours, minutes)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail=f"Неверный формат времени: {time_str}. Ожидается HH:MM"
        )


def calculate_day_norm(start: Optional[time], end: Optional[time], lunch: int, is_off: bool) -> float:
    if is_off or not start or not end:
        return 0.0
    from datetime import datetime, date, timedelta
    start_dt = datetime.combine(date.today(), start)
    end_dt = datetime.combine(date.today(), end)
    if end_dt <= start_dt:
        end_dt += timedelta(days=1)
    gross = (end_dt - start_dt).total_seconds() / 3600
    return round(max(gross - lunch / 60, 0.0), 2)


@router.get("/", response_model=List[ScheduleResponse])
def get_schedules(db: Session = Depends(get_db)):
    schedules = db.query(WorkSchedule).all()
    result = []
    for sched in schedules:
        days_data = []
        week_norm = 0.0
        for day in sorted(sched.days, key=lambda d: d.day_of_week):
            norm = calculate_day_norm(day.start_time, day.end_time, day.lunch_minutes, day.is_day_off)
            week_norm += norm
            days_data.append({
                "day_of_week": day.day_of_week,
                "day_name": DAY_NAMES[day.day_of_week],
                "start_time": day.start_time.strftime("%H:%M") if day.start_time else None,
                "end_time": day.end_time.strftime("%H:%M") if day.end_time else None,
                "lunch_minutes": day.lunch_minutes,
                "is_day_off": day.is_day_off,
                "norm_hours": norm
            })
        
        employee_count = db.query(Employee).filter(Employee.schedule_id == sched.id).count()
        
        result.append({
            "id": sched.id,
            "name": sched.name,
            "week_norm_hours": round(week_norm, 2),
            "employee_count": employee_count,
            "days": days_data
        })
    return result


@router.post("/", response_model=ScheduleResponse)
def create_schedule(schedule: ScheduleCreate, db: Session = Depends(get_db)):
    existing = db.query(WorkSchedule).filter(WorkSchedule.name == schedule.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"График '{schedule.name}' уже существует")
    
    # Валидация: должно быть 7 дней
    if len(schedule.days) != 7:
        raise HTTPException(status_code=400, detail="Должно быть указано расписание для всех 7 дней недели")
    
    new_schedule = WorkSchedule(name=schedule.name)
    db.add(new_schedule)
    db.commit()
    db.refresh(new_schedule)
    
    for day_data in schedule.days:
        day = WorkScheduleDay(
            schedule_id=new_schedule.id,
            day_of_week=day_data.day_of_week,
            start_time=parse_time(day_data.start_time) if not day_data.is_day_off else None,
            end_time=parse_time(day_data.end_time) if not day_data.is_day_off else None,
            lunch_minutes=day_data.lunch_minutes,
            is_day_off=day_data.is_day_off
        )
        db.add(day)
    
    db.commit()
    db.refresh(new_schedule)
    
    # Собираем ответ вручную
    days_data = []
    week_norm = 0.0
    for day in sorted(new_schedule.days, key=lambda d: d.day_of_week):
        norm = calculate_day_norm(day.start_time, day.end_time, day.lunch_minutes, day.is_day_off)
        week_norm += norm
        days_data.append({
            "day_of_week": day.day_of_week,
            "day_name": DAY_NAMES[day.day_of_week],
            "start_time": day.start_time.strftime("%H:%M") if day.start_time else None,
            "end_time": day.end_time.strftime("%H:%M") if day.end_time else None,
            "lunch_minutes": day.lunch_minutes,
            "is_day_off": day.is_day_off,
            "norm_hours": norm
        })

    employee_count = db.query(Employee).filter(Employee.schedule_id == new_schedule.id).count()

    return {
        "id": new_schedule.id,
        "name": new_schedule.name,
        "week_norm_hours": round(week_norm, 2),
        "employee_count": employee_count,
        "days": days_data
}


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, schedule: ScheduleCreate, db: Session = Depends(get_db)):
    sched = db.query(WorkSchedule).filter(WorkSchedule.id == schedule_id).first()
    if not sched:
        raise HTTPException(status_code=404, detail="График не найден")
    
    sched.name = schedule.name
    
    # Удаляем старые дни
    db.query(WorkScheduleDay).filter(WorkScheduleDay.schedule_id == schedule_id).delete()
    
    # Создаём новые
    for day_data in schedule.days:
        day = WorkScheduleDay(
            schedule_id=schedule_id,
            day_of_week=day_data.day_of_week,
            start_time=parse_time(day_data.start_time) if not day_data.is_day_off else None,
            end_time=parse_time(day_data.end_time) if not day_data.is_day_off else None,
            lunch_minutes=day_data.lunch_minutes,
            is_day_off=day_data.is_day_off
        )
        db.add(day)
    
    db.commit()

    # Возвращаем обновлённый график
    sched = db.query(WorkSchedule).filter(WorkSchedule.id == schedule_id).first()

    days_data = []
    week_norm = 0.0
    for day in sorted(sched.days, key=lambda d: d.day_of_week):
        norm = calculate_day_norm(day.start_time, day.end_time, day.lunch_minutes, day.is_day_off)
        week_norm += norm
        days_data.append({
            "day_of_week": day.day_of_week,
            "day_name": DAY_NAMES[day.day_of_week],
            "start_time": day.start_time.strftime("%H:%M") if day.start_time else None,
            "end_time": day.end_time.strftime("%H:%M") if day.end_time else None,
            "lunch_minutes": day.lunch_minutes,
            "is_day_off": day.is_day_off,
            "norm_hours": norm
        })

    employee_count = db.query(Employee).filter(Employee.schedule_id == sched.id).count()

    return {
        "id": sched.id,
        "name": sched.name,
        "week_norm_hours": round(week_norm, 2),
        "employee_count": employee_count,
        "days": days_data
    }


@router.delete("/{schedule_id}")
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    sched = db.query(WorkSchedule).filter(WorkSchedule.id == schedule_id).first()
    if not sched:
        raise HTTPException(status_code=404, detail="График не найден")
    
    employee_count = db.query(Employee).filter(Employee.schedule_id == schedule_id).count()
    if employee_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя удалить график: к нему привязано {employee_count} сотрудников"
        )
    
    db.delete(sched)
    db.commit()
    return {"status": "ok"}


@router.get("/{schedule_id}/day/{day_of_week}")
def get_schedule_day(
    schedule_id: int,
    day_of_week: int,
    db: Session = Depends(get_db)
):
    """Получить расписание для конкретного дня недели (0=Пн, 6=Вс)"""
    day = db.query(WorkScheduleDay).filter(
        WorkScheduleDay.schedule_id == schedule_id,
        WorkScheduleDay.day_of_week == day_of_week
    ).first()
    
    if not day:
        raise HTTPException(status_code=404, detail="День не найден")
    
    return {
        "day_of_week": day.day_of_week,
        "day_name": DAY_NAMES[day.day_of_week],
        "start_time": day.start_time.strftime("%H:%M") if day.start_time else None,
        "end_time": day.end_time.strftime("%H:%M") if day.end_time else None,
        "lunch_minutes": day.lunch_minutes,
        "is_day_off": day.is_day_off,
        "norm_hours": calculate_day_norm(day.start_time, day.end_time, day.lunch_minutes, day.is_day_off)
    }