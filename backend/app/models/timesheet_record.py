from datetime import date, datetime
from sqlalchemy import Integer, Float, String, Date, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TimesheetRecord(Base):
    __tablename__ = 'timesheet_records'
    __table_args__ = (
        UniqueConstraint('employee_id', 'date', name='uq_timesheet_employee_date'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(Integer, ForeignKey('employees.id'))
    date: Mapped[date] = mapped_column(Date, nullable=False)

    first_in: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_out: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    fact_hours: Mapped[float] = mapped_column(Float, default=0)
    planned_hours: Mapped[float | None] = mapped_column(Float, nullable=True)  # заполняется вручную начальником
    default_hours: Mapped[float] = mapped_column(Float, default=8.0)  # норма из графика (WorkSchedule)
    overtime: Mapped[float | None] = mapped_column(Float, nullable=True)
    lunch_minutes: Mapped[int] = mapped_column(Integer, default=60)

    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    employee: Mapped['Employee'] = relationship('Employee')
