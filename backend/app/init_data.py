"""Инициализация справочников и учётных записей по умолчанию."""
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database import DATABASE_URL
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
    # username, password, full_name, is_admin, is_hr, timesheet_inspector, is_user
    ("admin", "admin123", "Администратор", True, False, True, True),
    ("hr",    "hr123",    "Кадровик",      False, True, True, True),
]


def seed(db: Session) -> None:
    # Справочник «Коды часов»
    for code, name, h_day, h_night in DEFAULT_TIME_CODES:
        if not db.query(TimeCode).filter(TimeCode.code == code).first():
            db.add(TimeCode(code=code, name=name, hours_day=h_day, hours_night=h_night))

    # Пользователи по умолчанию (создаются только если таблица users пуста)
    if db.query(User).count() == 0:
        for username, password, full_name, is_admin, is_hr, inspector, is_user in DEFAULT_USERS:
            db.add(User(
                username=username,
                full_name=full_name,
                hashed_password=hash_password(password),
                is_admin=is_admin,
                is_hr=is_hr,
                timesheet_inspector=inspector,
                is_user=is_user,
            ))
    db.commit()

    # Миграция: добавляем недостающие колонки в существующие таблицы (SQLite / PostgreSQL)
    _ensure_columns()


def _ensure_columns() -> None:
    """Добавляет новые колонки в уже созданные таблицы (простая авто-миграция)."""
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    migrations = [
        ("tabel_entries", "position", "INTEGER DEFAULT 0"),
        ("users", "is_user", "BOOLEAN DEFAULT 1"),
    ]
    with engine.begin() as conn:
        for table, column, coltype in migrations:
            if not inspector.has_table(table):
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
        # Существующим пользователям без ролей выдаём базовую роль «Пользователь»
        if "users" in {m[0] for m in migrations} and inspector.has_table("users"):
            try:
                conn.execute(text(
                    "UPDATE users SET is_user = 1 WHERE is_user IS NULL"
                ))
            except Exception:
                pass
