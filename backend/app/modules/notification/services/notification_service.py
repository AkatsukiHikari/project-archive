"""
通知服务层
"""

import uuid
import logging
from typing import Optional

from app.modules.notification.models.notification import Notification
from app.modules.notification.repositories.notification_repository import NotificationRepository
from app.modules.notification.schemas import NotificationCreate

logger = logging.getLogger(__name__)


class NotificationService:
    """通知业务逻辑"""

    def __init__(self, repo: NotificationRepository):
        self.repo = repo

    async def create_notification(self, notification_in: NotificationCreate) -> Notification:
        """创建通知，并通过 WebSocket 实时推送给目标用户"""
        notification = await self.repo.create(notification_in)

        # ── WebSocket 实时推送 ──
        try:
            from app.infra.ws.manager import ws_manager
            from app.modules.notification.schemas import NotificationOut

            payload = NotificationOut.model_validate(notification).model_dump(mode="json")
            await ws_manager.send_personal(
                user_id=str(notification.user_id),
                event="notification:new",
                data=payload,
            )
        except Exception as e:
            # 推送失败不影响通知创建流程
            logger.warning("WebSocket 推送通知失败: %s", str(e))

        return notification

    async def get_user_notifications(
        self,
        user_id: uuid.UUID,
        type_filter: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        """获取用户通知（分页）"""
        return await self.repo.get_by_user(user_id, type_filter, page, page_size)

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """获取未读数量"""
        return await self.repo.get_unread_count(user_id)

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """标记单条已读"""
        return await self.repo.mark_as_read(notification_id, user_id)

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        """全部标记已读"""
        return await self.repo.mark_all_read(user_id)

    async def delete_notification(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """删除通知（逻辑删除）"""
        return await self.repo.delete(notification_id, user_id)

