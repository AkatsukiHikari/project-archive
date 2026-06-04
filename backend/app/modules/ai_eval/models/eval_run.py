"""
评测执行记录

每次 Workflow 改版 / 模型切换 / Prompt 调整都触发一次 eval_run。
跑完的指标如果回归（低于阈值且开关打开）会阻断 Workflow 上线（6004）。

EvalRun        ── 一次评测的总体记录
EvalRunItem    ── 该次评测下每条黄金集样本的实际产出 + 命中/未命中
"""
import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class EvalRun(BaseEntity):
    """一次评测的总体记录。"""

    __tablename__ = "ai_eval_run"
    __table_args__ = (
        Index("ix_ai_eval_run_tenant_scenario", "tenant_id", "scenario_code"),
        Index("ix_ai_eval_run_status", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_code: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_version: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="被评测的 Workflow 版本"
    )
    model_tier: Mapped[str | None] = mapped_column(
        String(8), nullable=True, comment="被评测的模型档位"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="状态机：pending / running / passed / failed / error",
    )
    total: Mapped[int | None] = mapped_column(comment="样本总数")
    passed: Mapped[int | None] = mapped_column(comment="通过数")
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="指标快照：accuracy / recall@k / citation_coverage / ...",
    )
    threshold: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="本次门禁阈值（与 metrics 同 key 比对）",
    )
    blocked_upgrade: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否因不达标而阻断上线",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="评测过程错误信息"
    )


class EvalRunItem(BaseEntity):
    """评测中的单个样本结果。"""

    __tablename__ = "ai_eval_run_item"
    __table_args__ = (
        Index("ix_ai_eval_item_run", "run_id"),
        Index("ix_ai_eval_item_passed", "run_id", "passed"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_eval_run.id", ondelete="CASCADE"),
        nullable=False,
    )
    golden_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_golden_set.id", ondelete="CASCADE"),
        nullable=False,
    )
    actual: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, comment="实际输出"
    )
    passed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True, comment="评分（0~1）")
    diff: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="与期望的 diff，便于人工复核",
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
