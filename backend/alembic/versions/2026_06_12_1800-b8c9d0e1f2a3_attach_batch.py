"""attach batch trace table

repo_attach_batch

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-12 18:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "repo_attach_batch",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("batch_no", sa.String(40), nullable=False),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("attached", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("not_found", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("overwrite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("rows", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["operator_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_repo_attach_batch_batch_no", "repo_attach_batch", ["batch_no"])
    op.create_index("ix_repo_attach_batch_tenant_id", "repo_attach_batch", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("repo_attach_batch")
