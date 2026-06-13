"""archive open appraisal

repo_archive + KFZT/JDRQ/KFLY
appr_standard / appr_sensitive_word / appr_plan / appr_task / appr_item
sys_dict_item KFZT 补「延期开放」

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-06-12 09:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, Sequence[str], None] = 'e0f1a2b3c4d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def upgrade() -> None:
    # ── 正式库加开放鉴定字段（分区表，ALTER 自动下发各分区）──
    op.add_column("repo_archive", sa.Column("KFZT", sa.String(20), nullable=True))
    op.add_column("repo_archive", sa.Column("JDRQ", sa.String(20), nullable=True))
    op.add_column("repo_archive", sa.Column("KFLY", sa.Text(), nullable=True))
    op.create_index("ix_repo_archive_KFZT", "repo_archive", ["KFZT"])

    # ── 鉴定标准条款 ──
    op.create_table(
        "appr_standard",
        *_audit_columns(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("target_kfzt", sa.String(20), nullable=False),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("source", sa.String(200), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_appr_standard_code", "appr_standard", ["code"])
    op.create_index("ix_appr_standard_tenant_id", "appr_standard", ["tenant_id"])

    # ── 敏感词 ──
    op.create_table(
        "appr_sensitive_word",
        *_audit_columns(),
        sa.Column("word", sa.String(100), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("suggest_kfzt", sa.String(20), nullable=False, server_default="控制使用"),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_appr_sensitive_word_word", "appr_sensitive_word", ["word"])
    op.create_index("ix_appr_sensitive_word_tenant_id", "appr_sensitive_word", ["tenant_id"])

    # ── 鉴定计划 ──
    op.create_table(
        "appr_plan",
        *_audit_columns(),
        sa.Column("plan_no", sa.String(40), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("appraisal_type", sa.String(20), nullable=False, server_default="open"),
        sa.Column("leader_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="in_progress"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_tasks", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_archives", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["leader_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_appr_plan_plan_no", "appr_plan", ["plan_no"])
    op.create_index("ix_appr_plan_reviewer_id", "appr_plan", ["reviewer_id"])
    op.create_index("ix_appr_plan_tenant_id", "appr_plan", ["tenant_id"])

    # ── 鉴定任务 ──
    op.create_table(
        "appr_task",
        *_audit_columns(),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fonds_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("QZH", sa.String(50), nullable=False),
        sa.Column("fonds_name", sa.String(200), nullable=True),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["appr_plan.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["fonds_id"], ["repo_fonds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignee_id"], ["iam_user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_appr_task_plan_id", "appr_task", ["plan_id"])
    op.create_index("ix_appr_task_assignee_id", "appr_task", ["assignee_id"])
    op.create_index("ix_appr_task_status", "appr_task", ["status"])
    op.create_index("ix_appr_task_tenant_id", "appr_task", ["tenant_id"])

    # ── 鉴定明细 ──
    op.create_table(
        "appr_item",
        *_audit_columns(),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("archive_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ND", sa.Integer(), nullable=True),
        sa.Column("DH", sa.String(100), nullable=True),
        sa.Column("TM", sa.String(512), nullable=False),
        sa.Column("QZH", sa.String(50), nullable=True),
        sa.Column("MJ", sa.String(20), nullable=True),
        sa.Column("BGQX", sa.String(20), nullable=True),
        sa.Column("due_basis", sa.String(100), nullable=True),
        sa.Column("ai_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("ai_kfzt", sa.String(20), nullable=True),
        sa.Column("ai_reason", sa.Text(), nullable=True),
        sa.Column("ai_hit_words", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ai_standard_code", sa.String(40), nullable=True),
        sa.Column("ai_confidence", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("final_kfzt", sa.String(20), nullable=True),
        sa.Column("final_reason", sa.Text(), nullable=True),
        sa.Column("final_standard_code", sa.String(40), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["task_id"], ["appr_task.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["appr_plan.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_appr_item_task_id", "appr_item", ["task_id"])
    op.create_index("ix_appr_item_plan_id", "appr_item", ["plan_id"])
    op.create_index("ix_appr_item_archive_id", "appr_item", ["archive_id"])
    op.create_index("ix_appr_item_status", "appr_item", ["status"])
    op.create_index("ix_appr_item_tenant_id", "appr_item", ["tenant_id"])

    # ── 字典 KFZT 补「延期开放」（存量库）──
    op.execute(
        """
        INSERT INTO sys_dict_item
            (id, dict_type, item_value, item_label, is_default, sort_order,
             create_time, update_time, is_deleted)
        SELECT gen_random_uuid(), 'KFZT', '延期开放', '延期开放', false, 3,
               now(), now(), false
        WHERE EXISTS (
            SELECT 1 FROM sys_dict WHERE dict_type = 'KFZT' AND is_deleted = false
        )
        AND NOT EXISTS (
            SELECT 1 FROM sys_dict_item
            WHERE dict_type = 'KFZT' AND item_value = '延期开放' AND is_deleted = false
        )
        """
    )


def downgrade() -> None:
    op.drop_table("appr_item")
    op.drop_table("appr_task")
    op.drop_table("appr_plan")
    op.drop_table("appr_sensitive_word")
    op.drop_table("appr_standard")
    op.drop_index("ix_repo_archive_KFZT", "repo_archive")
    op.drop_column("repo_archive", "KFLY")
    op.drop_column("repo_archive", "JDRQ")
    op.drop_column("repo_archive", "KFZT")
