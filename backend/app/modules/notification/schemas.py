"""
通知 Pydantic Schemas
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NotificationBase(BaseModel):
    """通知基础字段"""
    title: str
    content: str
    type: str = "system"  # system / todo / message
    level: str = "info"   # info / warning / error
    source_type: Optional[str] = None
    source_id: Optional[str] = None


class NotificationCreate(NotificationBase):
    """创建通知请求"""
    user_id: uuid.UUID


class NotificationOut(NotificationBase):
    """通知响应"""
    id: uuid.UUID
    user_id: uuid.UUID
    is_read: bool
    read_time: Optional[datetime] = None
    create_time: datetime

    model_config = {"from_attributes": True}


class NotificationPage(BaseModel):
    """分页响应"""
    items: list[NotificationOut]
    total: int
    page: int
    page_size: int


class UnreadCount(BaseModel):
    """未读数量"""
    count: int
