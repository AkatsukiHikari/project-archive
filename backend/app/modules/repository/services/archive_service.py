"""
档案库业务服务层
"""

import uuid
from typing import List, Optional

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException, AuthorizationException
from app.modules.iam.models.user import User
from app.modules.repository.models.archive import Fonds, ArchiveFile, ArchiveItem
from app.modules.repository.repositories.archive_repository import (
    FondsRepository,
    ArchiveFileRepository,
    ArchiveItemRepository,
)
from app.modules.repository.schemas.archive import (
    FondsCreate,
    FondsUpdate,
    ArchiveFileCreate,
    ArchiveFileUpdate,
    ArchiveItemCreate,
    ArchiveItemUpdate,
)


class FondsService:
    def __init__(self, repo: FondsRepository) -> None:
        self.repo = repo

    async def create_fonds(
        self, fonds_in: FondsCreate, current_user: User
    ) -> Fonds:
        # 全宗号唯一性校验
        existing = await self.repo.get_by_code(fonds_in.fonds_code)
        if existing:
            raise ValidationException(
                code=ErrorCode.FONDS_CODE_EXISTS,
                message=f"全宗号 '{fonds_in.fonds_code}' 已存在",
            )
        fonds = Fonds(
            **fonds_in.model_dump(exclude_none=True),
            create_by=current_user.id,
        )
        return await self.repo.create(fonds)

    async def get_fonds(self, fonds_id: uuid.UUID) -> Fonds:
        fonds = await self.repo.get_by_id(fonds_id)
        if not fonds:
            raise NotFoundException(
                code=ErrorCode.FONDS_NOT_FOUND, message="全宗不存在"
            )
        return fonds

    async def list_fonds(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Fonds]:
        # 超管看全部；租户用户只看自己租户
        tenant_id = None if current_user.is_superadmin else current_user.tenant_id
        return await self.repo.list_all(tenant_id=tenant_id, skip=skip, limit=limit)

    async def update_fonds(
        self, fonds_id: uuid.UUID, fonds_in: FondsUpdate
    ) -> Fonds:
        fonds = await self.get_fonds(fonds_id)
        update_data = fonds_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(fonds, field, value)
        return await self.repo.save(fonds)

    async def delete_fonds(self, fonds_id: uuid.UUID) -> None:
        fonds = await self.get_fonds(fonds_id)
        fonds.is_deleted = True
        await self.repo.save(fonds)


class ArchiveFileService:
    def __init__(
        self,
        file_repo: ArchiveFileRepository,
        fonds_repo: FondsRepository,
    ) -> None:
        self.file_repo = file_repo
        self.fonds_repo = fonds_repo

    async def create_archive_file(
        self, file_in: ArchiveFileCreate, current_user: User
    ) -> ArchiveFile:
        # 验证全宗存在
        fonds = await self.fonds_repo.get_by_id(file_in.fonds_id)
        if not fonds:
            raise NotFoundException(
                code=ErrorCode.FONDS_NOT_FOUND, message="全宗不存在"
            )
        # 租户隔离校验
        if not current_user.is_superadmin and current_user.tenant_id:
            if fonds.tenant_id and fonds.tenant_id != current_user.tenant_id:
                raise AuthorizationException(message="无权在此全宗下创建案卷")

        archive_file = ArchiveFile(
            **file_in.model_dump(exclude_none=True),
            create_by=current_user.id,
        )
        return await self.file_repo.create(archive_file)

    async def get_archive_file(self, file_id: uuid.UUID) -> ArchiveFile:
        af = await self.file_repo.get_by_id(file_id)
        if not af:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_FILE_NOT_FOUND, message="案卷不存在"
            )
        return af

    async def list_by_fonds(
        self,
        fonds_id: uuid.UUID,
        year: Optional[int] = None,
        security_level: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ArchiveFile]:
        return await self.file_repo.list_by_fonds(
            fonds_id, year=year, security_level=security_level,
            skip=skip, limit=limit,
        )

    async def update_archive_file(
        self, file_id: uuid.UUID, file_in: ArchiveFileUpdate
    ) -> ArchiveFile:
        af = await self.get_archive_file(file_id)
        update_data = file_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(af, field, value)
        return await self.file_repo.save(af)

    async def delete_archive_file(self, file_id: uuid.UUID) -> None:
        af = await self.get_archive_file(file_id)
        af.is_deleted = True
        await self.file_repo.save(af)

    async def accept_sip_as_archive_file(
        self,
        sip_id: uuid.UUID,
        fonds_id: uuid.UUID,
        file_number: str,
        current_user: User,
    ) -> ArchiveFile:
        """SIP 审批通过后，创建对应案卷并关联来源"""
        file_in = ArchiveFileCreate(
            fonds_id=fonds_id,
            file_number=file_number,
            title=f"SIP归档 - {file_number}",
            source_sip_id=sip_id,
            tenant_id=current_user.tenant_id,
        )
        return await self.create_archive_file(file_in, current_user)


class ArchiveItemService:
    def __init__(
        self,
        item_repo: ArchiveItemRepository,
        file_repo: ArchiveFileRepository,
    ) -> None:
        self.item_repo = item_repo
        self.file_repo = file_repo

    async def create_item(
        self, item_in: ArchiveItemCreate, current_user: User
    ) -> ArchiveItem:
        # 验证案卷存在
        af = await self.file_repo.get_by_id(item_in.archive_file_id)
        if not af:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_FILE_NOT_FOUND, message="案卷不存在"
            )
        item = ArchiveItem(
            **item_in.model_dump(exclude_none=True),
            create_by=current_user.id,
        )
        created = await self.item_repo.create(item)
        # 更新案卷条目计数
        await self.file_repo.increment_item_count(item_in.archive_file_id, delta=1)
        return created

    async def get_item(self, item_id: uuid.UUID) -> ArchiveItem:
        item = await self.item_repo.get_by_id(item_id)
        if not item:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_ITEM_NOT_FOUND, message="文件条目不存在"
            )
        return item

    async def list_by_archive_file(
        self,
        archive_file_id: uuid.UUID,
        item_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ArchiveItem]:
        return await self.item_repo.list_by_archive_file(
            archive_file_id, item_type=item_type, skip=skip, limit=limit
        )

    async def update_item(
        self, item_id: uuid.UUID, item_in: ArchiveItemUpdate
    ) -> ArchiveItem:
        item = await self.get_item(item_id)
        update_data = item_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(item, field, value)
        return await self.item_repo.save(item)

    async def delete_item(self, item_id: uuid.UUID) -> None:
        item = await self.get_item(item_id)
        af_id = item.archive_file_id
        item.is_deleted = True
        await self.item_repo.save(item)
        await self.file_repo.increment_item_count(af_id, delta=-1)
