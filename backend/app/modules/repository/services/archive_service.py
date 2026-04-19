import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.archive import Catalog, Archive
from app.modules.repository.repositories.archive_repo import CatalogRepository, ArchiveRepository
from app.modules.repository.schemas.archive import (
    CatalogCreate,
    ArchiveCreate, ArchiveUpdate, ArchiveListQuery,
)
from app.common.exceptions.base import NotFoundException
from app.common.error_code import ErrorCode


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
            org_mode=data.org_mode,
            tenant_id=tenant_id,
        )
        return await self._repo.create(catalog)

    async def list_by_fonds(self, fonds_id: uuid.UUID) -> list[Catalog]:
        return await self._repo.list_by_fonds(fonds_id)

    async def delete(self, catalog_id: uuid.UUID) -> None:
        catalog = await self._repo.get_by_id(catalog_id)
        if not catalog:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="目录不存在")
        await self._repo.delete(catalog)


class ArchiveService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ArchiveRepository(db)

    async def create(self, data: ArchiveCreate, tenant_id: Optional[uuid.UUID]) -> Archive:
        archive = Archive(
            fonds_id=data.fonds_id,
            catalog_id=data.catalog_id,
            parent_id=data.parent_id,
            category_id=data.category_id,
            level=data.level,
            title=data.title,
            fonds_code=data.fonds_code,
            year=data.year,
            creator=data.creator,
            catalog_no=data.catalog_no,
            volume_no=data.volume_no,
            item_no=data.item_no,
            archive_no=data.archive_no,
            security_level=data.security_level,
            retention_period=data.retention_period,
            doc_date=data.doc_date,
            pages=data.pages,
            ext_fields=data.ext_fields,
            storage_key=data.storage_key,
            storage_bucket=data.storage_bucket,
            file_size=data.file_size,
            file_format=data.file_format,
            sha256_hash=data.sha256_hash,
            status="active",
            embedding_status="pending",
            tenant_id=tenant_id,
        )
        return await self._repo.create(archive)

    async def get(self, archive_id: uuid.UUID) -> Archive:
        archive = await self._repo.get_by_id(archive_id)
        if not archive:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="档案不存在")
        return archive

    async def update(self, archive_id: uuid.UUID, data: ArchiveUpdate) -> Archive:
        archive = await self._repo.get_by_id(archive_id)
        if not archive:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="档案不存在")
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(archive, field, value)
        return archive

    async def delete(self, archive_id: uuid.UUID) -> None:
        archive = await self._repo.get_by_id(archive_id)
        if not archive:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="档案不存在")
        await self._repo.delete(archive)

    async def list_archives(
        self, query: ArchiveListQuery, tenant_id: Optional[uuid.UUID] = None
    ) -> tuple[list[Archive], int]:
        return await self._repo.list_with_query(query, tenant_id=tenant_id)
