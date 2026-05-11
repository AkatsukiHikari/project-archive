import uuid
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.repository.models.archive import ArchiveStaging, Catalog
from app.modules.repository.schemas.archive import ArchiveListQuery


class CatalogRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, catalog_id: uuid.UUID) -> Optional[Catalog]:
        result = await self._db.execute(
            select(Catalog).where(
                and_(Catalog.id == catalog_id, Catalog.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def list_by_fonds(self, fonds_id: uuid.UUID) -> list[Catalog]:
        result = await self._db.execute(
            select(Catalog).where(
                and_(Catalog.fonds_id == fonds_id, Catalog.is_deleted == False)
            )
        )
        return list(result.scalars().all())

    async def create(self, catalog: Catalog) -> Catalog:
        self._db.add(catalog)
        await self._db.flush()
        await self._db.refresh(catalog)
        return catalog

    async def delete(self, catalog: Catalog) -> None:
        catalog.is_deleted = True
        await self._db.flush()


class ArchiveRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, archive_id: uuid.UUID) -> Optional[ArchiveStaging]:
        result = await self._db.execute(
            select(ArchiveStaging).where(
                and_(ArchiveStaging.id == archive_id, ArchiveStaging.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def list_with_query(
        self, query: ArchiveListQuery, tenant_id: Optional[uuid.UUID] = None
    ) -> tuple[list[ArchiveStaging], int]:
        conditions: list = [ArchiveStaging.is_deleted == False]
        if tenant_id:
            conditions.append(ArchiveStaging.tenant_id == tenant_id)
        if query.fonds_id:
            conditions.append(ArchiveStaging.fonds_id == query.fonds_id)
        if query.catalog_id:
            conditions.append(ArchiveStaging.catalog_id == query.catalog_id)
        if query.category_id:
            conditions.append(ArchiveStaging.category_id == query.category_id)
        if query.ND:
            conditions.append(ArchiveStaging.ND == query.ND)
        if query.MJ:
            conditions.append(ArchiveStaging.MJ == query.MJ)
        if query.status:
            conditions.append(ArchiveStaging.status == query.status)
        if query.keyword:
            kw = f"%{query.keyword}%"
            conditions.append(or_(ArchiveStaging.TM.ilike(kw), ArchiveStaging.RZZ.ilike(kw)))

        count_result = await self._db.execute(
            select(func.count()).select_from(ArchiveStaging).where(and_(*conditions))
        )
        total = count_result.scalar_one()

        offset = (query.page - 1) * query.page_size
        result = await self._db.execute(
            select(ArchiveStaging)
            .where(and_(*conditions))
            .order_by(ArchiveStaging.create_time.desc())
            .offset(offset)
            .limit(query.page_size)
        )
        return list(result.scalars().all()), total

    async def create(self, archive: ArchiveStaging) -> ArchiveStaging:
        self._db.add(archive)
        await self._db.flush()
        await self._db.refresh(archive)
        return archive

    async def delete(self, archive: ArchiveStaging) -> None:
        archive.is_deleted = True
        await self._db.flush()
