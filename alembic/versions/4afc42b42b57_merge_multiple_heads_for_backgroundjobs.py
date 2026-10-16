"""Merge multiple heads for BackgroundJobs

Revision ID: 4afc42b42b57
Revises: 1791908854, 88ac4827f9d4, 8b258124f79c, b8c340ac7a9e, f10000000000
Create Date: 2026-10-15 16:47:25.184846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4afc42b42b57'
down_revision: Union[str, Sequence[str], None] = ('1791908854', '88ac4827f9d4', '8b258124f79c', 'b8c340ac7a9e', 'f10000000000')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
