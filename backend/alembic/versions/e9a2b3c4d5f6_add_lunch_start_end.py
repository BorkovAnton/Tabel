"""add lunch_start and lunch_end to work_schedule_days

Добавляет конкретный промежуток времени обеда в график работы.
Старое поле lunch_minutes остаётся для обратной совместимости;
для старых строк с заданным lunch_minutes заполняется промежуток
по умолчанию 12:00 -> 12:00 + lunch_minutes (если он ещё не задан).

Revision ID: e9a2b3c4d5f6
Revises: d8f1a2b3c4e5
Create Date: 2026-11-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = 'e9a2b3c4d5f6'
down_revision: Union[str, None] = 'd8f1a2b3c4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table: str) -> set:
    bind = op.get_bind()
    return {c["name"] for c in sa_inspect(bind).get_columns(table)}


def upgrade() -> None:
    cols = _column_names("work_schedule_days")
    if "lunch_start" not in cols:
        op.add_column(
            "work_schedule_days",
            sa.Column("lunch_start", sa.Time(), nullable=True),
        )
    if "lunch_end" not in cols:
        op.add_column(
            "work_schedule_days",
            sa.Column("lunch_end", sa.Time(), nullable=True),
        )

    # Перенос данных: старым графикам с обедом ставим промежуток по умолчанию
    # 12:00 .. 12:00+minutes (например lunch_minutes=30 -> 12:00..12:30).
    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id, lunch_minutes FROM work_schedule_days "
        "WHERE lunch_start IS NULL AND lunch_end IS NULL "
        "AND lunch_minutes IS NOT NULL AND lunch_minutes > 0"
    )).fetchall()
    for row in rows:
        minutes = int(row[1] or 0)
        start_h, start_m = 12, 0
        end_total = start_h * 60 + start_m + minutes
        end_h, end_m = divmod(end_total, 60)
        bind.execute(
            sa.text(
                "UPDATE work_schedule_days "
                "SET lunch_start = :ls, lunch_end = :le WHERE id = :rid"
            ),
            {
                "ls": f"{start_h:02d}:{start_m:02d}:00",
                "le": f"{end_h % 24:02d}:{end_m:02d}:00",
                "rid": row[0],
            },
        )


def downgrade() -> None:
    cols = _column_names("work_schedule_days")
    if "lunch_end" in cols:
        op.drop_column("work_schedule_days", "lunch_end")
    if "lunch_start" in cols:
        op.drop_column("work_schedule_days", "lunch_start")
