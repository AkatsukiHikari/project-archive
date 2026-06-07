"""transfer collection tables

归档移交 / 接收登记 / 收集台账 模块表：
  col_transfer_plan   归档计划（应交计划，催交看板依据）
  col_transfer_batch  移交单（移交清单，含四性预检闸门结果）
  col_transfer_entry  移交明细（DA/T 拼音缩写字段，接收后物化为暂存库）

Revision ID: 29d73422b76f
Revises: bfd3f6773934
Create Date: 2026-06-07 10:51

注：本迁移仅新增 collection 模块的 3 张表，不触碰既有表。
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '29d73422b76f'
down_revision: Union[str, Sequence[str], None] = 'bfd3f6773934'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def upgrade() -> None:
    # ── col_transfer_plan ────────────────────────────────────────────
    op.create_table(
        "col_transfer_plan",
        *_audit_columns(),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("source_unit", sa.String(length=200), nullable=False),
        sa.Column("source_org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fonds_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("planned_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["fonds_id"], ["repo_fonds.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["repo_archive_category.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_col_transfer_plan_year", "col_transfer_plan", ["year"])
    op.create_index("ix_col_transfer_plan_source_unit", "col_transfer_plan", ["source_unit"])
    op.create_index("ix_col_transfer_plan_source_org_id", "col_transfer_plan", ["source_org_id"])
    op.create_index("ix_col_transfer_plan_fonds_id", "col_transfer_plan", ["fonds_id"])
    op.create_index("ix_col_transfer_plan_category_id", "col_transfer_plan", ["category_id"])
    op.create_index("ix_col_transfer_plan_tenant_id", "col_transfer_plan", ["tenant_id"])

    # ── col_transfer_batch ───────────────────────────────────────────
    op.create_table(
        "col_transfer_batch",
        *_audit_columns(),
        sa.Column("transfer_no", sa.String(length=50), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_unit", sa.String(length=200), nullable=False),
        sa.Column("source_org_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("fonds_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("catalog_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("handover_person", sa.String(length=100), nullable=False),
        sa.Column("handover_date", sa.Date(), nullable=True),
        sa.Column("expected_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handler_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("precheck_score", sa.Float(), nullable=True),
        sa.Column("precheck_passed", sa.Boolean(), nullable=True),
        sa.Column("precheck_detail", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("return_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["col_transfer_plan.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["fonds_id"], ["repo_fonds.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["category_id"], ["repo_archive_category.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["catalog_id"], ["repo_catalog.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["handler_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_col_transfer_batch_transfer_no", "col_transfer_batch", ["transfer_no"])
    op.create_index("ix_col_transfer_batch_plan_id", "col_transfer_batch", ["plan_id"])
    op.create_index("ix_col_transfer_batch_source_unit", "col_transfer_batch", ["source_unit"])
    op.create_index("ix_col_transfer_batch_fonds_id", "col_transfer_batch", ["fonds_id"])
    op.create_index("ix_col_transfer_batch_category_id", "col_transfer_batch", ["category_id"])
    op.create_index("ix_col_transfer_batch_catalog_id", "col_transfer_batch", ["catalog_id"])
    op.create_index("ix_col_transfer_batch_year", "col_transfer_batch", ["year"])
    op.create_index("ix_col_transfer_batch_status", "col_transfer_batch", ["status"])
    op.create_index("ix_col_transfer_batch_tenant_id", "col_transfer_batch", ["tenant_id"])

    # ── col_transfer_entry ───────────────────────────────────────────
    op.create_table(
        "col_transfer_entry",
        *_audit_columns(),
        sa.Column("batch_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("row_no", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("TM", sa.String(length=512), nullable=False),
        sa.Column("RZZ", sa.String(length=200), nullable=True),
        sa.Column("ND", sa.Integer(), nullable=True),
        sa.Column("WJRQ", sa.String(length=20), nullable=True),
        sa.Column("YS", sa.Integer(), nullable=True),
        sa.Column("MJ", sa.String(length=20), nullable=True),
        sa.Column("BGQX", sa.String(length=20), nullable=True),
        sa.Column("ext_fields", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("precheck_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("precheck_issues", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("staging_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["col_transfer_batch.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_col_transfer_entry_batch_id", "col_transfer_entry", ["batch_id"])
    op.create_index("ix_col_transfer_entry_staging_id", "col_transfer_entry", ["staging_id"])
    op.create_index("ix_col_transfer_entry_tenant_id", "col_transfer_entry", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("col_transfer_entry")
    op.drop_table("col_transfer_batch")
    op.drop_table("col_transfer_plan")
