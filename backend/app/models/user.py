import json

from sqlalchemy import Boolean, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # ✅ НОВОЕ ПОЛЕ (этап 1): единая роль. Пока не влияет на логику —
    # старые флаги ниже продолжают работать как раньше.
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user", server_default="user")

    # ✅ НОВЫЕ ПОЛЯ (этап 3): область видимости данных. Пока не влияет на логику.
    # 'own' — только свои табели, 'department' — своё подразделение,
    # 'custom' — выбранные подразделения (id в allowed_department_ids_json),
    # 'all' — все табели.
    data_scope: Mapped[str] = mapped_column(String(20), nullable=False, default="own", server_default="own")
    allowed_department_ids_json: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)

    # ✅ НОВЫЕ ПОЛЯ (этап 4): специальные права, независимые от базовой роли.
    # Пока не влияют на логику — только добавляются в модель и БД.
    can_approve: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    can_edit_references: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    can_view_salary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    can_import: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    can_manage_users: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    can_view_all_tabels: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # ✅ СТАРЫЕ ПОЛЯ (продолжают работать)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)          # Администратор
    is_hr: Mapped[bool] = mapped_column(Boolean, default=False)             # Кадровик
    timesheet_inspector: Mapped[bool] = mapped_column(Boolean, default=False)  # Инспектор табелей
    is_user: Mapped[bool] = mapped_column(Boolean, default=True)            # Пользователь (базовая роль)
    is_report: Mapped[bool] = mapped_column(Boolean, default=False)         # Отчёт (страница сводного отчёта часов)
    is_documents_manager: Mapped[bool] = mapped_column(Boolean, default=False)  # Документы и приказы

    # ✅ Права доступа к вкладкам сайта: JSON-список ключей страниц,
    # напр. ["tabels", "timesheet-report", "employees"].
    # NULL/пусто — доступны все страницы (обратная совместимость со старыми пользователями).
    permissions: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)

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
