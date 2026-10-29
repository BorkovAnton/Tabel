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
    # ─── Согласование табеля: роли в настройках ───
    ("company_settings", "hr_manager_id", "INTEGER REFERENCES users(id)"),
    ("company_settings", "security_specialist_id", "INTEGER REFERENCES users(id)"),
    # ─── Согласование табеля: workflow-поля в tabels ───
    ("tabels", "created_by", "INTEGER REFERENCES users(id)"),
    ("tabels", "hr_approved", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("tabels", "hr_approved_by", "INTEGER REFERENCES users(id)"),
    ("tabels", "hr_approved_at", "TIMESTAMP NULL"),
    ("tabels", "security_approved", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("tabels", "security_approved_by", "INTEGER REFERENCES users(id)"),
    ("tabels", "security_approved_at", "TIMESTAMP NULL"),
    # ─── Увольнительные записки: причина отсутствия (work/personal/undefined) ───
    ("dismissal_day_records", "reason", "VARCHAR(20) DEFAULT NULL"),
    # ✅ Права доступа к вкладкам сайта: JSON-список путей, NULL — все страницы
    ("users", "permissions", "JSON DEFAULT NULL"),
    # ─── Должность сотрудника (колонка «Должность» при импорте из Excel) ───
    ("employees", "position", "VARCHAR(200) DEFAULT NULL"),
    # ✅ ЭТАП 1: единая роль пользователя (старые флаги сохранены, логика не меняется)
    ("users", "role", "VARCHAR(20) NOT NULL DEFAULT 'user'"),
    # ─── ЭТАП 3: область видимости данных (логика пока не меняется) ───
    # 'own' — только свои табели, 'department' — своё подразделение,
    # 'custom' — выбранные подразделения, 'all' — все табели.
    ("users", "data_scope", "VARCHAR(20) NOT NULL DEFAULT 'own'"),
    # Список ID разрешённых подразделений (JSON); старое allowed_departments сохранено.
    ("users", "allowed_department_ids_json", "JSON DEFAULT NULL"),
    # ─── ЭТАП 4: специальные права (логика пока не меняется, DEFAULT FALSE) ───
    ("users", "can_approve", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_edit_references", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_view_salary", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_import", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_manage_users", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_view_all_tabels", "BOOLEAN NOT NULL DEFAULT FALSE"),
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

        # ─── ЭТАП 2: миграция данных — заполняем role по старым булевым флагам ───
        # Идемпотентна: можно запускать многократно, старые поля не изменяются.
        _sync_user_roles(conn, engine)


ROLE_SYNC_SQL = """
    UPDATE users SET role = CASE
        WHEN is_admin = TRUE THEN 'admin'
        WHEN is_hr = TRUE THEN 'hr'
        WHEN timesheet_inspector = TRUE THEN 'inspector'
        ELSE 'user'
    END
"""


def _sync_user_roles(conn, engine) -> None:
    """Заполняет users.role на основе старых флагов (ЭТАП 2).

    Выполняется только если в таблице users есть колонки role и все три
    старых флага. Идемпотентна: повторный запуск лишь переписывает те же
    значения. Булевы поля не читаются для записи и не изменяются.
    Приоритет ролей: admin > hr > inspector > user.
    """
    insp = inspect(engine)
    if not insp.has_table("users"):
        return
    user_cols = {c["name"] for c in insp.get_columns("users")}
    required = {"role", "is_admin", "is_hr", "timesheet_inspector"}
    if not required.issubset(user_cols):
        return

    print("[migrate] Этап 2: Обновление поля role на основе старых флагов...")
    result = conn.execute(text(ROLE_SYNC_SQL))
    print(f"[migrate] Этап 2: Поле role успешно обновлено "
          f"для существующих пользователей (rows={result.rowcount})")
