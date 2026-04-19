import uuid
from typing import Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.archive import Catalog, Archive
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

    async def get_by_id(self, archive_id: uuid.UUID) -> Optional[Archive]:
        result = await self._db.execute(
            select(Archive).where(
                and_(Archive.id == archive_id, Archive.is_deleted == False)
            )
        )
        return result.scalar_one_or_none()

    async def list_with_query(
        self, query: ArchiveListQuery, tenant_id: Optional[uuid.UUID] = None
    ) -> tuple[list[Archive], int]:
        conditions = [Archive.is_deleted == False, Archive.parent_id == None]
        if tenant_id:
            conditions.append(Archive.tenant_id == tenant_id)
        if query.fonds_id:
            conditions.append(Archive.fonds_id == query.fonds_id)
        if query.catalog_id:
            conditions.append(Archive.catalog_id == query.catalog_id)
        if query.category_id:
            conditions.append(Archive.category_id == query.category_id)
        if query.year:
            conditions.append(Archive.year == query.year)
        if query.security_level:
            conditions.append(Archive.security_level == query.security_level)
        if query.status:
            conditions.append(Archive.status == query.status)
        if query.keyword:
            kw = f"%{query.keyword}%"
            conditions.append(or_(Archive.title.ilike(kw), Archive.creator.ilike(kw)))

        count_result = await self._db.execute(
            select(func.count()).select_from(Archive).where(and_(*conditions))
        )
        total = count_result.scalar_one()

        offset = (query.page - 1) * query.page_size
        result = await self._db.execute(
            select(Archive)
            .where(and_(*conditions))
            .order_by(Archive.create_time.desc())
            .offset(offset)
            .limit(query.page_size)
        )
        return list(result.scalars().all()), total

    async def create(self, archive: Archive) -> Archive:
        self._db.add(archive)
        await self._db.flush()
        await self._db.refresh(archive)
        return archive

    async def delete(self, archive: Archive) -> None:
        archive.is_deleted = True
        await self._db.flush()
