from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
import os
import sys

# Добавляем путь к проекту в PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Импортируем модели
from app.models.base import Base
target_metadata = Base.metadata

# Для совместимости с autogenerate
from app.models.department import Department  # noqa: F401
from app.models.work_schedule import WorkSchedule  # noqa: F401
from app.models.employee import Employee  # noqa: F401
from app.models.turnstile_event import TurnstileEvent  # noqa: F401
from app.models.timesheet_record import TimesheetRecord  # noqa: F401
from app.models.holiday_calendar import HolidayCalendar  # noqa: F401
from app.models.unrecognized_mapping import UnrecognizedMapping  # noqa: F401

# Указываем целевую метаданную
target_metadata = Base.metadata

# Конфигурация Alembic
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()