import uuid
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions.base import NotFoundException, AuthorizationException
from app.common.error_code import ErrorCode
from app.modules.iam.models.user import User
from app.modules.collection.models.sip import SIPRecord
from app.modules.collection.repositories.sip_repository import SQLAlchemySIPRepository
from app.modules.collection.schemas.sip import SIPCreate


class SIPService:
    def __init__(self, repo: SQLAlchemySIPRepository):
        self.repo = repo

    async def create_sip(
        self,
        db: AsyncSession,
        current_user: User,
        sip_in: SIPCreate,
    ) -> SIPRecord:
        sip = SIPRecord(
            title=sip_in.title,
            description=sip_in.description,
            submitter_id=current_user.id,
            tenant_id=sip_in.tenant_id,
            status="draft",
            metadata_json=sip_in.metadata_json,
            file_count=0,
            create_by=current_user.id,
        )
        return await self.repo.create(sip)

    async def get_sip(
        self,
        sip_id: uuid.UUID,
        current_user: User,
    ) -> SIPRecord:
        sip = await self.repo.get_by_id(sip_id)
        if not sip:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_NOT_FOUND,
                message="SIP记录不存在",
            )
        # Access allowed if submitter or same tenant
        is_submitter = sip.submitter_id == current_user.id
        same_tenant = (
            sip.tenant_id is not None
            and hasattr(current_user, "tenant_id")
            and sip.tenant_id == current_user.tenant_id
        )
        if not (is_submitter or same_tenant or current_user.is_superadmin):
            raise AuthorizationException(message="无权访问该SIP记录")
        return sip

    async def list_sips(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 20,
    ) -> List[SIPRecord]:
        return await self.repo.list_by_submitter(current_user.id, skip=skip, limit=limit)

    async def submit_sip(
        self,
        sip_id: uuid.UUID,
        current_user: User,
    ) -> SIPRecord:
        sip = await self.get_sip(sip_id, current_user)
        if sip.status != "draft":
            raise AuthorizationException(message="只有草稿状态的SIP可以提交审核")
        return await self.repo.update_status(sip, "submitted")

    async def review_sip(
        self,
        sip_id: uuid.UUID,
        current_user: User,
        accept: bool,
        notes: str | None = None,
    ) -> SIPRecord:
        sip = await self.repo.get_by_id(sip_id)
        if not sip:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_NOT_FOUND,
                message="SIP记录不存在",
            )
        new_status = "accepted" if accept else "rejected"
        return await self.repo.update_status(sip, new_status, notes=notes)
