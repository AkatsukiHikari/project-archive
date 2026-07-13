"""智能校对：批次表 ai_proofread_batch + 结果表 ai_proofread_item

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-07-09 10:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f4a5b6c7d8e9"
down_revision: Union[str, Sequence[str], None] = "e3f4a5b6c7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_proofread_batch",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("scope", postgresql.JSONB(), nullable=True),
        sa.Column("scope_label", sa.String(512), nullable=True),
        sa.Column("doc_source", sa.String(10), nullable=False, server_default="all"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consistent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flagged", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("no_text", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("update_time", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_ai_proofread_batch_status", "ai_proofread_batch", ["status"])
    op.create_index("ix_ai_proofread_batch_tenant_id", "ai_proofread_batch", ["tenant_id"])

    op.create_table(
        "ai_proofread_item",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ai_proofread_batch.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("archive_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doc_source", sa.String(10), nullable=False, server_default="formal"),
        sa.Column("archive_dh", sa.String(100), nullable=True),
        sa.Column("archive_tm", sa.String(512), nullable=True),
        sa.Column("verdict", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("issue_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("issues", postgresql.JSONB(), nullable=True),
        sa.Column("text_hash", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("update_time", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_index("ix_ai_proofread_item_batch_id", "ai_proofread_item", ["batch_id"])
    op.create_index("ix_ai_proofread_item_archive_id", "ai_proofread_item", ["archive_id"])
    op.create_index("ix_ai_proofread_item_verdict", "ai_proofread_item", ["verdict"])
    op.create_index("ix_ai_proofread_item_tenant_id", "ai_proofread_item", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("ai_proofread_item")
    op.drop_table("ai_proofread_batch")
