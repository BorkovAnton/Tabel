"""dismissal notes tables (увольнительные записки)

Revision ID: a1b2c3d4e5f6
Revises: 8f3d21a4c9e0
Create Date: 2026-10-12 00:00:00

Таблицы раздела «Увольнительные записки»:
  - dismissal_notes       — заголовок документа (период, подразделение);
  - dismissal_entries     — строка записки (сотрудник);
  - dismissal_day_records — дневная запись (время ухода/возврата, часы).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8f3d21a4c9e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'dismissal_notes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('period_start', sa.Date(), nullable=False),
        sa.Column('period_end', sa.Date(), nullable=False),
        sa.Column('department_id', sa.Integer(), sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('created_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
    )
    op.create_index('idx_dismissal_notes_period', 'dismissal_notes', ['period_start', 'period_end'])

    op.create_table(
        'dismissal_entries',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('note_id', sa.Integer(), sa.ForeignKey('dismissal_notes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('employee_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False),
    )
    op.create_index('idx_dismissal_entries_note', 'dismissal_entries', ['note_id'])

    op.create_table(
        'dismissal_day_records',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entry_id', sa.Integer(), sa.ForeignKey('dismissal_entries.id', ondelete='CASCADE'), nullable=False),
        sa.Column('day', sa.Integer(), nullable=False),
        sa.Column('time_out', sa.Time(), nullable=True),
        sa.Column('time_in', sa.Time(), nullable=True),
        sa.Column('hours', sa.Numeric(5, 2), server_default='0', nullable=True),
        sa.Column('comment', sa.String(100), nullable=True),
    )
    op.create_index('idx_dismissal_day_entry', 'dismissal_day_records', ['entry_id'])


def downgrade() -> None:
    op.drop_index('idx_dismissal_day_entry', table_name='dismissal_day_records')
    op.drop_table('dismissal_day_records')
    op.drop_index('idx_dismissal_entries_note', table_name='dismissal_entries')
    op.drop_table('dismissal_entries')
    op.drop_index('idx_dismissal_notes_period', table_name='dismissal_notes')
    op.drop_table('dismissal_notes')
