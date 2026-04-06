import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.preservation.models.detection import DetectionRecord


class SQLAlchemyDetectionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, record: DetectionRecord) -> DetectionRecord:
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_by_id(self, record_id: uuid.UUID) -> Optional[DetectionRecord]:
        stmt = select(DetectionRecord).where(
            DetectionRecord.id == record_id,
            DetectionRecord.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_archive(
        self,
        archive_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[DetectionRecord]:
        stmt = (
            select(DetectionRecord)
            .where(
                DetectionRecord.archive_id == archive_id,
                DetectionRecord.is_deleted == False,
            )
            .order_by(DetectionRecord.create_time.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self, skip: int = 0, limit: int = 20) -> List[DetectionRecord]:
        stmt = (
            select(DetectionRecord)
            .where(DetectionRecord.is_deleted == False)
            .order_by(DetectionRecord.create_time.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
