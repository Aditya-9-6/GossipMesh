"""Resolve multiple heads

Revision ID: 88ac4827f9d4
Revises: 674ba9fa3e87, cddd633f69ba, f00000000001
Create Date: 2026-10-14 03:54:11.868257

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "88ac4827f9d4"
down_revision: Union[str, Sequence[str], None] = ("674ba9fa3e87", "cddd633f69ba", "f00000000001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
