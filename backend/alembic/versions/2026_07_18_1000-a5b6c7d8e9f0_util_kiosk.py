"""利用服务中心：util_application 加自助机通道字段（source/access_code/审批）

Revision ID: a5b6c7d8e9f0
Revises: f4a5b6c7d8e9
Create Date: 2026-07-18 10:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "f4a5b6c7d8e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "util_application",
        sa.Column("source", sa.String(10), nullable=False, server_default="counter"),
    )
    op.add_column("util_application", sa.Column("access_code", sa.String(8), nullable=True))
    op.add_column(
        "util_application",
        sa.Column(
            "approved_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("iam_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "util_application",
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("util_application", sa.Column("reject_reason", sa.String(500), nullable=True))
    op.create_index("ix_util_application_access_code", "util_application", ["access_code"])
    op.create_index("ix_util_application_source", "util_application", ["source"])


def downgrade() -> None:
    op.drop_index("ix_util_application_source", "util_application")
    op.drop_index("ix_util_application_access_code", "util_application")
    op.drop_column("util_application", "reject_reason")
    op.drop_column("util_application", "approved_at")
    op.drop_column("util_application", "approved_by")
    op.drop_column("util_application", "access_code")
    op.drop_column("util_application", "source")
