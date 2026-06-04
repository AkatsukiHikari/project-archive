"""
AI Patch staging 表

AI 不直接写库 —— 任何 AI 写操作都先落到本表，由审核队列 HITL 闸门按租户配置走
auto / review / manual 三档处理。详见 docs/superpowers/specs/2026-05-11-archive-ai-agent-design.md §5.1 / §7.1。

每行 patch 描述一次"AI 想做的事"：
- target_type + target_id   指明落库目标（archive / catalog / kb_doc / ...）
- payload                   JSON 形态的 diff（新建为 {"create": {...}}，更新为字段级 {"field": {"from": x, "to": y}}）
- citations                 引用 chunk_id 列表（无引用 patch 不入队，6005）
- gate / status             闸门档位 + 状态机
- payload_hash              防篡改校验（approve 时核对，不一致返回 6003）
"""
import uuid
from typing import Any

from sqlalchemy import Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity
from app.modules.ai.models.ai_session import AISession  # noqa: F401 — 确保 FK 引用的表已加载


class AIPatch(BaseEntity):
    """AI 写操作 staging。"""

    __tablename__ = "ai_patch"
    __table_args__ = (
        Index("ix_ai_patch_tenant_status", "tenant_id", "status"),
        Index("ix_ai_patch_scenario", "scenario_code"),
        Index("ix_ai_patch_target", "target_type", "target_id"),
        Index("ix_ai_patch_session", "session_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户",
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_session.id", ondelete="SET NULL"),
        nullable=True,
        comment="提交时所在 AI 会话",
    )
    scenario_code: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="生成此 patch 的场景：attach / catalog / kb_manage / ..."
    )
    target_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="落库目标实体类型：archive / catalog / kb_doc / ...",
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        comment="目标 ID（新建型 patch 为空，approve 后回填）",
    )
    operation: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        comment="操作类型：create / update / delete",
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment="patch 数据：create→{create: {...}}；update→{字段: {from, to}}",
    )
    payload_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="payload SHA-256，approve 时校验未被篡改",
    )
    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default="[]",
        comment="引用列表：[{chunk_id, source_type, source_id, score, ...}, ...]",
    )
    confidence: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="AI 置信度（0~1），用于队列排序"
    )
    gate: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        default="review",
        server_default="review",
        comment="闸门档位：auto / review / manual",
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="状态机：pending / approved / rejected / applied / failed",
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="审核人 ID",
    )
    reviewer_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="审核意见"
    )
    workflow_version: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="产出该 patch 的 Workflow 版本"
    )
    dify_message_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="关联的 Dify message_id（用于回溯）"
    )
    apply_error: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="落库失败时的错误信息"
    )
