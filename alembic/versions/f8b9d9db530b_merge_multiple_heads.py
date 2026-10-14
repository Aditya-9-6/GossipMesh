"""merge multiple heads

Revision ID: f8b9d9db530b
Revises: 674ba9fa3e87, cddd633f69ba, f00000000001
Create Date: 2026-10-14 04:18:38.978300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8b9d9db530b'
down_revision: Union[str, Sequence[str], None] = ('674ba9fa3e87', 'cddd633f69ba', 'f00000000001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
