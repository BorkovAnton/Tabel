"""Инициализация справочников и учётных записей по умолчанию."""
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.time_code import TimeCode
from app.models.user import User

DEFAULT_TIME_CODES = [
    ("О",   "Отпуск",       0.0, 0.0),
    ("В",   "Выходной",     0.0, 0.0),
    ("ДМ",  "День матери",  8.0, 0.0),
    ("К",   "Командировка", 8.0, 0.0),
    ("МО",  "Медосмотр",    8.0, 0.0),
    ("8н",  "Ночные",       2.0, 6.0),
    ("8с",  "Сверхурочные", 8.0, 0.0),
]

DEFAULT_USERS = [
    # username, password, full_name, role, data_scope
    ("admin", "admin123", "Администратор", "admin", "all"),
    ("hr",    "hr123",    "Кадровик",      "hr",    "all"),
]


def seed(db: Session) -> None:
    # Справочник «Коды часов»
    for code, name, h_day, h_night in DEFAULT_TIME_CODES:
        if not db.query(TimeCode).filter(TimeCode.code == code).first():
            db.add(TimeCode(code=code, name=name, hours_day=h_day, hours_night=h_night))

    # Пользователи по умолчанию (создаются только если таблица users пуста)
    # ✅ ЭТАП 10: старые булевы флаги удалены — используются только role/data_scope.
    if db.query(User).count() == 0:
        for username, password, full_name, role, data_scope in DEFAULT_USERS:
            db.add(User(
                username=username,
                full_name=full_name,
                hashed_password=hash_password(password),
                role=role,
                data_scope=data_scope,
            ))
    db.commit()

    # Гарантируем, что у учётной записи admin стоит роль «Администратор»
    # (без неё не виден пункт меню «Пользователи»).
    fix_admin = db.query(User).filter(User.username == "admin").first()
    if fix_admin and fix_admin.role != "admin":
        fix_admin.role = "admin"
    if fix_admin and fix_admin.data_scope != "all":
        fix_admin.data_scope = "all"
    db.commit()

    # Миграция: добавляем недостающие колонки в существующие таблицы (SQLite / PostgreSQL)
    _ensure_columns()


def _ensure_columns() -> None:
    """Добавляет новые колонки в уже созданные таблицы (простая авто-миграция).

    ✅ ЭТАП 10: миграции старых полей (is_user, allowed_departments) удалены —
    полный список авто-миграций находится в app/init_db.py (ensure_columns()).
    """
    from app.init_db import ensure_columns as _ensure_all_columns
    _ensure_all_columns()
