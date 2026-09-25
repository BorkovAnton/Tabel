import json

from sqlalchemy import Boolean, Integer, String, Text
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

    # Права на подразделения: JSON-список id, напр. "[3, 7]".
    # Пусто/NULL — подразделений нет; "*" — все подразделения.
    allowed_departments: Mapped[str] = mapped_column(Text, default="")

    # Табельщик видит только те табели, где он ответственный
    responsible_for_all_departments: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def allowed_department_ids(self) -> list[int]:
        """Список id разрешённых подразделений ([] если не задано)."""
        try:
            data = json.loads(self.allowed_departments or "")
        except (ValueError, TypeError):
            return []
        if data == "*":
            return []
        return [int(x) for x in data if str(x).isdigit()]

    @property
    def all_departments_allowed(self) -> bool:
        raw = (self.allowed_departments or "").strip()
        if raw == "*":
            return True
        try:
            return json.loads(raw) == "*"
        except (ValueError, TypeError):
            return False
