from fastapi import APIRouter, Depends, Query
from typing import List, Optional
from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import success, ResponseModel
from app.infra.db.session import get_db
from app.modules.iam.models.user import User
from app.modules.iam.api.dependencies import get_current_user
from app.modules.schedule.schemas import ScheduleEventResponse, ScheduleEventCreate, ScheduleEventUpdate
from app.modules.schedule.repositories import SQLAlchemyScheduleRepository
from app.modules.schedule.services import ScheduleService

router = APIRouter()

def get_schedule_service(db: AsyncSession = Depends(get_db)) -> ScheduleService:
    repo = SQLAlchemyScheduleRepository(db)
    return ScheduleService(repo)

@router.get(
    "",
    response_model=ResponseModel[List[ScheduleEventResponse]],
    summary="获取日程列表"
)
async def list_schedules(
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service)
):
    events = await service.list_user_schedules(current_user.id, start_time, end_time)
    data = [ScheduleEventResponse.model_validate(e).model_dump(mode="json") for e in events]
    return success(data=data)

@router.post(
    "",
    response_model=ResponseModel[ScheduleEventResponse],
    summary="创建日程"
)
async def create_schedule(
    event_in: ScheduleEventCreate,
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service)
):
    event = await service.create_schedule(current_user.id, event_in)
    return success(data=ScheduleEventResponse.model_validate(event).model_dump(mode="json"))

@router.get(
    "/{event_id}",
    response_model=ResponseModel[ScheduleEventResponse],
    summary="获取指定日程详情"
)
async def get_schedule(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service)
):
    event = await service.get_schedule(event_id, current_user.id)
    return success(data=ScheduleEventResponse.model_validate(event).model_dump(mode="json"))

@router.put(
    "/{event_id}",
    response_model=ResponseModel[ScheduleEventResponse],
    summary="修改日程"
)
async def update_schedule(
    event_id: uuid.UUID,
    event_in: ScheduleEventUpdate,
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service)
):
    event = await service.update_schedule(event_id, current_user.id, event_in)
    return success(data=ScheduleEventResponse.model_validate(event).model_dump(mode="json"))

@router.delete(
    "/{event_id}",
    response_model=ResponseModel[None],
    summary="删除日程"
)
async def delete_schedule(
    event_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    service: ScheduleService = Depends(get_schedule_service)
):
    await service.delete_schedule(event_id, current_user.id)
    return success(message="删除成功")
