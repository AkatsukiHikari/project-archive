"""智能著录抽取缓存：原文全文不变就复用 AI 抽取结果，避免每次重跑 Dify。"""

import uuid
from typing import Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class CatalogExtractCache(BaseEntity):
    __tablename__ = "ai_catalog_extract"

    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    text_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="full_text 的 sha256，变了才重抽"
    )
    data: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="抽取结果 {字段:{value,confidence,evidence}}"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
