import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.repository.models.fonds import Fonds
from app.modules.repository.repositories.fonds_repo import FondsRepository
from app.modules.repository.schemas.fonds import FondsCreate, FondsUpdate
from app.common.exceptions.base import NotFoundException, ValidationException
from app.common.error_code import ErrorCode


class FondsService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = FondsRepository(db)

    async def list_all(self, tenant_id: Optional[uuid.UUID] = None) -> list[Fonds]:
        return await self._repo.list_all(tenant_id=tenant_id)

    async def get(self, fonds_id: uuid.UUID) -> Fonds:
        fonds = await self._repo.get_by_id(fonds_id)
        if not fonds:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="全宗不存在")
        return fonds

    async def create(self, data: FondsCreate, tenant_id: Optional[uuid.UUID]) -> Fonds:
        existing = await self._repo.get_by_code(data.fonds_code)
        if existing:
            raise ValidationException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"全宗号 {data.fonds_code!r} 已存在",
            )
        fonds = Fonds(
            fonds_code=data.fonds_code,
            name=data.name,
            short_name=data.short_name,
            description=data.description,
            start_year=data.start_year,
            end_year=data.end_year,
            retention_period=data.retention_period,
            status=data.status,
            custodian_id=data.custodian_id,
            tenant_id=tenant_id,
        )
        return await self._repo.create(fonds)

    async def update(self, fonds_id: uuid.UUID, data: FondsUpdate) -> Fonds:
        fonds = await self._repo.get_by_id(fonds_id)
        if not fonds:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="全宗不存在")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            fonds.name = update_data["name"]
        if "short_name" in update_data:
            fonds.short_name = update_data["short_name"]
        if "description" in update_data:
            fonds.description = update_data["description"]
        if "start_year" in update_data:
            fonds.start_year = update_data["start_year"]
        if "end_year" in update_data:
            fonds.end_year = update_data["end_year"]
        if "retention_period" in update_data:
            fonds.retention_period = update_data["retention_period"]
        if "status" in update_data:
            fonds.status = update_data["status"]
        if "custodian_id" in update_data:
            fonds.custodian_id = update_data["custodian_id"]
        return fonds

    async def delete(self, fonds_id: uuid.UUID) -> None:
        fonds = await self._repo.get_by_id(fonds_id)
        if not fonds:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message="全宗不存在")
        await self._repo.delete(fonds)
