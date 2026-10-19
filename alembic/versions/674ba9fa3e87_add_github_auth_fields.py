"""Add GitHub auth fields

Revision ID: 674ba9fa3e87
Revises: 524303fcc606
Create Date: 2026-10-13 16:30:38.969887

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '674ba9fa3e87'
down_revision: Union[str, Sequence[str], None] = '524303fcc606'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # make hashed_password nullable
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('hashed_password',
                   existing_type=sa.VARCHAR(),
                   nullable=True)

    op.create_table('user_github_credentials',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('github_id', sa.Integer(), nullable=False),
    sa.Column('encrypted_access_token', sa.String(), nullable=False),
    sa.Column('encrypted_refresh_token', sa.String(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_user_github_credentials_github_id'), 'user_github_credentials', ['github_id'], unique=True)
    op.create_index(op.f('ix_user_github_credentials_id'), 'user_github_credentials', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_user_github_credentials_id'), table_name='user_github_credentials')
    op.drop_index(op.f('ix_user_github_credentials_github_id'), table_name='user_github_credentials')
    op.drop_table('user_github_credentials')

    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('hashed_password',
                   existing_type=sa.VARCHAR(),
                   nullable=False)
