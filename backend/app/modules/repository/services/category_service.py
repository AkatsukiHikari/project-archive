import uuid
import copy
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.repositories.category_repo import CategoryRepository
from app.modules.repository.schemas.category import CategoryCreate, CategoryUpdate
from app.common.exceptions.base import NotFoundException, ValidationException
from app.common.error_code import ErrorCode


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = CategoryRepository(db)

    async def create(
        self, data: CategoryCreate, tenant_id: Optional[uuid.UUID]
    ) -> ArchiveCategory:
        existing = await self._repo.get_by_code(data.code)
        if existing:
            raise ValidationException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"门类代码 {data.code!r} 已存在"
            )
        category = ArchiveCategory(
            code=data.code,
            name=data.name,
            parent_id=data.parent_id,
            base_category_id=data.base_category_id,
            is_builtin=data.is_builtin,
            requires_privacy_guard=data.requires_privacy_guard,
            field_schema=[f.model_dump() for f in data.field_schema] if data.field_schema else None,
            tenant_id=tenant_id,
        )
        return await self._repo.create(category)

    async def clone(
        self, source_id: uuid.UUID, new_code: str, new_name: str, tenant_id: uuid.UUID
    ) -> ArchiveCategory:
        source = await self._repo.get_by_id(source_id)
        if not source:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_NOT_FOUND, message="来源门类不存在"
            )
        existing = await self._repo.get_by_code(new_code)
        if existing:
            raise ValidationException(
                code=ErrorCode.VALIDATION_ERROR, message=f"门类代码 {new_code!r} 已存在"
            )
        cloned_schema = copy.deepcopy(source.field_schema) if source.field_schema else None
        if cloned_schema:
            for field in cloned_schema:
                field["inherited"] = True

        cloned = ArchiveCategory(
            code=new_code,
            name=new_name,
            parent_id=source.parent_id,
            base_category_id=source.id,
            is_builtin=False,
            requires_privacy_guard=source.requires_privacy_guard,
            field_schema=cloned_schema,
            tenant_id=tenant_id,
        )
        return await self._repo.create(cloned)

    async def update(self, category_id: uuid.UUID, data: CategoryUpdate) -> ArchiveCategory:
        category = await self._repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="门类不存在")
        if data.name is not None:
            category.name = data.name
        if data.requires_privacy_guard is not None:
            category.requires_privacy_guard = data.requires_privacy_guard
        if data.field_schema is not None:
            category.field_schema = [f.model_dump() for f in data.field_schema]
        return category

    async def get(self, category_id: uuid.UUID) -> ArchiveCategory:
        category = await self._repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="门类不存在")
        return category

    async def update_schema(
        self, category_id: uuid.UUID, field_schema: list
    ) -> ArchiveCategory:
        """专用：仅更新 field_schema（表单设计器保存入口）。"""
        category = await self._repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="门类不存在")
        category.field_schema = field_schema
        return category

    async def delete(self, category_id: uuid.UUID) -> None:
        category = await self._repo.get_by_id(category_id)
        if not category:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="门类不存在")
        if category.is_builtin:
            raise ValidationException(
                code=ErrorCode.VALIDATION_ERROR, message="内置门类不可删除"
            )
        await self._repo.delete(category)

    async def list_all(
        self, tenant_id: Optional[uuid.UUID] = None, parent_id: Optional[uuid.UUID] = None
    ) -> list[ArchiveCategory]:
        return await self._repo.list_all(tenant_id=tenant_id, parent_id=parent_id)
