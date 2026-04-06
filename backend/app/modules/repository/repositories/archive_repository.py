"""
档案库 Repository 层（数据访问）
"""

import uuid
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.repository.models.archive import Fonds, ArchiveFile, ArchiveItem


class FondsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, fonds_id: uuid.UUID) -> Optional[Fonds]:
        result = await self.db.execute(
            select(Fonds).where(Fonds.id == fonds_id, Fonds.is_deleted == False)
        )
        return result.scalars().first()

    async def get_by_code(self, fonds_code: str) -> Optional[Fonds]:
        result = await self.db.execute(
            select(Fonds).where(Fonds.fonds_code == fonds_code, Fonds.is_deleted == False)
        )
        return result.scalars().first()

    async def list_all(
        self,
        tenant_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Fonds]:
        stmt = select(Fonds).where(Fonds.is_deleted == False)
        if tenant_id:
            stmt = stmt.where(Fonds.tenant_id == tenant_id)
        stmt = stmt.order_by(Fonds.fonds_code).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, fonds: Fonds) -> Fonds:
        self.db.add(fonds)
        await self.db.commit()
        await self.db.refresh(fonds)
        return fonds

    async def save(self, fonds: Fonds) -> Fonds:
        await self.db.commit()
        await self.db.refresh(fonds)
        return fonds

    async def count_archive_files(self, fonds_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(ArchiveFile).where(
                ArchiveFile.fonds_id == fonds_id,
                ArchiveFile.is_deleted == False,
            )
        )
        return result.scalar_one()


class ArchiveFileRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, file_id: uuid.UUID) -> Optional[ArchiveFile]:
        result = await self.db.execute(
            select(ArchiveFile).where(
                ArchiveFile.id == file_id,
                ArchiveFile.is_deleted == False,
            )
        )
        return result.scalars().first()

    async def list_by_fonds(
        self,
        fonds_id: uuid.UUID,
        year: Optional[int] = None,
        security_level: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ArchiveFile]:
        stmt = select(ArchiveFile).where(
            ArchiveFile.fonds_id == fonds_id,
            ArchiveFile.is_deleted == False,
        )
        if year:
            stmt = stmt.where(ArchiveFile.year == year)
        if security_level:
            stmt = stmt.where(ArchiveFile.security_level == security_level)
        stmt = stmt.order_by(ArchiveFile.file_number).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, archive_file: ArchiveFile) -> ArchiveFile:
        self.db.add(archive_file)
        await self.db.commit()
        await self.db.refresh(archive_file)
        return archive_file

    async def save(self, archive_file: ArchiveFile) -> ArchiveFile:
        await self.db.commit()
        await self.db.refresh(archive_file)
        return archive_file

    async def increment_item_count(self, file_id: uuid.UUID, delta: int = 1) -> None:
        archive_file = await self.get_by_id(file_id)
        if archive_file:
            archive_file.item_count = max(0, archive_file.item_count + delta)
            await self.db.commit()


class ArchiveItemRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, item_id: uuid.UUID) -> Optional[ArchiveItem]:
        result = await self.db.execute(
            select(ArchiveItem).where(
                ArchiveItem.id == item_id,
                ArchiveItem.is_deleted == False,
            )
        )
        return result.scalars().first()

    async def list_by_archive_file(
        self,
        archive_file_id: uuid.UUID,
        item_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ArchiveItem]:
        stmt = select(ArchiveItem).where(
            ArchiveItem.archive_file_id == archive_file_id,
            ArchiveItem.is_deleted == False,
        )
        if item_type:
            stmt = stmt.where(ArchiveItem.item_type == item_type)
        stmt = stmt.order_by(ArchiveItem.item_number).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_pending_embedding(self, limit: int = 50) -> List[ArchiveItem]:
        """获取尚未向量化的条目，供 Celery 任务消费"""
        result = await self.db.execute(
            select(ArchiveItem)
            .where(
                ArchiveItem.embedding_status == "pending",
                ArchiveItem.is_deleted == False,
                ArchiveItem.storage_key.is_not(None),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, item: ArchiveItem) -> ArchiveItem:
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def save(self, item: ArchiveItem) -> ArchiveItem:
        await self.db.commit()
        await self.db.refresh(item)
        return item

    async def update_embedding_status(
        self, item_id: uuid.UUID, status: str
    ) -> None:
        item = await self.get_by_id(item_id)
        if item:
            item.embedding_status = status
            await self.db.commit()
