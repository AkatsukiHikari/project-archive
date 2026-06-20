"""archive research: doc editor + result archive library + templates

- research_result: + content_json, drop entries / cited_archives
- new research_result_archive (成果自有档案库)
- new research_template (编研模板)

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-06-18 11:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _audit() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "create_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "update_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("create_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    ]


def _snapshot_cols() -> list[sa.Column]:
    return [
        sa.Column("DH", sa.String(100), nullable=True),
        sa.Column("TM", sa.String(512), nullable=False),
        sa.Column("RZZ", sa.String(200), nullable=True),
        sa.Column("ND", sa.Integer(), nullable=True),
        sa.Column("WJRQ", sa.String(20), nullable=True),
        sa.Column("QZH", sa.String(50), nullable=True),
    ]


def upgrade() -> None:
    # research_result: 富文档化
    op.add_column(
        "research_result",
        sa.Column(
            "content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.drop_column("research_result", "entries")
    op.drop_column("research_result", "cited_archives")

    # 成果自有档案库
    op.create_table(
        "research_result_archive",
        *_audit(),
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("archive_id", postgresql.UUID(as_uuid=True), nullable=False),
        *_snapshot_cols(),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["result_id"], ["research_result.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_research_result_archive_result_id", "research_result_archive", ["result_id"]
    )
    op.create_index(
        "ix_research_result_archive_archive_id",
        "research_result_archive",
        ["archive_id"],
    )
    op.create_index(
        "ix_research_result_archive_tenant_id", "research_result_archive", ["tenant_id"]
    )

    # 编研模板
    op.create_table(
        "research_template",
        *_audit(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "result_type", sa.String(20), nullable=False, server_default="专题汇编"
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column(
            "content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column(
            "is_builtin", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_research_template_tenant_id", "research_template", ["tenant_id"]
    )


def downgrade() -> None:
    op.drop_table("research_template")
    op.drop_table("research_result_archive")
    op.add_column(
        "research_result",
        sa.Column(
            "cited_archives", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "research_result",
        sa.Column("entries", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.drop_column("research_result", "content_json")
