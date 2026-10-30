"""Простая авто-миграция: добавляет недостающие колонки в существующие таблицы.

Вызывается из main.py до create_all/seed, чтобы запросы к новым полям
не падали на старых базах PostgreSQL/SQLite.

ЭТАП 10: список миграций очищен от старых полей прав (is_user, is_report,
is_documents_manager, allowed_departments — они больше не создаются).
Добавлена DROP-миграция, удаляющая старые колонки из существующих баз;
перед удалением автоматически создаётся резервная копия users_backup_stage10.
"""
from sqlalchemy import create_engine, inspect, text

from app.database import DATABASE_URL

MIGRATIONS = [
    ("tabel_entries", "position", "INTEGER DEFAULT 0"),
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
    # ✅ ЭТАП 1: единая роль пользователя
    ("users", "role", "VARCHAR(20) NOT NULL DEFAULT 'user'"),
    # ─── ЭТАП 3: область видимости данных ───
    # 'own' — только свои табели, 'department' — своё подразделение,
    # 'custom' — выбранные подразделения, 'all' — все табели.
    ("users", "data_scope", "VARCHAR(20) NOT NULL DEFAULT 'own'"),
    # Список ID разрешённых подразделений (JSON); заменил старое allowed_departments.
    ("users", "allowed_department_ids_json", "JSON DEFAULT NULL"),
    # ─── ЭТАП 4: специальные права ───
    ("users", "can_approve", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_edit_references", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_view_salary", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_import", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_manage_users", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("users", "can_view_all_tabels", "BOOLEAN NOT NULL DEFAULT FALSE"),
]

# ✅ ЭТАП 10: старые колонки прав, подлежащие удалению из существующих БД.
LEGACY_DROP_COLUMNS = [
    "is_admin",
    "is_hr",
    "timesheet_inspector",
    "is_user",
    "is_report",
    "is_documents_manager",
    "allowed_departments",
]


def ensure_columns() -> None:
    """Добавляет недостающие колонки из MIGRATIONS и выполняет миграции данных.

    Диагностика (почему раньше «миграции не срабатывали»):
    1. INSPECTCache-проблема: один Inspector кэширует результат has_table() и
       get_columns() на весь свой жизненный цикл. Теперь для каждой таблицы
       создаётся НОВЫЙ inspector сразу перед проверкой — метаданные всегда свежие.
    2. Движок переиспользуется от app.database.engine (общий пул соединений),
       а не создаётся новый — меньше подключений и нет рассинхрона состояния.
    3. Все шаги логируются с префиксом [migrate], включая COMMIT транзакции,
       чтобы по логам было видно, где именно обрывается процесс.
    """
    print("[migrate] === НАЧАЛО МИГРАЦИИ ===")
    print(f"[migrate] DATABASE_URL: {DATABASE_URL[:50]}...")

    # Переиспользуем общий движок приложения (app.database.engine)
    from app.database import engine
    dialect = engine.url.get_dialect().name  # 'postgresql' / 'sqlite' / ...
    supports_if_not_exists = dialect.startswith("postgresql")
    with engine.connect() as probe:
        tables = inspect(probe).get_table_names()
    print(f"[migrate] Подключение к БД установлено (dialect: {dialect})")
    print(f"[migrate] Таблицы в БД: {sorted(tables)}")
    print(f"[migrate] Всего миграций в списке: {len(MIGRATIONS)}")

    added = 0
    skipped_exists = 0
    skipped_no_table = 0
    errors = []

    with engine.begin() as conn:
        print("[migrate] Транзакция открыта (engine.begin(), авто-COMMIT при выходе)")

        for table, column, coltype in MIGRATIONS:
            print(f"[migrate] Проверяем {table}.{column}...")

            # ВАЖНО: новый inspector на каждую проверку — иначе SQLAlchemy
            # отдаёт закэшированный список таблиц/колонок (кэш живёт в Inspector).
            insp = inspect(conn)
            if not insp.has_table(table):
                print(f"[migrate]   Таблица {table} не существует, пропускаем")
                skipped_no_table += 1
                continue

            try:
                existing = {c["name"] for c in insp.get_columns(table)}
            except Exception as e:  # таблица могла появиться позже списка
                print(f"[migrate]   ❌ Не удалось прочитать колонки {table}: {e}")
                errors.append((table, column, str(e)))
                continue

            if column not in existing:
                print(f"[migrate]   Колонка {column} отсутствует, добавляем...")
                try:
                    if supports_if_not_exists:
                        # PostgreSQL 9.6+: двойная защита от гонки/рассинхрона
                        conn.execute(text(
                            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {coltype}"
                        ))
                    else:
                        # SQLite и прочие не поддерживают IF NOT EXISTS в ALTER TABLE
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
                    print(f"[migrate]   ✅ {table}.{column} добавлена")
                    added += 1
                except Exception as e2:
                    print(f"[migrate]   ❌ Ошибка при добавлении {table}.{column}: {e2}")
                    errors.append((table, column, str(e2)))
                    raise
            else:
                print(f"[migrate]   Колонка {column} уже существует")
                skipped_exists += 1

        # ─── ЭТАП 10: удаление старых колонок прав (с резервной копией таблицы) ───
        _drop_legacy_columns(conn)

    # Выход из engine.begin() = COMMIT (если не было исключений).
    print(f"[migrate] Транзакция зафиксирована (COMMIT выполнен)")
    print(f"[migrate] ИТОГ: добавлено={added}, уже существовало={skipped_exists}, "
          f"нет таблицы={skipped_no_table}, ошибок={len(errors)}")
    print("[migrate] === МИГРАЦИЯ ЗАВЕРШЕНА ===")


def _drop_legacy_columns(conn) -> None:
    """ЭТАП 10: удаляет старые колонки прав из таблицы users.

    Идемпотентна: если колонок нет — ничего не делает. Перед первым удалением
    создаёт резервную копию всей таблицы users в users_backup_stage10
    (если такой ещё нет), чтобы данные можно было восстановить.

    Замечание: раньше здесь выполнялась миграция ROLE_SYNC_SQL (заполнение
    role по старым флагам, Этап 2). К этому моменту она многократно выполнена
    на всех рабочих базах, поэтому удалена вместе со старыми колонками.
    """
    insp = inspect(conn)
    if not insp.has_table("users"):
        print("[migrate] Этап 10: таблица users отсутствует, пропускаем")
        return
    existing = {c["name"] for c in insp.get_columns("users")}
    to_drop = [c for c in LEGACY_DROP_COLUMNS if c in existing]
    if not to_drop:
        print("[migrate] Этап 10: старых колонок нет — база уже чистая")
        return

    tables = set(insp.get_table_names())
    if "users_backup_stage10" not in tables:
        conn.execute(text("CREATE TABLE users_backup_stage10 AS SELECT * FROM users"))
        print("[migrate] Этап 10: ✅ создана резервная копия users_backup_stage10")

    dialect = conn.engine.url.get_dialect().name
    if_exists = "IF EXISTS" if dialect.startswith("postgresql") else ""
    for col in to_drop:
        conn.execute(text(f"ALTER TABLE users DROP COLUMN {if_exists} {col}"))
        print(f"[migrate] Этап 10: ✅ удалена колонка users.{col}")
