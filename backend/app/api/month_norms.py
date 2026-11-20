from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.holiday_calendar import HolidayCalendar
from app.models.month_norm import MonthNorm

router = APIRouter(prefix="/month-norms", tags=["Month Norms"])


class MonthNormCreate(BaseModel):
    year: int
    month: int
    norm_hours: float
    working_days: int


class MonthNormResponse(BaseModel):
    id: int
    year: int
    month: int
    norm_hours: float
    working_days: int

    class Config:
        from_attributes = True


@router.get("/", response_model=List[MonthNormResponse])
def list_norms(year: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(MonthNorm)
    if year:
        q = q.filter(MonthNorm.year == year)
    return q.order_by(MonthNorm.year, MonthNorm.month).all()


@router.post("/", response_model=MonthNormResponse)
def create_norm(norm: MonthNormCreate, db: Session = Depends(get_db)):
    existing = db.query(MonthNorm).filter(
        MonthNorm.year == norm.year,
        MonthNorm.month == norm.month
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Норма на этот месяц уже существует")

    db_norm = MonthNorm(
        year=norm.year,
        month=norm.month,
        norm_hours=norm.norm_hours,
        working_days=norm.working_days,
    )
    db.add(db_norm)
    db.commit()
    db.refresh(db_norm)
    return db_norm


@router.put("/{norm_id}", response_model=MonthNormResponse)
def update_norm(norm_id: int, norm: MonthNormCreate, db: Session = Depends(get_db)):
    db_norm = db.query(MonthNorm).filter(MonthNorm.id == norm_id).first()
    if not db_norm:
        raise HTTPException(status_code=404, detail="Норма не найдена")

    db_norm.year = norm.year
    db_norm.month = norm.month
    db_norm.norm_hours = norm.norm_hours
    db_norm.working_days = norm.working_days
    db.commit()
    db.refresh(db_norm)
    return db_norm


@router.delete("/{norm_id}")
def delete_norm(norm_id: int, db: Session = Depends(get_db)):
    db_norm = db.query(MonthNorm).filter(MonthNorm.id == norm_id).first()
    if not db_norm:
        raise HTTPException(status_code=404, detail="Норма не найдена")
    db.delete(db_norm)
    db.commit()
    return {"ok": True}


@router.post("/auto-calculate")
def auto_calculate_norms(year: int, db: Session = Depends(get_db)):
    """Автоматический расчёт норм рабочего времени на год по производственному календарю.

    Формула: (рабочие дни × 8) − предпраздничные часы.
    Предпраздничный день — рабочий день, за которым следует праздник.
    """
    created = 0
    updated = 0
    # Проверка: есть ли загруженный производственный календарь на этот год
    cal_count = db.query(HolidayCalendar).filter(
        HolidayCalendar.date >= date(year, 1, 1),
        HolidayCalendar.date <= date(year, 12, 31),
    ).count()
    if cal_count == 0:
        raise HTTPException(
            status_code=400,
            detail=f"Производственный календарь на {year} год не загружен. "
                   f"Сначала загрузите его в разделе «Производственный календарь» (Год: {year}).",
        )

    for month in range(1, 13):
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(year, month + 1, 1) - timedelta(days=1)

        days = db.query(HolidayCalendar).filter(
            HolidayCalendar.date >= first_day,
            HolidayCalendar.date <= last_day,
        ).order_by(HolidayCalendar.date).all()

        working_days = [d for d in days if not d.is_holiday and not d.is_weekend]
        working_days_count = len(working_days)

        # Предпраздничные дни: рабочий день, за которым идёт праздник
        pre_holiday_count = 0
        for wd in working_days:
            next_day = wd.date + timedelta(days=1)
            is_next_holiday = db.query(HolidayCalendar).filter(
                HolidayCalendar.date == next_day,
                HolidayCalendar.is_holiday == True,  # noqa: E712
            ).first()
            if is_next_holiday:
                pre_holiday_count += 1

        norm_hours = float(working_days_count * 8 - pre_holiday_count)

        existing = db.query(MonthNorm).filter(
            MonthNorm.year == year,
            MonthNorm.month == month,
        ).first()

        if existing:
            existing.norm_hours = norm_hours
            existing.working_days = working_days_count
            updated += 1
        else:
            db.add(MonthNorm(
                year=year,
                month=month,
                norm_hours=norm_hours,
                working_days=working_days_count,
            ))
            created += 1

    db.commit()

    return {
        "ok": True,
        "year": year,
        "created": created,
        "updated": updated,
        "message": f"Нормы на {year} год рассчитаны: создано {created}, обновлено {updated}",
    }