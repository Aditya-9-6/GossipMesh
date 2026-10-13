"""Add organization owner and projects

Revision ID: cddd633f69ba
Revises: 524303fcc606
Create Date: 2026-10-13 16:28:10.849395

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cddd633f69ba'
down_revision: Union[str, Sequence[str], None] = '524303fcc606'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('organization_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_organization_id'), 'projects', ['organization_id'], unique=False)

    op.add_column('organizations', sa.Column('owner_id', sa.Integer(), nullable=True))

    # We must provide a default for owner_id or set it after adding the column.
    # However, since we don't know the owner_id for existing orgs, we'll just add the column and make it non-nullable later if needed,
    # or handle it in the application. For now we just add it and add the foreign key.

    # In sqlite ALTER TABLE ADD CONSTRAINT is not fully supported, so we will do batch operations for sqlite compatibility
    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.create_foreign_key('fk_organizations_owner_id_users', 'users', ['owner_id'], ['id'])

    with op.batch_alter_table('user_organizations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(), server_default='active', nullable=False))

    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.add_column(sa.Column('project_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_repositories_project_id'), ['project_id'], unique=False)
        batch_op.create_foreign_key('fk_repositories_project_id_projects', 'projects', ['project_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('repositories', schema=None) as batch_op:
        batch_op.drop_constraint('fk_repositories_project_id_projects', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_repositories_project_id'))
        batch_op.drop_column('project_id')

    with op.batch_alter_table('user_organizations', schema=None) as batch_op:
        batch_op.drop_column('status')

    with op.batch_alter_table('organizations', schema=None) as batch_op:
        batch_op.drop_constraint('fk_organizations_owner_id_users', type_='foreignkey')
        batch_op.drop_column('owner_id')

    op.drop_index(op.f('ix_projects_organization_id'), table_name='projects')
    op.drop_index(op.f('ix_projects_id'), table_name='projects')
    op.drop_table('projects')
