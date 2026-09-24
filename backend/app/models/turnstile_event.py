from datetime import datetime
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class TurnstileEvent(Base):
    __tablename__ = 'turnstile_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_name: Mapped[str] = mapped_column(String(255), nullable=False)
    employee_id: Mapped[int | None] = mapped_column(Integer, ForeignKey('employees.id'), nullable=True)
    event_type: Mapped[str] = mapped_column(String(10), nullable=False)
    datetime: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_recognized: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    employee: Mapped['Employee'] = relationship('Employee')