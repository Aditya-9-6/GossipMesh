"""merge multiple heads

Revision ID: 83a8d81c7e7f
Revises: 1791908854, c19a0a1f0a2d
Create Date: 2026-10-14 05:32:05.415663

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '83a8d81c7e7f'
down_revision: Union[str, Sequence[str], None] = ('1791908854', 'f8b9d9db530b', 'c19a0a1f0a2d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
