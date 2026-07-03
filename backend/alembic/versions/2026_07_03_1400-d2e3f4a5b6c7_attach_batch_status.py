"""repo_attach_batch 加 status（分批上传会话状态）

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
Create Date: 2026-07-03 14:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d2e3f4a5b6c7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "repo_attach_batch",
        sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
    )


def downgrade() -> None:
    op.drop_column("repo_attach_batch", "status")
