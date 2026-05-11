"""rename_archive_fields_to_pinyin

将 repo_archive 表的 DA/T 规范化列重命名为中文拼音缩写，
与 field_schema 的字段命名体系保持一致。

映射关系：
  archive_no       → DH   (档号)
  fonds_code       → QZH  (全宗号)
  catalog_no       → MLH  (目录号)
  volume_no        → AJH  (案卷号)
  item_no          → JH   (件号)
  year             → ND   (年度)
  title            → TM   (题名)
  creator          → RZZ  (责任者)
  security_level   → MJ   (密级)
  retention_period → BGQX (保管期限)
  doc_date         → WJRQ (文件日期)
  pages            → YS   (页数)

Revision ID: b3e7f2a1c9d4
Revises: eceabc81e6a9
Create Date: 2026-04-25 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3e7f2a1c9d4'
down_revision: Union[str, Sequence[str], None] = 'eceabc81e6a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "repo_archive"

_RENAMES = [
    ("archive_no",       "DH"),
    ("fonds_code",       "QZH"),
    ("catalog_no",       "MLH"),
    ("volume_no",        "AJH"),
    ("item_no",          "JH"),
    ("year",             "ND"),
    ("title",            "TM"),
    ("creator",          "RZZ"),
    ("security_level",   "MJ"),
    ("retention_period", "BGQX"),
    ("doc_date",         "WJRQ"),
    ("pages",            "YS"),
]


def upgrade() -> None:
    for old_name, new_name in _RENAMES:
        op.alter_column(_TABLE, old_name, new_column_name=new_name)


def downgrade() -> None:
    for old_name, new_name in _RENAMES:
        op.alter_column(_TABLE, new_name, new_column_name=old_name)
