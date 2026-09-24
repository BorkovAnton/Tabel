"""update timesheet_record fields for turnstile-based calculation

Revision ID: 8f3d21a4c9e0
Revises: c9cad34e1823
Create Date: 2026-09-09 00:00:00

Примечание: в репозитории отсутствует файл ревизии 'c9cad34e1823' (была
записана в alembic_version БД, но сам .py файл потерян/не закоммичен ранее).
Чтобы alembic мог строить историю на "чистых" окружениях, down_revision
указан как None (миграция становится новой базовой точкой). На окружении,
где alembic_version уже содержит 'c9cad34e1823', апгрейд этой ревизии был
применён вручную через SQL — таблица alembic_version обновлена на
'8f3d21a4c9e0' напрямую.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f3d21a4c9e0'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Новые поля для расчёта табеля по событиям проходной
    op.add_column('timesheet_records', sa.Column('first_in', sa.DateTime(), nullable=True))
    op.add_column('timesheet_records', sa.Column('last_out', sa.DateTime(), nullable=True))
    op.add_column('timesheet_records', sa.Column('default_hours', sa.Float(), nullable=False, server_default='8.0'))
    op.add_column('timesheet_records', sa.Column('overtime', sa.Float(), nullable=True))
    op.add_column('timesheet_records', sa.Column('lunch_minutes', sa.Integer(), nullable=False, server_default='60'))
    op.add_column('timesheet_records', sa.Column('needs_review', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('timesheet_records', sa.Column('review_reason', sa.String(length=255), nullable=True))

    # fact_hours теперь обязателен (по умолчанию 0)
    op.alter_column(
        'timesheet_records', 'fact_hours',
        existing_type=sa.Float(),
        nullable=False,
        server_default='0',
    )

    # Убираем поля, использовавшиеся в старой логике расчёта по графику
    op.drop_column('timesheet_records', 'absence_type')
    op.drop_column('timesheet_records', 'manual_overtime')
    op.drop_column('timesheet_records', 'calculated_overtime')

    # Одна запись табеля на сотрудника за день
    op.create_unique_constraint(
        'uq_timesheet_employee_date', 'timesheet_records', ['employee_id', 'date']
    )


def downgrade() -> None:
    op.drop_constraint('uq_timesheet_employee_date', 'timesheet_records', type_='unique')

    op.add_column('timesheet_records', sa.Column('calculated_overtime', sa.Float(), nullable=False, server_default='0'))
    op.add_column('timesheet_records', sa.Column('manual_overtime', sa.Float(), nullable=False, server_default='0'))
    op.add_column('timesheet_records', sa.Column('absence_type', sa.String(length=50), nullable=True))

    op.alter_column(
        'timesheet_records', 'fact_hours',
        existing_type=sa.Float(),
        nullable=True,
        server_default=None,
    )

    op.drop_column('timesheet_records', 'review_reason')
    op.drop_column('timesheet_records', 'needs_review')
    op.drop_column('timesheet_records', 'lunch_minutes')
    op.drop_column('timesheet_records', 'overtime')
    op.drop_column('timesheet_records', 'default_hours')
    op.drop_column('timesheet_records', 'last_out')
    op.drop_column('timesheet_records', 'first_in')
