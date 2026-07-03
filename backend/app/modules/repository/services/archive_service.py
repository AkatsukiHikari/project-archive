import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException
from app.modules.repository.models.archive import ArchiveStaging, Catalog
from app.modules.repository.repositories.archive_repo import ArchiveRepository, CatalogRepository
from app.modules.repository.schemas.archive import (
    ArchiveCreate,
    ArchiveListQuery,
    ArchiveUpdate,
    CatalogCreate,
    CatalogUpdate,
)


class CatalogService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = CatalogRepository(db)

    async def create(self, data: CatalogCreate, tenant_id: Optional[uuid.UUID]) -> Catalog:
        catalog = Catalog(
            fonds_id=data.fonds_id,
            category_id=data.category_id,
            catalog_no=data.catalog_no,
            name=data.name,
            year=data.year,
            catalog_type=data.catalog_type,
            volume_archive_id=data.volume_archive_id,
            tenant_id=tenant_id,
        )
        return await self._repo.create(catalog)

    async def list_by_fonds(self, fonds_id: uuid.UUID) -> list[Catalog]:
        return await self._repo.list_by_fonds(fonds_id)

    async def update(self, catalog_id: uuid.UUID, data: CatalogUpdate) -> Catalog:
        catalog = await self._repo.get_by_id(catalog_id)
        if not catalog:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="目录不存在")
        update_data = data.model_dump(exclude_unset=True)
        for field in ("name", "year", "catalog_type", "volume_archive_id"):
            if field in update_data:
                setattr(catalog, field, update_data[field])
        return catalog

    async def delete(self, catalog_id: uuid.UUID) -> None:
        catalog = await self._repo.get_by_id(catalog_id)
        if not catalog:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="目录不存在")
        await self._repo.delete(catalog)


class ArchiveService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ArchiveRepository(db)

    async def create(self, data: ArchiveCreate, tenant_id: Optional[uuid.UUID]) -> ArchiveStaging:
        archive = ArchiveStaging(
            fonds_id=data.fonds_id,
            catalog_id=data.catalog_id,
            category_id=data.category_id,
            TM=data.TM,
            QZH=data.QZH,
            ND=data.ND,
            RZZ=data.RZZ,
            DH=data.DH,
            MJ=data.MJ,
            BGQX=data.BGQX,
            WJRQ=data.WJRQ,
            YS=data.YS,
            ext_fields=data.ext_fields,
            status="draft",
            embedding_status="pending",
            tenant_id=tenant_id,
        )
        return await self._repo.create(archive)

    async def get(self, archive_id: uuid.UUID) -> ArchiveStaging:
        archive = await self._repo.get_by_id(archive_id)
        if not archive:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="档案不存在")
        return archive

    async def update(self, archive_id: uuid.UUID, data: ArchiveUpdate) -> ArchiveStaging:
        archive = await self._repo.get_by_id(archive_id)
        if not archive:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="档案不存在")
        update_data = data.model_dump(exclude_unset=True)
        for field in ("TM", "RZZ", "ND", "WJRQ", "YS", "MJ", "BGQX", "DH", "status", "ext_fields"):
            if field in update_data:
                setattr(archive, field, update_data[field])
        return archive

    async def delete(self, archive_id: uuid.UUID) -> None:
        archive = await self._repo.get_by_id(archive_id)
        if not archive:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="档案不存在")
        await self._repo.delete(archive)

    async def list_archives(
        self, query: ArchiveListQuery, tenant_id: Optional[uuid.UUID] = None,
        source: str = "staging",
    ):
        from app.modules.repository.models.archive import Archive

        model = Archive if source == "formal" else ArchiveStaging
        return await self._repo.list_with_query(query, tenant_id=tenant_id, model=model)
