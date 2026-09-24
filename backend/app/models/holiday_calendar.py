from datetime import date
from sqlalchemy import Integer, Boolean, Date, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class HolidayCalendar(Base):
    __tablename__ = 'holiday_calendars'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False)
    is_weekend: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str] = mapped_column(String(2), default='BY')
