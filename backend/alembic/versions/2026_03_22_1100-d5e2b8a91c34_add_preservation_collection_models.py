"""Add preservation and collection models

Revision ID: d5e2b8a91c34
Revises: c4e1a7f83b21
Create Date: 2026-03-22 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5e2b8a91c34'
down_revision: Union[str, None] = 'c4e1a7f83b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pres_detection_record',
        sa.Column('archive_id', sa.UUID(), nullable=False, comment='被检测档案ID'),
        sa.Column('filename', sa.String(length=512), nullable=False, comment='文件名'),
        sa.Column('original_hash', sa.String(length=256), nullable=False, comment='原始哈希值'),
        sa.Column('algorithm', sa.String(length=32), nullable=False, comment='哈希算法'),
        sa.Column('metadata_json', sa.JSON(), nullable=True, comment='档案元数据JSON'),
        sa.Column('content_text', sa.Text(), nullable=True, comment='档案内容文本'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='检测状态: pending/pass/fail'),
        sa.Column('score', sa.Float(), nullable=False, comment='四性检测评分(0-100)'),
        sa.Column('details_json', sa.JSON(), nullable=True, comment='检测详情JSON'),
        sa.Column('checked_by', sa.UUID(), nullable=True, comment='检测人ID'),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=True, comment='检测时间'),
        sa.Column('id', sa.UUID(), nullable=False, comment='唯一标识'),
        sa.Column('create_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.Column('create_by', sa.UUID(), nullable=True, comment='创建人ID'),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False, comment='是否逻辑删除'),
        sa.ForeignKeyConstraint(['checked_by'], ['iam_user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pres_detection_record_archive_id'), 'pres_detection_record', ['archive_id'], unique=False)
    op.create_index(op.f('ix_pres_detection_record_checked_by'), 'pres_detection_record', ['checked_by'], unique=False)

    op.create_table(
        'col_sip_record',
        sa.Column('title', sa.String(length=512), nullable=False, comment='SIP标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='描述'),
        sa.Column('submitter_id', sa.UUID(), nullable=False, comment='提交人ID'),
        sa.Column('tenant_id', sa.UUID(), nullable=True, comment='所属租户ID'),
        sa.Column('status', sa.String(length=20), nullable=False, comment='状态: draft/submitted/reviewing/accepted/rejected'),
        sa.Column('metadata_json', sa.JSON(), nullable=True, comment='档案元数据JSON'),
        sa.Column('file_count', sa.Integer(), nullable=False, comment='文件数量'),
        sa.Column('notes', sa.Text(), nullable=True, comment='备注'),
        sa.Column('id', sa.UUID(), nullable=False, comment='唯一标识'),
        sa.Column('create_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('update_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
        sa.Column('create_by', sa.UUID(), nullable=True, comment='创建人ID'),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False, comment='是否逻辑删除'),
        sa.ForeignKeyConstraint(['submitter_id'], ['iam_user.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['iam_tenant.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_col_sip_record_submitter_id'), 'col_sip_record', ['submitter_id'], unique=False)
    op.create_index(op.f('ix_col_sip_record_tenant_id'), 'col_sip_record', ['tenant_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_col_sip_record_tenant_id'), table_name='col_sip_record')
    op.drop_index(op.f('ix_col_sip_record_submitter_id'), table_name='col_sip_record')
    op.drop_table('col_sip_record')
    op.drop_index(op.f('ix_pres_detection_record_checked_by'), table_name='pres_detection_record')
    op.drop_index(op.f('ix_pres_detection_record_archive_id'), table_name='pres_detection_record')
    op.drop_table('pres_detection_record')
