"""Add billing and Stripe models (Task 87)

Revision ID: 7a1000000009
Revises: 7a1000000008
Create Date: 2026-10-21 19:53:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a1000000009"
down_revision = "7a1000000008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. stripe_customers
    op.create_table(
        "stripe_customers",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("currency", sa.String(length=10), server_default="usd", nullable=False),
        sa.Column("delinquent", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_stripe_customers_organization_id", "stripe_customers", ["organization_id"], unique=True)
    op.create_index("ix_stripe_customers_stripe_customer_id", "stripe_customers", ["stripe_customer_id"], unique=True)

    # 2. billing_subscriptions
    op.create_table(
        "billing_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("plan_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_billing_subscriptions_organization_id", "billing_subscriptions", ["organization_id"])
    op.create_index("ix_billing_subscriptions_stripe_subscription_id", "billing_subscriptions", ["stripe_subscription_id"], unique=True)
    op.create_index("ix_billing_subscriptions_stripe_customer_id", "billing_subscriptions", ["stripe_customer_id"])

    # 3. billing_invoices
    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stripe_invoice_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=False),
        sa.Column("amount_due", sa.Integer(), server_default="0", nullable=False),
        sa.Column("amount_paid", sa.Integer(), server_default="0", nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="usd", nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("hosted_invoice_url", sa.String(length=1024), nullable=True),
        sa.Column("invoice_pdf", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_billing_invoices_organization_id", "billing_invoices", ["organization_id"])
    op.create_index("ix_billing_invoices_stripe_invoice_id", "billing_invoices", ["stripe_invoice_id"], unique=True)
    op.create_index("ix_billing_invoices_stripe_customer_id", "billing_invoices", ["stripe_customer_id"])

    # 4. processed_webhook_events
    op.create_table(
        "processed_webhook_events",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="success", nullable=False),
        sa.Column("error_message", sa.String(length=1024), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_processed_webhook_events_stripe_event_id", "processed_webhook_events", ["stripe_event_id"], unique=True)

    # 5. usage_records
    op.create_table(
        "usage_records",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("metric_type", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.String(length=2048), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_usage_records_organization_id", "usage_records", ["organization_id"])
    op.create_index("ix_usage_records_metric_type", "usage_records", ["metric_type"])
    op.create_index("ix_usage_records_idempotency_key", "usage_records", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_table("usage_records")
    op.drop_table("processed_webhook_events")

    op.drop_table("billing_invoices")
    op.drop_table("billing_subscriptions")
    op.drop_table("stripe_customers")
