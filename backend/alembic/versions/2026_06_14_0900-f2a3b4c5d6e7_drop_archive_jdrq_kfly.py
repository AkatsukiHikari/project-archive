"""drop archive JDRQ/KFLY (normalize: appraisal date+reason belong to appraisal process record)

鉴定日期/开放理由是"鉴定"这一管理过程的元数据，应留在 appr_task/appr_item，
不作为档案实体的静态列。开放状态 KFZT 作为当前访问标识保留。

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-06-14 09:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f2a3b4c5d6e7'
down_revision: Union[str, Sequence[str], None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("repo_archive", "JDRQ")
    op.drop_column("repo_archive", "KFLY")


def downgrade() -> None:
    op.add_column("repo_archive", sa.Column("KFLY", sa.Text(), nullable=True))
    op.add_column("repo_archive", sa.Column("JDRQ", sa.String(20), nullable=True))
