"""
通知模型

sys_notification — 系统通知表
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class Notification(BaseEntity):
    __tablename__ = "sys_notification"

    # 接收人
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="CASCADE"),
        index=True,
        comment="接收用户ID",
    )

    # 内容
    title: Mapped[str] = mapped_column(String(100), comment="标题")
    content: Mapped[str] = mapped_column(Text, comment="正文内容")
    type: Mapped[str] = mapped_column(
        String(20), index=True, comment="类型: system / todo / message"
    )
    level: Mapped[str] = mapped_column(
        String(20), default="info", server_default="info", comment="级别: info / warning / error"
    )

    # 状态
    is_read: Mapped[bool] = mapped_column(
        default=False, server_default="false", comment="是否已读"
    )
    read_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="已读时间"
    )

    # 关联来源（可选）
    source_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="来源模块, 如 archive, workflow"
    )
    source_id: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="来源对象ID"
    )
