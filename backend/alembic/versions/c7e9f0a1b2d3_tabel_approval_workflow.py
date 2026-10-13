"""tabel approval workflow (согласование табеля)

Revision ID: c7e9f0a1b2d3
Revises: a1b2c3d4e5f6
Create Date: 2026-10-13 00:00:00

Система согласования табеля с тремя ролями:
  - tabels: created_by, hr_approved/_by/_at, security_approved/_by/_at;
  - company_settings: hr_manager_id, security_specialist_id.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7e9f0a1b2d3'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Роли согласования в настройках предприятия
    with op.batch_alter_table('company_settings') as batch_op:
        batch_op.add_column(sa.Column('hr_manager_id', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('security_specialist_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_company_settings_hr_manager', 'users', ['hr_manager_id'], ['id'])
        batch_op.create_foreign_key(
            'fk_company_settings_security_specialist', 'users', ['security_specialist_id'], ['id'])

    # Workflow-поля табеля
    with op.batch_alter_table('tabels') as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('hr_approved', sa.Boolean(), nullable=False,
                                      server_default=sa.false()))
        batch_op.add_column(sa.Column('hr_approved_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('hr_approved_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('security_approved', sa.Boolean(), nullable=False,
                                      server_default=sa.false()))
        batch_op.add_column(sa.Column('security_approved_by', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('security_approved_at', sa.DateTime(), nullable=True))
        batch_op.create_foreign_key('fk_tabels_created_by', 'users', ['created_by'], ['id'])
        batch_op.create_foreign_key('fk_tabels_hr_approved_by', 'users', ['hr_approved_by'], ['id'])
        batch_op.create_foreign_key('fk_tabels_security_approved_by', 'users', ['security_approved_by'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('tabels') as batch_op:
        batch_op.drop_constraint('fk_tabels_security_approved_by', type_='foreignkey')
        batch_op.drop_constraint('fk_tabels_hr_approved_by', type_='foreignkey')
        batch_op.drop_constraint('fk_tabels_created_by', type_='foreignkey')
        batch_op.drop_column('security_approved_at')
        batch_op.drop_column('security_approved_by')
        batch_op.drop_column('security_approved')
        batch_op.drop_column('hr_approved_at')
        batch_op.drop_column('hr_approved_by')
        batch_op.drop_column('hr_approved')
        batch_op.drop_column('created_by')

    with op.batch_alter_table('company_settings') as batch_op:
        batch_op.drop_constraint('fk_company_settings_security_specialist', type_='foreignkey')
        batch_op.drop_constraint('fk_company_settings_hr_manager', type_='foreignkey')
        batch_op.drop_column('security_specialist_id')
        batch_op.drop_column('hr_manager_id')
