"""
专家标注表

P3 起：用户驳回的 patch 自动入"待标注池"，专家审后转黄金集。
本表是待标注池的载体——黄金集来源最便宜的方式。详见设计稿 §7.4。
"""
import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class Annotation(BaseEntity):
    """待标注 / 已标注样本。"""

    __tablename__ = "ai_annotation"
    __table_args__ = (
        Index("ix_ai_annotation_tenant_status", "tenant_id", "status"),
        Index("ix_ai_annotation_scenario", "scenario_code"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_code: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="reject_pool",
        server_default="reject_pool",
        comment="来源：reject_pool / manual / import",
    )
    patch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_patch.id", ondelete="SET NULL"),
        nullable=True,
        comment="来源 patch（若由驳回入池）",
    )
    input: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="输入快照"
    )
    ai_output: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="AI 当时的输出"
    )
    expected: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, comment="标注后的期望输出（标注完成才填）"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="状态：pending / annotated / promoted（已转入黄金集）/ discarded",
    )
    annotator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    promoted_golden_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_golden_set.id", ondelete="SET NULL"),
        nullable=True,
        comment="若已转入黄金集，对应的 golden_id",
    )
