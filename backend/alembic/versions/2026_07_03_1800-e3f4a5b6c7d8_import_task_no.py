"""repo_import_task 加 task_no（导入批次号）+ attach_batch_id（关联挂接批次），存量回填批次号

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-07-03 18:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, Sequence[str], None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("repo_import_task", sa.Column("task_no", sa.String(40), nullable=True))
    op.add_column(
        "repo_import_task",
        sa.Column("attach_batch_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_repo_import_task_task_no", "repo_import_task", ["task_no"])
    # 存量任务按创建日期回填批次号 DRyyyymmddNNN
    op.execute(
        """
        WITH numbered AS (
            SELECT id,
                   'DR' || to_char(create_time, 'YYYYMMDD') ||
                   lpad(row_number() OVER (
                       PARTITION BY to_char(create_time, 'YYYYMMDD')
                       ORDER BY create_time
                   )::text, 3, '0') AS no
            FROM repo_import_task
        )
        UPDATE repo_import_task t
        SET task_no = n.no
        FROM numbered n
        WHERE t.id = n.id AND t.task_no IS NULL
        """
    )


def downgrade() -> None:
    op.drop_index("ix_repo_import_task_task_no", table_name="repo_import_task")
    op.drop_column("repo_import_task", "attach_batch_id")
    op.drop_column("repo_import_task", "task_no")
