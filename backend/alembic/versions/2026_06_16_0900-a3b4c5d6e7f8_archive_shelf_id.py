"""archive shelf_id (库房架位物理存放位置)

repo_archive.shelf_id —— 档案与架位关联，库房/架位占用率由此实时统计

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-06-16 09:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'a3b4c5d6e7f8'
down_revision: Union[str, Sequence[str], None] = 'f2a3b4c5d6e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("repo_archive", sa.Column("shelf_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index("ix_repo_archive_shelf_id", "repo_archive", ["shelf_id"])


def downgrade() -> None:
    op.drop_index("ix_repo_archive_shelf_id", "repo_archive")
    op.drop_column("repo_archive", "shelf_id")
