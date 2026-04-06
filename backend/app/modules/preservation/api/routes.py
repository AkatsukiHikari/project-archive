import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success, fail
from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException
from app.infra.db.session import get_db
from app.modules.iam.models.user import User
from app.modules.iam.api.dependencies import get_current_user
from app.core.security.permissions import require_permissions
from app.modules.preservation.schemas.detection import DetectionRequest, DetectionRecordOut
from app.modules.preservation.repositories.detection_repository import SQLAlchemyDetectionRepository
from app.modules.preservation.api.dependencies import get_detection_service
from app.modules.preservation.services.preservation_service import PreservationService

router = APIRouter()


@router.post(
    "",
    response_model=ResponseModel[DetectionRecordOut],
    summary="执行四性检测并记录结果",
)
async def run_detection(
    body: DetectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("preservation:detect")),
    service: PreservationService = Depends(get_detection_service),
) -> dict:
    record = await service.store_detection(db, body, current_user.id)
    return success(data=DetectionRecordOut.from_orm_model(record).model_dump(mode="json"))


@router.get(
    "/{record_id}",
    response_model=ResponseModel[DetectionRecordOut],
    summary="获取检测记录详情",
)
async def get_detection(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    repo = SQLAlchemyDetectionRepository(db)
    record = await repo.get_by_id(record_id)
    if not record:
        raise NotFoundException(message="检测记录不存在")
    return success(data=DetectionRecordOut.from_orm_model(record).model_dump(mode="json"))


@router.get(
    "",
    response_model=ResponseModel[List[DetectionRecordOut]],
    summary="获取检测记录列表",
)
async def list_detections(
    archive_id: Optional[uuid.UUID] = Query(None, description="按档案ID筛选"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    repo = SQLAlchemyDetectionRepository(db)
    if archive_id is not None:
        records = await repo.list_by_archive(archive_id, skip=skip, limit=limit)
    else:
        records = await repo.list_all(skip=skip, limit=limit)
    data = [DetectionRecordOut.from_orm_model(r).model_dump(mode="json") for r in records]
    return success(data=data)
