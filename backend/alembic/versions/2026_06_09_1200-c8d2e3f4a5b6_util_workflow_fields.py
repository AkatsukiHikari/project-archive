"""utilization workflow fields (borrow / copy / certificate)

给 util_application 增加 借阅/复制/证明 三类利用方式的业务字段。

Revision ID: c8d2e3f4a5b6
Revises: b7c1d2e3f4a5
Create Date: 2026-06-09 12:00
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c8d2e3f4a5b6'
down_revision: Union[str, Sequence[str], None] = 'b7c1d2e3f4a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLS = [
    ("borrowed_at", sa.DateTime(timezone=True)),
    ("due_date", sa.Date()),
    ("returned_at", sa.DateTime(timezone=True)),
    ("copy_method", sa.String(length=20)),
    ("copies", sa.Integer()),
    ("fee", sa.Numeric(10, 2)),
    ("delivered_at", sa.DateTime(timezone=True)),
    ("cert_no", sa.String(length=40)),
    ("cert_content", sa.Text()),
    ("issued_at", sa.DateTime(timezone=True)),
]


def upgrade() -> None:
    for name, col_type in _COLS:
        op.add_column("util_application", sa.Column(name, col_type, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(_COLS):
        op.drop_column("util_application", name)
