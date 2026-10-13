from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    # Порог переработки в минутах (общий для всех графиков).
    # Превышение нормы <= порога не считается сверхурочным. 0 = считать любую переработку.
    overtime_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ─── Роли согласования табеля ───
    # Начальник отдела кадров: проверяет табель после создателя.
    hr_manager_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    # Специалист службы безопасности: финальная проверка после кадровика.
    security_specialist_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)

    hr_manager: Mapped["User | None"] = relationship("User", foreign_keys=[hr_manager_id])
    security_specialist: Mapped["User | None"] = relationship("User", foreign_keys=[security_specialist_id])
