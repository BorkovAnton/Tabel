"""sync lunch_minutes with lunch interval

Пересчитывает legacy-колонку work_schedule_days.lunch_minutes по новому
правилу: длина валидного промежутка обеда (lunch_start/lunch_end оба заданы
и lunch_end > lunch_start), иначе 0. Делает БД согласованной с логикой
расчёта нормы (lunch_deduction_minutes).

Revision ID: f0b3c4d5e6a7
Revises: e9a2b3c4d5f6
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f0b3c4d5e6a7'
down_revision: Union[str, None] = 'e9a2b3c4d5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE work_schedule_days
        SET lunch_minutes = CASE
            WHEN lunch_start IS NOT NULL
                 AND lunch_end IS NOT NULL
                 AND lunch_end > lunch_start
            THEN EXTRACT(EPOCH FROM (lunch_end - lunch_start))::int / 60
            ELSE 0
        END
        """
    )


def downgrade() -> None:
    # Данные (legacy lunch_minutes) перезаписываются безвозвратно;
    # откат не предусмотрен.
    pass
