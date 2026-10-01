from sqlalchemy import Column, Boolean, Integer, String, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TimeCode(Base):
    """Справочник 'Коды часов' (нефиксированный, записи можно добавлять)."""
    __tablename__ = "time_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    hours_day: Mapped[float] = mapped_column(Float, default=0.0)   # часов день
    hours_night: Mapped[float] = mapped_column(Float, default=0.0) # часов ночь
    # «Время по графику»: для этого кода часы берутся из нормы графика работы
    # на конкретный день (командировка в пн = 8.25ч, в пт = 7ч и т.п.),
    # а не из фиксированных hours_day/hours_night.
    use_schedule_hours: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    destinations = Column(JSON, default=list)
