"""OCR 作业：挂接 PDF 后台识别的任务记录（供进度查看）。"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class OcrJob(BaseEntity):
    __tablename__ = "ai_ocr_job"

    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    attachment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    archive_dh: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="档号快照"
    )
    archive_tm: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="题名快照"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending | running | succeeded | failed",
    )
    chars: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="识别出的字数"
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
