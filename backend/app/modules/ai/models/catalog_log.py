"""智能著录审计：记录 AI 著录/补足/更正 操作，供政务可追溯。"""

import uuid
from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class AiCatalogLog(BaseEntity):
    __tablename__ = "ai_catalog_log"

    archive_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
        comment="目标档案（自动录入新增时为新建后的 id）",
    )
    doc_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="staging",
        comment="staging | formal",
    )
    action: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True,
        comment="ingest 自动录入 | fill 补足 | correct 更正",
    )
    archive_dh: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    archive_tm: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # 采用明细：{field: {old, suggested, adopted, confidence}}
    changes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
