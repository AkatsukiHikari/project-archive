"""utilization application + 调阅篮 tables

util_application  利用申请 / 利用登记
util_item         调阅篮条目（利用明细）

Revision ID: b7c1d2e3f4a5
Revises: 29d73422b76f
Create Date: 2026-06-09 10:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'b7c1d2e3f4a5'
down_revision: Union[str, Sequence[str], None] = '29d73422b76f'
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
        "util_application",
        *_audit(),
        sa.Column("reg_no", sa.String(length=40), nullable=False),
        sa.Column("applicant_name", sa.String(length=100), nullable=False),
        sa.Column("id_card_no", sa.String(length=32), nullable=True),
        sa.Column("gender", sa.String(length=8), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("organization", sa.String(length=200), nullable=True),
        sa.Column("avatar_key", sa.String(length=1024), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column("use_type", sa.String(length=20), nullable=False, server_default="read"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="processing"),
        sa.Column("handler_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["handler_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_util_application_reg_no", "util_application", ["reg_no"])
    op.create_index("ix_util_application_applicant_name", "util_application", ["applicant_name"])
    op.create_index("ix_util_application_id_card_no", "util_application", ["id_card_no"])
    op.create_index("ix_util_application_status", "util_application", ["status"])
    op.create_index("ix_util_application_tenant_id", "util_application", ["tenant_id"])

    op.create_table(
        "util_item",
        *_audit(),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("archive_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("DH", sa.String(length=100), nullable=True),
        sa.Column("TM", sa.String(length=512), nullable=False),
        sa.Column("RZZ", sa.String(length=200), nullable=True),
        sa.Column("ND", sa.Integer(), nullable=True),
        sa.Column("QZH", sa.String(length=50), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["application_id"], ["util_application.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_util_item_application_id", "util_item", ["application_id"])
    op.create_index("ix_util_item_archive_id", "util_item", ["archive_id"])
    op.create_index("ix_util_item_tenant_id", "util_item", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("util_item")
    op.drop_table("util_application")
