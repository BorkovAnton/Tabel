from sqlalchemy import Integer, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime

from app.database import Base


class UserPrintSettings(Base):
    """Настройки печати для пользователя.

    Персональный список итоговых колонок, которые отображаются
    в печатной форме Т-13. selected_columns = NULL — все колонки.
    """
    __tablename__ = "user_print_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    selected_columns: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=None)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
