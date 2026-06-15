"""archive full_text (OCR) column for full-text search

repo_archive.full_text + repo_archive_staging.full_text

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-06-13 14:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'd0e1f2a3b4c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("repo_archive", sa.Column("full_text", sa.Text(), nullable=True))
    op.add_column("repo_archive_staging", sa.Column("full_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("repo_archive_staging", "full_text")
    op.drop_column("repo_archive", "full_text")
