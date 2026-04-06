import uuid
import logging
from typing import List, Optional
from datetime import datetime
from app.modules.schedule.models import ScheduleEvent, ScheduleParticipant
from app.modules.schedule.schemas import ScheduleEventCreate, ScheduleEventUpdate
from app.modules.schedule.repositories import SQLAlchemyScheduleRepository
from app.common.exceptions.base import NotFoundException, AuthorizationException

logger = logging.getLogger(__name__)

class ScheduleService:
    def __init__(self, repo: SQLAlchemyScheduleRepository):
        self.repo = repo

    async def list_user_schedules(self, user_id: uuid.UUID, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None):
        return await self.repo.list_for_user(user_id, start_time, end_time)

    async def get_schedule(self, event_id: uuid.UUID, current_user_id: uuid.UUID):
        event = await self.repo.get_by_id(event_id)
        if not event:
            raise NotFoundException(message="日程不存在")
        # Optional: check if user has access (is creator or participant)
        has_access = (event.creator_id == current_user_id) or any(p.user_id == current_user_id for p in event.participants)
        if not has_access:
            raise AuthorizationException(message="无权查看该日程")
        return event

    async def create_schedule(self, current_user_id: uuid.UUID, event_in: ScheduleEventCreate):
        event = ScheduleEvent(
            title=event_in.title,
            description=event_in.description,
            start_time=event_in.start_time,
            end_time=event_in.end_time,
            is_all_day=event_in.is_all_day,
            location=event_in.location,
            event_type=event_in.event_type,
            creator_id=current_user_id
        )
        await self.repo.create(event)

        participant_ids_set: set[uuid.UUID] = set()
        if event_in.participant_ids:
            # exclude creator just in case they added themselves
            participant_ids_set = set(event_in.participant_ids)
            participant_ids_set.discard(current_user_id)
            participants = [
                ScheduleParticipant(event_id=event.id, user_id=uid, status="pending")
                for uid in participant_ids_set
            ]
            if participants:
                await self.repo.add_participants(participants)

        await self.repo.commit()

        # 通知参与者
        if participant_ids_set:
            await self._notify_participants(
                participant_ids=participant_ids_set,
                event_title=event.title,
                creator_id=current_user_id,
            )

        # reload to get relations
        return await self.repo.get_by_id(event.id)

    async def _notify_participants(
        self,
        participant_ids: set[uuid.UUID],
        event_title: str,
        creator_id: uuid.UUID,
    ) -> None:
        """向所有被邀请的参与者发送日程邀请通知"""
        try:
            from app.modules.notification.services.notification_service import NotificationService
            from app.modules.notification.repositories.notification_repository import SQLAlchemyNotificationRepository
            from app.modules.notification.schemas import NotificationCreate
            from app.infra.db.session import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                notif_repo = SQLAlchemyNotificationRepository(db)
                notif_service = NotificationService(notif_repo)
                for uid in participant_ids:
                    await notif_service.create_notification(
                        NotificationCreate(
                            user_id=uid,
                            title="日程邀请",
                            content=f"您被邀请参加日程：{event_title}",
                            type="todo",
                            level="info",
                            source_type="schedule",
                            source_id=str(creator_id),
                        )
                    )
        except Exception as e:
            logger.warning("发送日程邀请通知失败: %s", str(e))

    async def update_schedule(self, event_id: uuid.UUID, current_user_id: uuid.UUID, event_in: ScheduleEventUpdate):
        event = await self.get_schedule(event_id, current_user_id)
        if event.creator_id != current_user_id:
            raise AuthorizationException(message="只有创建者可以修改日程")

        # Update fields
        update_data = event_in.model_dump(exclude_unset=True, exclude={"participant_ids"})
        for k, v in update_data.items():
            setattr(event, k, v)
        
        await self.repo.save(event)

        # Update participants
        if event_in.participant_ids is not None:
            await self.repo.delete_participants(event_id)
            participant_ids = set(event_in.participant_ids)
            participant_ids.discard(current_user_id)
            participants = [
                ScheduleParticipant(event_id=event.id, user_id=uid, status="pending")
                for uid in participant_ids
            ]
            if participants:
                await self.repo.add_participants(participants)

        await self.repo.commit()
        return await self.repo.get_by_id(event_id)

    async def delete_schedule(self, event_id: uuid.UUID, current_user_id: uuid.UUID):
        event = await self.get_schedule(event_id, current_user_id)
        if event.creator_id != current_user_id:
            raise AuthorizationException(message="只有创建者可以删除日程")
        
        event.is_deleted = True
        await self.repo.save(event)
        await self.repo.commit()
