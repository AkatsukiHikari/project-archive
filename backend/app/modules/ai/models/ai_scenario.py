"""
AI 场景配置表

每个租户为每个 AI 能力（问答 / 检索 / 摘要 / 自动挂接 / 自动编目 / 四性 / 拟稿 / 关联 / KB 管理）
配置一行：是否启用、Dify App / Workflow 绑定、模型档位映射、HITL 闸门档位。

模型档位（model_tier）= 用户看到的"快 / 准 / 思考"三档抽象，
实际 LLM provider/model id 写在 ``model_mapping`` JSON 里，由 ``ai/services/scenario_router`` 解析。

HITL 闸门（gate）= ``auto`` / ``review`` / ``manual``：
- auto    AI 出 patch 直接 approve 落库
- review  进审核队列，等人点（默认）
- manual  带"高风险"标记置顶，必须二审签
"""
import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class AIScenario(BaseEntity):
    """AI 能力场景配置（按租户）。"""

    __tablename__ = "ai_scenario"
    __table_args__ = (
        UniqueConstraint("tenant_id", "scenario_code", name="uq_ai_scenario_tenant_code"),
        Index("ix_ai_scenario_tenant", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户",
    )
    scenario_code: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="能力码：qa/search/summary/attach/catalog/4nat/draft/relate/kb_manage",
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False, comment="显示名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="说明")
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", comment="是否启用"
    )
    dify_app_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="对应 Dify App ID（主 Chatflow 或子 Workflow）"
    )
    dify_workflow_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="子 Workflow ID（如适用）"
    )
    workflow_version: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="当前生效 Workflow 版本号（与 Eval 绑定）"
    )
    default_model_tier: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="准",
        server_default="准",
        comment="默认模型档位：快 / 准 / 思考",
    )
    model_mapping: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="档位→模型映射：{ '快': {'provider':'qwen','model':'qwen-turbo'}, ... }",
    )
    gate: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="review",
        server_default="review",
        comment="HITL 闸门档位：auto / review / manual（仅写类场景生效）",
    )
    citation_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="是否强制引用（无 evidence 拒答）",
    )
    extra_config: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default="{}",
        comment="扩展配置（Prompt 模板覆盖、阈值等）",
    )
