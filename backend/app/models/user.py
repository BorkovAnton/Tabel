from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)          # Администратор
    is_hr: Mapped[bool] = mapped_column(Boolean, default=False)             # Кадровик
    timesheet_inspector: Mapped[bool] = mapped_column(Boolean, default=False)  # Инспектор табелей
    is_user: Mapped[bool] = mapped_column(Boolean, default=True)            # Пользователь (базовая роль)

    # Табельщик видит только те табели, где он ответственный
    responsible_for_all_departments: Mapped[bool] = mapped_column(Boolean, default=False)
