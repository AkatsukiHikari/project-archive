"""four-natures detection: catalog + scheme + run tables

pres_check_item / pres_scheme / pres_scheme_item / pres_run / pres_run_result

Revision ID: d9e3f4a5b6c7
Revises: c8d2e3f4a5b6
Create Date: 2026-06-10 09:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd9e3f4a5b6c7'
down_revision: Union[str, Sequence[str], None] = 'c8d2e3f4a5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit() -> list:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "pres_check_item",
        *_audit(),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("dimension", sa.String(20), nullable=False),
        sa.Column("exec_type", sa.String(10), nullable=False, server_default="rule"),
        sa.Column("standard_ref", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("carrier_type", sa.String(20), nullable=False, server_default="electronic"),
        sa.Column("default_params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("default_weight", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("default_blocking", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("builtin", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("code", name="uq_pres_check_item_code"),
    )
    op.create_index("ix_pres_check_item_code", "pres_check_item", ["code"])
    op.create_index("ix_pres_check_item_dimension", "pres_check_item", ["dimension"])

    op.create_table(
        "pres_scheme",
        *_audit(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("carrier_type", sa.String(20), nullable=False, server_default="electronic"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pres_scheme_tenant_id", "pres_scheme", ["tenant_id"])

    op.create_table(
        "pres_scheme_item",
        *_audit(),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_code", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["scheme_id"], ["pres_scheme.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pres_scheme_item_scheme_id", "pres_scheme_item", ["scheme_id"])

    op.create_table(
        "pres_run",
        *_audit(),
        sa.Column("target_type", sa.String(20), nullable=False, server_default="archive"),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_label", sa.String(512), nullable=True),
        sa.Column("scheme_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("scheme_name", sa.String(200), nullable=True),
        sa.Column("scheme_version", sa.Integer(), nullable=True),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("dim_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("conclusion", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("status", sa.String(20), nullable=False, server_default="done"),
        sa.Column("total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warned", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manual_pending", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_key", sa.String(1024), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["scheme_id"], ["pres_scheme.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operator_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pres_run_target_id", "pres_run", ["target_id"])
    op.create_index("ix_pres_run_tenant_id", "pres_run", ["tenant_id"])

    op.create_table(
        "pres_run_result",
        *_audit(),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("check_code", sa.String(64), nullable=False),
        sa.Column("check_name", sa.String(200), nullable=False),
        sa.Column("dimension", sa.String(20), nullable=False),
        sa.Column("exec_type", sa.String(10), nullable=False),
        sa.Column("result", sa.String(20), nullable=False, server_default="pass"),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("weight", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_blocking", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("standard_ref", sa.String(200), nullable=True),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["pres_run.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["decided_by"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_pres_run_result_run_id", "pres_run_result", ["run_id"])


def downgrade() -> None:
    op.drop_table("pres_run_result")
    op.drop_table("pres_run")
    op.drop_table("pres_scheme_item")
    op.drop_table("pres_scheme")
    op.drop_table("pres_check_item")
