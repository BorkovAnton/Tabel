"""add reason column to dismissal_day_records

Revision ID: d8f1a2b3c4e5
Revises: c7e9f0a1b2d3
Create Date: 2026-10-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect


# revision identifiers, used by Alembic.
revision: str = 'd8f1a2b3c4e5'
down_revision: Union[str, None] = 'c7e9f0a1b2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa_inspect(conn)
    if not insp.has_table('dismissal_day_records'):
        return
    existing = {c['name'] for c in insp.get_columns('dismissal_day_records')}
    if 'reason' not in existing:
        op.add_column('dismissal_day_records', sa.Column('reason', sa.String(20), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    insp = sa_inspect(conn)
    if not insp.has_table('dismissal_day_records'):
        return
    existing = {c['name'] for c in insp.get_columns('dismissal_day_records')}
    if 'reason' in existing:
        op.drop_column('dismissal_day_records', 'reason')
