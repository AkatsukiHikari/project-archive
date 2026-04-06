from sqlalchemy import String, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.common.entity.base import BaseEntity
from typing import List, Optional
from datetime import datetime
import uuid

class ScheduleEvent(BaseEntity):
    __tablename__ = "schedule_events"

    title: Mapped[str] = mapped_column(String(255), comment="日程标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="日程描述")
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="开始时间")
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="结束时间")
    is_all_day: Mapped[bool] = mapped_column(default=False, comment="是否全天")
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="地点")
    event_type: Mapped[str] = mapped_column(String(50), default="meeting", comment="日程类型")

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_tenant.id", ondelete="CASCADE"), index=True, nullable=True, comment="所属租户ID")
    creator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_user.id", ondelete="CASCADE"), index=True, comment="创建者ID")

    participants: Mapped[List["ScheduleParticipant"]] = relationship(
        "ScheduleParticipant", back_populates="event", cascade="all, delete-orphan"
    )

class ScheduleParticipant(BaseEntity):
    __tablename__ = "schedule_participants"

    event_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedule_events.id", ondelete="CASCADE"), index=True, comment="日程ID")
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_user.id", ondelete="CASCADE"), index=True, comment="用户ID")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="参与状态: pending, accepted, declined")

    event: Mapped["ScheduleEvent"] = relationship("ScheduleEvent", back_populates="participants")
