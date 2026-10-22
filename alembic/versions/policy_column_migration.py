"""add policy column to repository

Revision ID: f30000000000
Revises: 8b258124f79c, 88ac4827f9d4, c19a0a1f0a2d, f10000000002, def6dd2b0f44
Create Date: 2024-10-16 16:21:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f30000000000'
down_revision: Union[str, Sequence[str], None] = ('8b258124f79c', '88ac4827f9d4', 'c19a0a1f0a2d', 'f10000000002', 'def6dd2b0f44')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('policy', sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.drop_column('policy')
