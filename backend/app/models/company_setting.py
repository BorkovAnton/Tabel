from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CompanySetting(Base):
    """Настройки предприятия: название и руководитель.

    Используется в печатных формах табелей, отчетах Excel и шапках документов.
    Хранится одна запись (id=1).
    """
    __tablename__ = "company_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    director_position: Mapped[str] = mapped_column(String(100), nullable=False, default="Генеральный директор")
    director_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
