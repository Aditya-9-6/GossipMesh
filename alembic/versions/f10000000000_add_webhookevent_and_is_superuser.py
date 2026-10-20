"""Add WebhookEvent and is_superuser

Revision ID: f10000000000
Revises: f00000000001
Create Date: 2024-10-14 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f10000000000"
down_revision = "f00000000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add WebhookEvent table
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("delivery_id", sa.String(), nullable=False),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("replayed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replayed_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["replayed_by"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("webhook_events", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_webhook_events_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_webhook_events_delivery_id"), ["delivery_id"], unique=True)

    # Add is_superuser to users
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_superuser", sa.Boolean(), server_default="0", nullable=False))


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("is_superuser")

    with op.batch_alter_table("webhook_events", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_webhook_events_delivery_id"))
        batch_op.drop_index(batch_op.f("ix_webhook_events_id"))
    op.drop_table("webhook_events")
