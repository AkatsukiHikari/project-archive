import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.common.entity.base import BaseEntity


class DetectionRecord(BaseEntity):
    __tablename__ = "pres_detection_record"

    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True, comment="被检测档案ID"
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False, comment="文件名")
    original_hash: Mapped[str] = mapped_column(String(256), nullable=False, comment="原始哈希值")
    algorithm: Mapped[str] = mapped_column(String(32), nullable=False, default="sha256", comment="哈希算法")
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="档案元数据JSON")
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="档案内容文本")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="检测状态: pending/pass/fail"
    )
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, comment="四性检测评分(0-100)")
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="检测详情JSON")
    checked_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="检测人ID",
    )
    checked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="检测时间"
    )
