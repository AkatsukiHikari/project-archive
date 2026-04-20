import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class ImportTask(BaseEntity):
    """
    批量导入任务表。
    记录每次导入的元数据、进度和结果。
    """
    __tablename__ = "repo_import_task"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="RESTRICT"),
        nullable=False, index=True, comment="导入的档案门类"
    )
    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="RESTRICT"),
        nullable=False, index=True, comment="目标全宗"
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_catalog.id", ondelete="RESTRICT"),
        nullable=False, index=True, comment="目标目录"
    )
    operator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="RESTRICT"),
        nullable=False, comment="操作人"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="任务状态: pending/running/done/failed"
    )
    file_key: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="上传的原始文件对象键"
    )
    original_filename: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="原始文件名"
    )
    mapping_snapshot: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="本次导入使用的字段映射快照"
    )
    total: Mapped[int] = mapped_column(Integer, default=0, comment="总行数")
    success: Mapped[int] = mapped_column(Integer, default=0, comment="成功行数")
    failed: Mapped[int] = mapped_column(Integer, default=0, comment="失败行数")
    skipped: Mapped[int] = mapped_column(Integer, default=0, comment="跳过行数")
    error_report_key: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="失败报表文件的对象键"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="任务开始时间"
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="任务完成时间"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
