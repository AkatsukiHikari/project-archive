"""archive.kb_doc_id (Dify 知识库文档 ID)

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-06-21 15:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, Sequence[str], None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("repo_archive", sa.Column("kb_doc_id", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("repo_archive", "kb_doc_id")
