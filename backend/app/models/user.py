import json

from sqlalchemy import Boolean, Integer, JSON, String
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
    # Видеть ВСЕ документы/приказы: роли admin/hr получают автоматически; остальным —
    # явно (например, опытному начальнику участка). Без права видны только
    # документы, созданные пользователем (Document.created_by == User.id).
    can_view_all_documents: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # ✅ Права доступа к вкладкам сайта: JSON-список путей страниц,
    # напр. ["/tabels", "/timesheet-report", "/employees"].
    # NULL/пусто — доступны все страницы (обратная совместимость).
    # ВНИМАНИЕ: это поле — часть НОВОЙ системы прав, НЕ удалять!
    permissions: Mapped[list | None] = mapped_column(JSON, nullable=True, default=None)

    # ✅ ЭТАП 10: старые поля прав УДАЛЕНЫ из модели и БД:
    # is_admin, is_hr, timesheet_inspector, is_user, is_report,
    # is_documents_manager, allowed_departments.
    # Разрешённые подразделения хранятся в allowed_department_ids_json (колонка выше).

    # Табельщик видит только те табели, где он ответственный
    responsible_for_all_departments: Mapped[bool] = mapped_column(Boolean, default=False)

    @property
    def allowed_department_ids(self) -> list[int]:
        """Список id разрешённых подразделений ([] если не задано).

        ЭТАП 10: источник — новая JSON-колонка allowed_department_ids_json
        (старая текстовая allowed_departments удалена).
        """
        try:
            data = self.allowed_department_ids_json
            if isinstance(data, str):
                data = json.loads(data or "[]")
            if not isinstance(data, list):
                return []
            return [int(x) for x in data if str(x).lstrip("-").isdigit()]
        except (ValueError, TypeError):
            return []

    @property
    def all_departments_allowed(self) -> bool:
        """ЭТАП 10: полный доступ ко всем подразделениям — по новой системе:
        роль admin или data_scope == 'all'."""
        return self.data_scope == "all" or self.role == "admin"
