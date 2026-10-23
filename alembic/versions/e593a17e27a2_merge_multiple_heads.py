"""Merge multiple heads

Revision ID: e593a17e27a2
Revises: 674ba9fa3e87, cddd633f69ba, f00000000001
Create Date: 2026-10-16 04:35:35.812269

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e593a17e27a2"
down_revision: Union[str, Sequence[str], None] = ("674ba9fa3e87", "cddd633f69ba", "f00000000001")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
