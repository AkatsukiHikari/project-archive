"""智能校对：批次 + 单条结果 模型。

批次 = 一次「开始校对」（按检索范围圈定的一批档案）；
结果 = 批次内单条档案的条目-原文比对结论（每条档案以最新一次为有效）。
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class AiProofreadBatch(BaseEntity):
    """一次批量校对（范围快照 + 进度计数）。"""

    __tablename__ = "ai_proofread_batch"

    scope: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="发起时的检索范围快照（doc_source/导航/字段条件）"
    )
    scope_label: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="范围描述文本（展示用）"
    )
    doc_source: Mapped[str] = mapped_column(
        String(10), nullable=False, default="all", comment="all | staging | formal"
    )
    total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="件数"
    )
    processed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="已处理件数"
    )
    consistent: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="一致件数"
    )
    flagged: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="存疑件数"
    )
    no_text: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="无原文全文件数"
    )
    failed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="失败件数"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        index=True,
        comment="running | done | failed | canceled",
    )
    operator_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="发起人"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )


class AiProofreadItem(BaseEntity):
    """批次内单条档案的校对结果。"""

    __tablename__ = "ai_proofread_item"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_proofread_batch.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="档案ID（暂存/正式，无DB FK）",
    )
    doc_source: Mapped[str] = mapped_column(
        String(10), nullable=False, default="formal", comment="staging | formal"
    )
    archive_dh: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="档号快照"
    )
    archive_tm: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True, comment="题名快照"
    )
    verdict: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending | consistent 一致 | flagged 存疑 | resolved 已整改 | no_text 无原文 | failed",
    )
    issue_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="存疑字段数"
    )
    issues: Mapped[Optional[list]] = mapped_column(
        JSONB,
        nullable=True,
        comment="存疑明细 [{name,label,kind,current,suggested,confidence,evidence,similarity}]",
    )
    text_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="比对时原文全文 sha256"
    )
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
