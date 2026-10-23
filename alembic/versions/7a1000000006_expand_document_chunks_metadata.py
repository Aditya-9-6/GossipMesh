"""Expand document_chunks metadata for production vector storage (Task 75)

Revision ID: 7a1000000006
Revises: 7a1000000005
Create Date: 2026-10-21 19:22:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "7a1000000006"
down_revision = "7a1000000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("document_chunks", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("organization_id", sa.String(length=128), nullable=False, server_default="default")
        )
        batch_op.add_column(sa.Column("repository_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("branch", sa.String(length=256), nullable=False, server_default="main"))
        batch_op.add_column(sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("chunk_hash", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("provider", sa.String(length=128), nullable=False, server_default="openai:text-embedding-3-small")
        )
        batch_op.add_column(sa.Column("embedding_version", sa.String(length=32), nullable=False, server_default="v1"))
        batch_op.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")))
        batch_op.add_column(sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False
            )
        )

        batch_op.create_index("ix_document_chunks_organization_id", ["organization_id"])
        batch_op.create_index("ix_document_chunks_repository_id", ["repository_id"])
        batch_op.create_index("ix_document_chunks_branch", ["branch"])
        batch_op.create_index("ix_document_chunks_chunk_hash", ["chunk_hash"])
        batch_op.create_index("ix_document_chunks_is_deleted", ["is_deleted"])


def downgrade() -> None:
    with op.batch_alter_table("document_chunks", schema=None) as batch_op:
        batch_op.drop_index("ix_document_chunks_is_deleted")
        batch_op.drop_index("ix_document_chunks_chunk_hash")
        batch_op.drop_index("ix_document_chunks_branch")
        batch_op.drop_index("ix_document_chunks_repository_id")
        batch_op.drop_index("ix_document_chunks_organization_id")

        batch_op.drop_column("updated_at")
        batch_op.drop_column("created_at")
        batch_op.drop_column("retention_expires_at")
        batch_op.drop_column("is_deleted")
        batch_op.drop_column("embedding_version")
        batch_op.drop_column("provider")
        batch_op.drop_column("chunk_hash")
        batch_op.drop_column("chunk_index")
        batch_op.drop_column("branch")
        batch_op.drop_column("repository_id")
        batch_op.drop_column("organization_id")
