"""Add overage fields to subscriptions

Revision ID: 003
Revises: 002
Create Date: 2026-01-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add overage fields to subscriptions table
    op.add_column('subscriptions', sa.Column('overage_enabled', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('subscriptions', sa.Column('overage_limit', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('subscriptions', 'overage_limit')
    op.drop_column('subscriptions', 'overage_enabled')

