"""Add webhook retries and installation

Revision ID: f10000000002
Revises: f10000000000
Create Date: 2024-10-16 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f10000000002"
down_revision = "f10000000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("webhook_events", schema=None) as batch_op:
        batch_op.add_column(sa.Column("retries", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("installation_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("organization_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_webhook_events_installation_id"), ["installation_id"], unique=False)
        batch_op.create_index(batch_op.f("ix_webhook_events_organization_id"), ["organization_id"], unique=False)
        batch_op.create_foreign_key("fk_webhook_events_organization_id", "organizations", ["organization_id"], ["id"])


def downgrade() -> None:
    with op.batch_alter_table("webhook_events", schema=None) as batch_op:
        batch_op.drop_constraint("fk_webhook_events_organization_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_webhook_events_organization_id"))
        batch_op.drop_index(batch_op.f("ix_webhook_events_installation_id"))
        batch_op.drop_column("organization_id")
        batch_op.drop_column("installation_id")
        batch_op.drop_column("next_retry_at")
        batch_op.drop_column("retries")
