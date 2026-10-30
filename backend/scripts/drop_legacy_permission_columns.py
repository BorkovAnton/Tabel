"""ЭТАП 10: финальная очистка — удаление старых колонок прав из таблицы users.

Удаляет колонки:
    is_admin, is_hr, timesheet_inspector, is_user, is_report,
    is_documents_manager, allowed_departments

НЕ трогает: permissions, allowed_department_ids_json, role, data_scope, can_*.

Использование (из папки backend/):
    python scripts/drop_legacy_permission_columns.py            # только dry-run (без изменений)
    python scripts/drop_legacy_permission_columns.py --execute  # реальное удаление

Перед удалением автоматически создаётся резервная копия таблицы users
(таблица users_backup_stage10 с полным дампом всех колонок), поэтому даже
при ошибке данные можно восстановить. Дополнительно сделайте дамп всей БД:
    docker-compose exec postgres pg_dump -U user tabel > backup_before_cleanup_<дата>.sql
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, text  # noqa: E402

from app.database import engine  # noqa: E402

LEGACY_COLUMNS = [
    "is_admin",
    "is_hr",
    "timesheet_inspector",
    "is_user",
    "is_report",
    "is_documents_manager",
    "allowed_departments",
]

KEEP = ["role", "data_scope", "allowed_department_ids_json", "permissions",
        "can_approve", "can_edit_references", "can_view_salary", "can_import",
        "can_manage_users", "can_view_all_tabels"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Удаление старых колонок прав (Этап 10)")
    parser.add_argument("--execute", action="store_true",
                        help="Выполнить удаление (по умолчанию — только dry-run)")
    args = parser.parse_args()

    with engine.connect() as conn:
        insp = inspect(conn)
        if not insp.has_table("users"):
            print("Таблица users не найдена — ничего делать не нужно.")
            return 0
        existing = {c["name"] for c in insp.get_columns("users")}
        to_drop = [c for c in LEGACY_COLUMNS if c in existing]

        print(f"Колонки для удаления: {to_drop or 'нет (уже удалены)'}")
        missing_keep = [c for c in KEEP if c not in existing]
        if missing_keep:
            print(f"⚠️  Осторожно: отсутствуют новые колонки: {missing_keep}. "
                  f"Сначала обновите схему (миграции запустятся сами при старте бэкенда).")

        if not to_drop:
            print("Старых колонок нет — база уже чистая.")
            return 0

        if not args.execute:
            print("DRY-RUN: ничего не изменено. Для запуска добавьте --execute")
            return 0

        # 1) Резервная копия всей таблицы users (если ещё не создана)
        if "users_backup_stage10" not in insp.get_table_names():
            conn.execute(text("CREATE TABLE users_backup_stage10 AS SELECT * FROM users"))
            print("✅ Создана резервная копия: таблица users_backup_stage10")
        else:
            print("Резервная копия users_backup_stage10 уже существует — пропускаем")

        # 2) Удаление старых колонок (PostgreSQL поддерживает IF EXISTS; SQLite 3.35+ — тоже)
        dialect = engine.url.get_dialect().name
        for col in to_drop:
            if_exists = "IF EXISTS" if dialect.startswith("postgresql") else ""
            conn.execute(text(f"ALTER TABLE users DROP COLUMN {if_exists} {col}"))
            print(f"✅ Удалена колонка: users.{col}")

        conn.commit()

        # 3) Проверка результата
        insp2 = inspect(engine.connect())
        left = {c["name"] for c in insp2.get_columns("users")}
        gone = [c for c in LEGACY_COLUMNS if c not in left]
        print(f"ИТОГ: удалено {len(gone)} из {len(to_drop)}. "
              f"Оставшиеся колонки users: {sorted(left)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
