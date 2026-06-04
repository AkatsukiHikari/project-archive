"""
AI 黄金集（评测样本）

每能力一组样本，作为上线门禁。Workflow 升版 / 模型切换 / Prompt 调整时必须
跑一遍黄金集，达不到阈值自动回滚。详见设计稿 §7.4。
"""
import uuid
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class GoldenSetItem(BaseEntity):
    """黄金集条目（一行 = 一个评测样本）。"""

    __tablename__ = "ai_golden_set"
    __table_args__ = (
        Index("ix_ai_golden_tenant_scenario", "tenant_id", "scenario_code"),
        Index("ix_ai_golden_source", "source"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户（黄金集按租户隔离）",
    )
    scenario_code: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="所属能力：qa/search/summary/..."
    )
    input: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="输入：{query, scenario_code, context_archive_ids?, ...}"
    )
    expected: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="期望输出 / 评分 rubric"
    )
    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        comment="标签：难度/类型/边界等，便于分桶统计",
    )
    source: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="seed",
        server_default="seed",
        comment="来源：seed（人工种子）/ reject_pool（驳回入池）/ import（批量导入）",
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
