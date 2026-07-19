"""利用服务中心 + 自助查询机（kiosk）API。挂载前缀 /utilization。

服务中心（工作人员）：
- GET  /center/summary                  今日概览（接待/办理中/待审批/办结）
- POST /applications/{id}/approve       批准自助机申请（→办理中，可阅览）
- POST /applications/{id}/reject        拒绝自助机申请
- POST /applications/{id}/transfer      转办（改经办人，审计留痕）

自助查询机（设备账号登录后民众自助操作）：
- POST /kiosk/apply                     提交「申请查看」（返回申请码）
- GET  /kiosk/status                    凭申请码查进度
- GET  /kiosk/attachments               批准后取原文（校验码+范围）
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.utilization.schemas.application import ApplicationOut, ItemIn
from app.modules.utilization.services import kiosk_service

router = APIRouter(prefix="/utilization", tags=["利用服务中心"])


# ── 服务中心 ──────────────────────────────────────────────────────────────────
@router.get("/center/summary", response_model=ResponseModel[dict])
async def center_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return success(await kiosk_service.center_summary(db, current_user.tenant_id))


@router.post("/applications/{app_id}/approve", response_model=ResponseModel[ApplicationOut])
async def approve_application(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = await kiosk_service.approve(db, app_id, current_user)
    return success(ApplicationOut.model_validate(app).model_dump(mode="json"))


class RejectBody(BaseModel):
    reason: str = Field(default="", max_length=500)


@router.post("/applications/{app_id}/reject", response_model=ResponseModel[ApplicationOut])
async def reject_application(
    app_id: uuid.UUID,
    body: RejectBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = await kiosk_service.reject(db, app_id, body.reason, current_user)
    return success(ApplicationOut.model_validate(app).model_dump(mode="json"))


class TransferBody(BaseModel):
    handler_id: uuid.UUID


@router.post("/applications/{app_id}/transfer", response_model=ResponseModel[ApplicationOut])
async def transfer_application(
    app_id: uuid.UUID,
    body: TransferBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = await kiosk_service.transfer(db, app_id, body.handler_id, current_user)
    return success(ApplicationOut.model_validate(app).model_dump(mode="json"))


# ── 自助查询机 ────────────────────────────────────────────────────────────────
class KioskApplyBody(BaseModel):
    applicant_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=5, max_length=32)
    id_card_no: Optional[str] = Field(default=None, max_length=32)
    purpose: Optional[str] = Field(default=None, max_length=500)
    items: list[ItemIn] = Field(..., min_length=1)


@router.post("/kiosk/apply", response_model=ResponseModel[dict])
async def kiosk_apply(
    body: KioskApplyBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await kiosk_service.kiosk_create(
        db,
        applicant_name=body.applicant_name,
        phone=body.phone,
        id_card_no=body.id_card_no,
        purpose=body.purpose,
        items=body.items,
        device_user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )
    return success(data)


@router.get("/kiosk/status", response_model=ResponseModel[dict])
async def kiosk_status(
    code: str = Query(..., min_length=4, max_length=8),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return success(await kiosk_service.kiosk_status(db, code, current_user.tenant_id))


@router.get("/kiosk/attachments", response_model=ResponseModel[list[dict]])
async def kiosk_attachments(
    code: str = Query(..., min_length=4, max_length=8),
    archive_id: uuid.UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await kiosk_service.kiosk_attachments(db, code, archive_id, current_user.tenant_id)
    return success(data)
