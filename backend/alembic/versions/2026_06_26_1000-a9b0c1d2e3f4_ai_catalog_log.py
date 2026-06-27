"""ai_catalog_log 表（智能著录审计）

Revision ID: a9b0c1d2e3f4
Revises: f8a9b0c1d2e3
Create Date: 2026-06-26 10:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a9b0c1d2e3f4"
down_revision: Union[str, Sequence[str], None] = "f8a9b0c1d2e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ai_catalog_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("archive_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("doc_source", sa.String(20), server_default="staging", nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("archive_dh", sa.String(100), nullable=True),
        sa.Column("archive_tm", sa.String(512), nullable=True),
        sa.Column("changes", postgresql.JSONB(), nullable=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_ai_catalog_log_archive_id", "ai_catalog_log", ["archive_id"])
    op.create_index("ix_ai_catalog_log_action", "ai_catalog_log", ["action"])
    op.create_index("ix_ai_catalog_log_tenant_id", "ai_catalog_log", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("ai_catalog_log")
