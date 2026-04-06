import uuid
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.modules.schedule.models import ScheduleEvent, ScheduleParticipant

class SQLAlchemyScheduleRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, event_id: uuid.UUID) -> Optional[ScheduleEvent]:
        stmt = select(ScheduleEvent).options(selectinload(ScheduleEvent.participants)).where(ScheduleEvent.id == event_id, ScheduleEvent.is_deleted == False)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: uuid.UUID, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[ScheduleEvent]:
        # User is creator or participant
        stmt = select(ScheduleEvent).outerjoin(ScheduleParticipant).options(selectinload(ScheduleEvent.participants)).where(
            and_(
                ScheduleEvent.is_deleted == False,
                or_(
                    ScheduleEvent.creator_id == user_id,
                    and_(ScheduleParticipant.user_id == user_id, ScheduleParticipant.is_deleted == False)
                )
            )
        ).distinct()

        if start_time:
            stmt = stmt.where(ScheduleEvent.end_time >= start_time)
        if end_time:
            stmt = stmt.where(ScheduleEvent.start_time <= end_time)

        stmt = stmt.order_by(ScheduleEvent.start_time.asc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, event: ScheduleEvent) -> ScheduleEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def add_participants(self, participants: List[ScheduleParticipant]):
        self.session.add_all(participants)

    async def delete_participants(self, event_id: uuid.UUID):
        stmt = select(ScheduleParticipant).where(ScheduleParticipant.event_id == event_id)
        result = await self.session.execute(stmt)
        for p in result.scalars():
            await self.session.delete(p)

    async def save(self, event: ScheduleEvent) -> ScheduleEvent:
        self.session.add(event)
        await self.session.flush()
        return event

    async def commit(self):
        await self.session.commit()
