from datetime import date, time, datetime
from typing import Optional
from sqlalchemy import Integer, Date, DateTime, Time, Numeric, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class DismissalNote(Base):
    """Увольнительная записка (заголовок)"""
    __tablename__ = "dismissal_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    department_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("departments.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    entries: Mapped[list["DismissalEntry"]] = relationship(
        "DismissalEntry", back_populates="note", cascade="all, delete-orphan"
    )


class DismissalEntry(Base):
    """Строка увольнительной записки (сотрудник)"""
    __tablename__ = "dismissal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    note_id: Mapped[int] = mapped_column(Integer, ForeignKey("dismissal_notes.id", ondelete="CASCADE"), nullable=False)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey("employees.id"), nullable=False)

    note: Mapped["DismissalNote"] = relationship("DismissalNote", back_populates="entries")
    employee: Mapped["Employee"] = relationship("Employee")
    day_records: Mapped[list["DismissalDayRecord"]] = relationship(
        "DismissalDayRecord", back_populates="entry", cascade="all, delete-orphan"
    )


class DismissalDayRecord(Base):
    """Запись за конкретный день (время ухода и возврата)"""
    __tablename__ = "dismissal_day_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(Integer, ForeignKey("dismissal_entries.id", ondelete="CASCADE"), nullable=False)
    day: Mapped[int] = mapped_column(Integer, nullable=False)
    time_out: Mapped[time | None] = mapped_column(Time, nullable=True)
    time_in: Mapped[time | None] = mapped_column(Time, nullable=True)
    hours: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    comment: Mapped[str | None] = mapped_column(String(100), nullable=True)

    entry: Mapped["DismissalEntry"] = relationship("DismissalEntry", back_populates="day_records")
