"""MJ 密级值体系修正

密级依据《保守国家秘密法》：无 | 秘密 | 机密 | 绝密（"公开/内部"不是密级）。
历史英文编码与旧中文值统一迁移为新值体系；同步修正 sys_dict MJ 字典项。

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-13 09:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c9d0e1f2a3b4'
down_revision: Union[str, Sequence[str], None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# 旧值 → 新值（public/internal/公开/内部 均视为"无密级"）
MJ_MAP = [
    ("public", "无"),
    ("internal", "无"),
    ("公开", "无"),
    ("内部", "无"),
    ("secret", "秘密"),
    ("confidential", "机密"),
    ("top_secret", "绝密"),
]

TABLES = ["repo_archive", "repo_archive_staging", "appr_item"]


def upgrade() -> None:
    for table in TABLES:
        for old, new in MJ_MAP:
            op.execute(f"UPDATE {table} SET \"MJ\" = '{new}' WHERE \"MJ\" = '{old}'")

    # 字典 MJ 项重置为标准密级
    op.execute("DELETE FROM sys_dict_item WHERE dict_type = 'MJ'")
    op.execute(
        """
        INSERT INTO sys_dict_item
            (id, dict_type, item_value, item_label, is_default, sort_order,
             create_time, update_time, is_deleted)
        SELECT gen_random_uuid(), 'MJ', v.val, v.val, v.dflt, v.ord, now(), now(), false
        FROM (VALUES
            ('无',   true,  1),
            ('秘密', false, 2),
            ('机密', false, 3),
            ('绝密', false, 4)
        ) AS v(val, dflt, ord)
        WHERE EXISTS (SELECT 1 FROM sys_dict WHERE dict_type = 'MJ' AND is_deleted = false)
        """
    )


def downgrade() -> None:
    # 值迁移不可逆（公开/内部 与 无 已合并），downgrade 不做处理
    pass
