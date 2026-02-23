"""
通知模块依赖注入
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.notification.repositories.notification_repository import (
    SQLAlchemyNotificationRepository,
)
from app.modules.notification.services.notification_service import NotificationService


def get_notification_service(
    db: AsyncSession = Depends(get_db),
) -> NotificationService:
    """构建 NotificationService 实例（Repository → Service）"""
    repo = SQLAlchemyNotificationRepository(db)
    return NotificationService(repo)
