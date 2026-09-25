"""Простая авто-миграция: добавляет недостающие колонки в существующие таблицы.

Вызывается из main.py до create_all/seed, чтобы запросы к новым полям
(например users.is_user) не падали на старых базах PostgreSQL/SQLite.
"""
from sqlalchemy import create_engine, inspect, text

from app.database import DATABASE_URL

MIGRATIONS = [
    ("tabel_entries", "position", "INTEGER DEFAULT 0"),
    ("users", "is_user", "BOOLEAN NOT NULL DEFAULT TRUE"),
    ("users", "allowed_departments", "TEXT DEFAULT ''"),
]


def ensure_columns() -> None:
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, column, coltype in MIGRATIONS:
            if not inspector.has_table(table):
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column not in existing:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
                print(f"[migrate] {table}.{column} added")
