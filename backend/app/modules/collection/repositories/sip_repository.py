import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.collection.models.sip import SIPRecord


class SQLAlchemySIPRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, sip: SIPRecord) -> SIPRecord:
        self.session.add(sip)
        await self.session.commit()
        await self.session.refresh(sip)
        return sip

    async def get_by_id(self, sip_id: uuid.UUID) -> Optional[SIPRecord]:
        stmt = select(SIPRecord).where(
            SIPRecord.id == sip_id,
            SIPRecord.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_submitter(
        self,
        submitter_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[SIPRecord]:
        stmt = (
            select(SIPRecord)
            .where(
                SIPRecord.submitter_id == submitter_id,
                SIPRecord.is_deleted == False,
            )
            .order_by(SIPRecord.create_time.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_tenant(
        self,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[SIPRecord]:
        stmt = (
            select(SIPRecord)
            .where(
                SIPRecord.tenant_id == tenant_id,
                SIPRecord.is_deleted == False,
            )
            .order_by(SIPRecord.create_time.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        sip: SIPRecord,
        new_status: str,
        notes: Optional[str] = None,
    ) -> SIPRecord:
        sip.status = new_status
        if notes is not None:
            sip.notes = notes
        self.session.add(sip)
        await self.session.commit()
        await self.session.refresh(sip)
        return sip

    async def save(self, sip: SIPRecord) -> SIPRecord:
        self.session.add(sip)
        await self.session.commit()
        await self.session.refresh(sip)
        return sip
