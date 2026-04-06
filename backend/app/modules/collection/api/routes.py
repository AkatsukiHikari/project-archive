import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.models.user import User
from app.modules.iam.api.dependencies import get_current_user
from app.core.security.permissions import require_permissions
from app.modules.collection.schemas.sip import SIPCreate, SIPOut, SIPReviewRequest
from app.modules.collection.repositories.sip_repository import SQLAlchemySIPRepository
from app.modules.collection.services.sip_service import SIPService

router = APIRouter()


def get_sip_service(db: AsyncSession = Depends(get_db)) -> SIPService:
    repo = SQLAlchemySIPRepository(db)
    return SIPService(repo)


@router.post(
    "",
    response_model=ResponseModel[SIPOut],
    summary="创建SIP档案收集包",
)
async def create_sip(
    sip_in: SIPCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("collection:create")),
    service: SIPService = Depends(get_sip_service),
) -> dict:
    sip = await service.create_sip(db, current_user, sip_in)
    return success(data=SIPOut.model_validate(sip).model_dump(mode="json"))


@router.get(
    "",
    response_model=ResponseModel[List[SIPOut]],
    summary="获取SIP列表",
)
async def list_sips(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    service: SIPService = Depends(get_sip_service),
) -> dict:
    sips = await service.list_sips(current_user, skip=skip, limit=limit)
    data = [SIPOut.model_validate(s).model_dump(mode="json") for s in sips]
    return success(data=data)


@router.get(
    "/{sip_id}",
    response_model=ResponseModel[SIPOut],
    summary="获取SIP详情",
)
async def get_sip(
    sip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: SIPService = Depends(get_sip_service),
) -> dict:
    sip = await service.get_sip(sip_id, current_user)
    return success(data=SIPOut.model_validate(sip).model_dump(mode="json"))


@router.put(
    "/{sip_id}/submit",
    response_model=ResponseModel[SIPOut],
    summary="提交SIP进入审核",
)
async def submit_sip(
    sip_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: SIPService = Depends(get_sip_service),
) -> dict:
    sip = await service.submit_sip(sip_id, current_user)
    return success(data=SIPOut.model_validate(sip).model_dump(mode="json"))


@router.put(
    "/{sip_id}/review",
    response_model=ResponseModel[SIPOut],
    summary="审核SIP（接受或拒绝）",
)
async def review_sip(
    sip_id: uuid.UUID,
    body: SIPReviewRequest,
    current_user: User = Depends(require_permissions("collection:review")),
    service: SIPService = Depends(get_sip_service),
) -> dict:
    sip = await service.review_sip(sip_id, current_user, accept=body.accept, notes=body.notes)
    return success(data=SIPOut.model_validate(sip).model_dump(mode="json"))
