from sqlalchemy import Boolean, Integer, String, Float
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
