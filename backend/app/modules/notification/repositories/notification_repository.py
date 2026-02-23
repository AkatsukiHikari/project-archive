"""
通知仓储层

遵循项目 DDD 模式：接口 + SQLAlchemy 实现
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notification.models.notification import Notification
from app.modules.notification.schemas import NotificationCreate


class NotificationRepository(ABC):
    """[Repository Interface] 通知仓储接口"""

    @abstractmethod
    async def create(self, notification_in: NotificationCreate) -> Notification:
        pass

    @abstractmethod
    async def get_by_user(
        self,
        user_id: uuid.UUID,
        type_filter: Optional[str],
        page: int,
        page_size: int,
    ) -> tuple[list[Notification], int]:
        pass

    @abstractmethod
    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        pass

    @abstractmethod
    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        pass

    @abstractmethod
    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        pass

    @abstractmethod
    async def delete(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        pass


class SQLAlchemyNotificationRepository(NotificationRepository):
    """[Repository Implementation] SQLAlchemy 通知仓储实现"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, notification_in: NotificationCreate) -> Notification:
        notification = Notification(
            user_id=notification_in.user_id,
            title=notification_in.title,
            content=notification_in.content,
            type=notification_in.type,
            level=notification_in.level,
            source_type=notification_in.source_type,
            source_id=notification_in.source_id,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        type_filter: Optional[str],
        page: int,
        page_size: int,
    ) -> tuple[list[Notification], int]:
        base_query = select(Notification).where(
            Notification.user_id == user_id,
            Notification.is_deleted == False,
        )

        if type_filter:
            base_query = base_query.where(Notification.type == type_filter)

        # 总数
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # 分页数据（最新在前）
        items_query = (
            base_query.order_by(Notification.create_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(items_query)
        items = list(result.scalars().all())

        return items, total

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        query = select(func.count()).where(
            Notification.user_id == user_id,
            Notification.is_read == False,
            Notification.is_deleted == False,
        )
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .values(is_read=True, read_time=datetime.now(timezone.utc))
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,
                Notification.is_deleted == False,
            )
            .values(is_read=True, read_time=datetime.now(timezone.utc))
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount

    async def delete(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """逻辑删除"""
        stmt = (
            update(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
            .values(is_deleted=True)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        return result.rowcount > 0
