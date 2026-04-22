import uuid
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.fonds import Fonds


class FondsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, fonds_id: uuid.UUID) -> Optional[Fonds]:
        result = await self._db.execute(
            select(Fonds).where(and_(Fonds.id == fonds_id, Fonds.is_deleted == False))
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, fonds_code: str) -> Optional[Fonds]:
        result = await self._db.execute(
            select(Fonds).where(and_(Fonds.fonds_code == fonds_code, Fonds.is_deleted == False))
        )
        return result.scalar_one_or_none()

    async def list_all(self, tenant_id: Optional[uuid.UUID] = None) -> list[Fonds]:
        conditions = [Fonds.is_deleted == False]
        if tenant_id is not None:
            conditions.append(Fonds.tenant_id == tenant_id)
        result = await self._db.execute(
            select(Fonds).where(and_(*conditions)).order_by(Fonds.fonds_code)
        )
        return list(result.scalars().all())

    async def create(self, fonds: Fonds) -> Fonds:
        self._db.add(fonds)
        await self._db.flush()
        await self._db.refresh(fonds)
        return fonds

    async def delete(self, fonds: Fonds) -> None:
        fonds.is_deleted = True
        await self._db.flush()
