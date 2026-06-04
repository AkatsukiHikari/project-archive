"""
AI 会话元数据表

承载用户在 ``/ai`` 独立页里的对话记录索引。
对话内容的真正存储在 Dify 端（``dify_conversation_id`` 是外键），
本表只存：标题、最后场景、最后模型档位、消息数、所属用户/租户。

软删除沿用 BaseEntity 的 ``is_deleted``。
"""
import uuid

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class AISession(BaseEntity):
    """用户会话索引（一行 = 一段对话）。"""

    __tablename__ = "ai_session"
    __table_args__ = (
        Index("ix_ai_session_user_recent", "tenant_id", "user_id", "update_time"),
        Index("ix_ai_session_dify_conv", "dify_conversation_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=False,
        comment="所属租户",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="CASCADE"),
        nullable=False,
        comment="发起用户",
    )
    dify_conversation_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        comment="Dify 会话 ID（首次发问后填入）",
    )
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="新对话",
        server_default="新对话",
        comment="会话标题（首条消息自动摘要）",
    )
    last_scenario_code: Mapped[str | None] = mapped_column(
        String(32), nullable=True, comment="上一次使用的场景"
    )
    last_model_tier: Mapped[str | None] = mapped_column(
        String(8), nullable=True, comment="上一次使用的模型档位"
    )
    message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="消息数（人 + AI）",
    )
