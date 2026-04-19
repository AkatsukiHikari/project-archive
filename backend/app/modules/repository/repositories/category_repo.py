import uuid
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.category import ArchiveCategory


class CategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, category_id: uuid.UUID) -> Optional[ArchiveCategory]:
        result = await self._db.execute(
            select(ArchiveCategory).where(
                and_(ArchiveCategory.id == category_id, ArchiveCategory.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[ArchiveCategory]:
        result = await self._db.execute(
            select(ArchiveCategory).where(
                and_(ArchiveCategory.code == code, ArchiveCategory.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        parent_id: Optional[uuid.UUID] = None,
    ) -> list[ArchiveCategory]:
        conditions = [ArchiveCategory.is_deleted == False]
        if tenant_id is not None:
            conditions.append(
                (ArchiveCategory.tenant_id == tenant_id) | (ArchiveCategory.tenant_id == None)
            )
        if parent_id is not None:
            conditions.append(ArchiveCategory.parent_id == parent_id)
        result = await self._db.execute(
            select(ArchiveCategory).where(and_(*conditions))
        )
        return list(result.scalars().all())

    async def create(self, category: ArchiveCategory) -> ArchiveCategory:
        self._db.add(category)
        await self._db.flush()
        await self._db.refresh(category)
        return category

    async def delete(self, category: ArchiveCategory) -> None:
        category.is_deleted = True
        await self._db.flush()
