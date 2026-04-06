"""Add is_superadmin to user

Revision ID: c4e1a7f83b21
Revises: b9d297427344
Create Date: 2026-03-22 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e1a7f83b21'
down_revision: Union[str, None] = 'b9d297427344'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'iam_user',
        sa.Column(
            'is_superadmin',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='是否超级管理员',
        )
    )


def downgrade() -> None:
    op.drop_column('iam_user', 'is_superadmin')
