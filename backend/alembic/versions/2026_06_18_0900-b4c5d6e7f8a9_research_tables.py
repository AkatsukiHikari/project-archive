"""archive research (编研) tables

research_project / research_material / research_result

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-06-18 09:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, Sequence[str], None] = "a3b4c5d6e7f8"
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


def upgrade() -> None:
    op.create_table(
        "research_project",
        *_audit(),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "project_type", sa.String(20), nullable=False, server_default="专题汇编"
        ),
        sa.Column("editor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("members", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("purpose", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="in_progress"
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(["editor_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_research_project_tenant_id", "research_project", ["tenant_id"])

    op.create_table(
        "research_material",
        *_audit(),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("archive_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("DH", sa.String(100), nullable=True),
        sa.Column("TM", sa.String(512), nullable=False),
        sa.Column("RZZ", sa.String(200), nullable=True),
        sa.Column("ND", sa.Integer(), nullable=True),
        sa.Column("WJRQ", sa.String(20), nullable=True),
        sa.Column("QZH", sa.String(50), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["research_project.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_research_material_project_id", "research_material", ["project_id"]
    )
    op.create_index(
        "ix_research_material_archive_id", "research_material", ["archive_id"]
    )
    op.create_index(
        "ix_research_material_tenant_id", "research_material", ["tenant_id"]
    )

    op.create_table(
        "research_result",
        *_audit(),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "result_type", sa.String(20), nullable=False, server_default="专题汇编"
        ),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("entries", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "cited_archives", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["research_project.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["author_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewer_id"], ["iam_user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["iam_tenant.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_research_result_project_id", "research_result", ["project_id"])
    op.create_index("ix_research_result_status", "research_result", ["status"])
    op.create_index("ix_research_result_tenant_id", "research_result", ["tenant_id"])


def downgrade() -> None:
    op.drop_table("research_result")
    op.drop_table("research_material")
    op.drop_table("research_project")
