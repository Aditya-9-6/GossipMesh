"""merge multiple heads

Revision ID: 8b258124f79c
Revises: 146ee27bb11f, 674ba9fa3e87, f00000000001
Create Date: 2024-03-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8b258124f79c'
down_revision: Union[str, None] = ('146ee27bb11f', '674ba9fa3e87', 'f00000000001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
