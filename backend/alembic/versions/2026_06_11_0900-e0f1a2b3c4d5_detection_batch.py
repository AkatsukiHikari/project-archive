"""four-natures detection batch

pres_batch + pres_run.batch_id

Revision ID: e0f1a2b3c4d5
Revises: d9e3f4a5b6c7
Create Date: 2026-06-11 09:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'e0f1a2b3c4d5'
down_revision: Union[str, Sequence[str], None] = 'd9e3f4a5b6c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pres_batch",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("batch_no", sa.String(40), nullable=False),
        sa.Column("scope_type", sa.String(20), nullable=False, server_default="single"),
        sa.Column("scope_label", sa.String(512), nullable=True),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheme_name", sa.String(200), nullable=True),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pending", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dim_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("conclusion", sa.String(20), nullable=False, server_default="pass"),
        sa.Column("status", sa.String(20), nullable=False, server_default="done"),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_key", sa.String(1024), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["scheme_id"], ["pres_scheme.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operator_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pres_batch_batch_no", "pres_batch", ["batch_no"])
    op.create_index("ix_pres_batch_tenant_id", "pres_batch", ["tenant_id"])

    op.add_column("pres_run", sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_pres_run_batch_id", "pres_run", ["batch_id"])
    op.create_foreign_key("fk_pres_run_batch", "pres_run", "pres_batch", ["batch_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint("fk_pres_run_batch", "pres_run", type_="foreignkey")
    op.drop_index("ix_pres_run_batch_id", "pres_run")
    op.drop_column("pres_run", "batch_id")
    op.drop_table("pres_batch")
