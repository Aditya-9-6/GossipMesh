"""Add idempotency_keys table (Task 59)

Revision ID: 7a1000000003
Revises: 7a1000000002
Create Date: 2026-10-21 18:50:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a1000000003"
down_revision = "7a1000000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=50), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="in_progress"),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(op.f("ix_idempotency_keys_id"), "idempotency_keys", ["id"], unique=False)
    op.create_index(op.f("ix_idempotency_keys_key"), "idempotency_keys", ["key"], unique=True)
    op.create_index(op.f("ix_idempotency_keys_scope"), "idempotency_keys", ["scope"], unique=False)
    op.create_index(op.f("ix_idempotency_keys_organization_id"), "idempotency_keys", ["organization_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_idempotency_keys_organization_id"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_scope"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_key"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_id"), table_name="idempotency_keys")
    op.drop_table("idempotency_keys")
