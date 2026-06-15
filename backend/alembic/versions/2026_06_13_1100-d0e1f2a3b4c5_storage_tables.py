"""storage vault / shelf / inout

stor_vault / stor_shelf / stor_inout

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-13 11:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'd0e1f2a3b4c5'
down_revision: Union[str, Sequence[str], None] = 'c9d0e1f2a3b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("create_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("update_time", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "stor_vault",
        *_audit(),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("area_sqm", sa.Float(), nullable=True),
        sa.Column("rows", sa.Integer(), nullable=False, server_default="4"),
        sa.Column("columns", sa.Integer(), nullable=False, server_default="6"),
        sa.Column("layers", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("humidity", sa.Float(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("manager_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["manager_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_stor_vault_code", "stor_vault", ["code"])
    op.create_index("ix_stor_vault_tenant_id", "stor_vault", ["tenant_id"])

    op.create_table(
        "stor_shelf",
        *_audit(),
        sa.Column("vault_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(40), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("col_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["vault_id"], ["stor_vault.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_stor_shelf_vault_id", "stor_shelf", ["vault_id"])
    op.create_index("ix_stor_shelf_tenant_id", "stor_shelf", ["tenant_id"])

    op.create_table(
        "stor_inout",
        *_audit(),
        sa.Column("record_no", sa.String(40), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("biz_type", sa.String(20), nullable=False, server_default="borrow"),
        sa.Column("archive_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("DH", sa.String(100), nullable=True),
        sa.Column("TM", sa.String(512), nullable=True),
        sa.Column("qty", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("vault_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("counterparty", sa.String(200), nullable=True),
        sa.Column("related_app_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="out"),
        sa.Column("out_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_return", sa.DateTime(timezone=True), nullable=True),
        sa.Column("in_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operator_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["vault_id"], ["stor_vault.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operator_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_stor_inout_record_no", "stor_inout", ["record_no"])
    op.create_index("ix_stor_inout_direction", "stor_inout", ["direction"])
    op.create_index("ix_stor_inout_status", "stor_inout", ["status"])
    op.create_index("ix_stor_inout_archive_id", "stor_inout", ["archive_id"])
    op.create_index("ix_stor_inout_related_app_id", "stor_inout", ["related_app_id"])
    op.create_index("ix_stor_inout_tenant_id", "stor_inout", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("stor_inout")
    op.drop_table("stor_shelf")
    op.drop_table("stor_vault")
