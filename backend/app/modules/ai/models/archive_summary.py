"""档案摘要缓存：原文全文不变则复用已生成的摘要。"""

import uuid
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class ArchiveSummary(BaseEntity):
    __tablename__ = "ai_archive_summary"

    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    text_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="full_text 的 sha256，变了才重新生成"
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
