"""add version_id for concurrency

Revision ID: 1791908854
Revises: 524303fcc606
Create Date: 2026-10-13 16:27:34.467929

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1791908854"
down_revision: Union[str, Sequence[str], None] = "7b25e94872cd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # add version_id to workflows
    op.add_column("workflows", sa.Column("version_id", sa.Integer(), server_default="1", nullable=False))
    # add version_id to jobs
    op.add_column("jobs", sa.Column("version_id", sa.Integer(), server_default="1", nullable=False))
    # add version_id to repositories
    op.add_column("repositories", sa.Column("version_id", sa.Integer(), server_default="1", nullable=False))


def downgrade() -> None:
    op.drop_column("repositories", "version_id")
    op.drop_column("jobs", "version_id")
    op.drop_column("workflows", "version_id")
