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
    ("users", "is_report", "BOOLEAN NOT NULL DEFAULT FALSE"),
    # Ручные итоговые колонки «КДУ» в табеле заполнения
    ("tabel_entries", "kdu_work_days", "NUMERIC(4,2)"),
    ("tabel_entries", "kdu_weekend_days", "NUMERIC(4,2)"),
    # Резервная норма часов (fallback; основная норма берётся из графика по дню недели)
    ("employees", "norm_hours", "NUMERIC(5,2) DEFAULT NULL"),
    # Ручные отметки проходной (добавлены вручную на странице «Пропущенные отметки»)
    ("turnstile_events", "is_manual", "BOOLEAN NOT NULL DEFAULT FALSE"),
    # Ручные смены (созданы вручную на вкладке «Смены»): время выхода смены
    ("turnstile_events", "shift_end", "TIMESTAMP NULL"),
    # Код часов «Время по графику»: часы берутся из нормы графика на день
    ("time_codes", "use_schedule_hours", "BOOLEAN NOT NULL DEFAULT FALSE"),
    # «Код для автозаполнения» в днях графика работы (функция «Заполнить по графику»)
    ("work_schedule_days", "auto_fill_code", "VARCHAR NULL"),
    # «Часы для выходного дня»: фиксированные часы кода в выходные (напр. 8 для «К»)
    ("time_codes", "weekend_hours", "NUMERIC(5,2) DEFAULT NULL"),
    # Роль «Документы и приказы» — ввод событий сотрудников для автозаполнения табеля
    ("users", "is_documents_manager", "BOOLEAN NOT NULL DEFAULT FALSE"),
    # Часы события в документе (автоподставляются из выбранного «Кода часов»)
    ("documents", "hours", "NUMERIC(5,2) DEFAULT NULL"),
    # Внутренняя категория типа документа (vacation/business_trip/sick/other) — цвет чипа
    ("documents", "doc_type_category", "VARCHAR(50) DEFAULT NULL"),
    ("timesheet_records", "document_code", "VARCHAR(10) DEFAULT NULL"),
    # Общий порог переработки (минуты) в настройках системы — применяется ко всем графикам
    ("company_settings", "overtime_threshold", "INTEGER NOT NULL DEFAULT 0"),
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
