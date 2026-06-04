"""
AI Patch 审核队列 API（P1 占位 + P3 实装）。

P1 阶段只暴露：
- GET /v1/ai/patches             — 列表（按租户隔离）
- GET /v1/ai/patches/{patch_id}  — 详情

写入（approve / reject）端点保留接口形态但抛 ``6003`` 提示 "P3 尚未实装"，
避免演示时点击触发未知 500。
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import BaseAPIException
from app.common.response import ResponseModel
from app.infra.db.session import get_db
from app.modules.ai._tenant_helper import ensure_tenant_id
from app.modules.ai_patch.models.ai_patch import AIPatch
from app.modules.ai_patch.schemas.patch import (
    PatchDetail,
    PatchListItem,
    PatchListResponse,
    PatchReviewAction,
)
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User

router = APIRouter()


@router.get(
    "",
    summary="AI 写操作审核队列",
    response_model=ResponseModel[PatchListResponse],
)
async def list_patches(
    status: Optional[str] = Query(default=None, description="状态过滤：pending/approved/rejected/applied/failed"),
    scenario_code: Optional[str] = Query(default=None, description="按场景过滤"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[PatchListResponse]:
    base = select(AIPatch).where(
        AIPatch.tenant_id == await ensure_tenant_id(db, current_user),
        AIPatch.is_deleted.is_(False),
    )
    if status:
        base = base.where(AIPatch.status == status)
    if scenario_code:
        base = base.where(AIPatch.scenario_code == scenario_code)

    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()

    stmt = base.order_by(AIPatch.create_time.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).scalars().all()
    items = [
        PatchListItem(
            id=row.id,
            scenario_code=row.scenario_code,
            target_type=row.target_type,
            target_id=row.target_id,
            operation=row.operation,
            status=row.status,  # type: ignore[arg-type]
            gate=row.gate,  # type: ignore[arg-type]
            confidence=row.confidence,
            workflow_version=row.workflow_version,
            reviewer_id=row.reviewer_id,
            create_time=row.create_time,
            update_time=row.update_time,
        )
        for row in rows
    ]
    return ResponseModel(data=PatchListResponse(total=total, items=items))


@router.get(
    "/{patch_id}",
    summary="AI Patch 详情",
    response_model=ResponseModel[PatchDetail],
)
async def get_patch(
    patch_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[PatchDetail]:
    stmt = select(AIPatch).where(
        AIPatch.id == patch_id,
        AIPatch.tenant_id == await ensure_tenant_id(db, current_user),
        AIPatch.is_deleted.is_(False),
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise BaseAPIException(
            code=ErrorCode.AI_PATCH_STATE_CONFLICT,
            message="Patch 不存在或不属于当前租户",
            status_code=404,
        )
    detail = PatchDetail(
        id=row.id,
        scenario_code=row.scenario_code,
        target_type=row.target_type,
        target_id=row.target_id,
        operation=row.operation,
        status=row.status,  # type: ignore[arg-type]
        gate=row.gate,  # type: ignore[arg-type]
        confidence=row.confidence,
        workflow_version=row.workflow_version,
        reviewer_id=row.reviewer_id,
        create_time=row.create_time,
        update_time=row.update_time,
        payload=row.payload or {},
        citations=row.citations or [],
        reviewer_note=row.reviewer_note,
        apply_error=row.apply_error,
    )
    return ResponseModel(data=detail)


@router.post(
    "/{patch_id}/review",
    summary="审核 AI Patch（P3 实装）",
    response_model=ResponseModel[None],
)
async def review_patch(
    patch_id: uuid.UUID,
    body: PatchReviewAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[None]:
    # P1 占位：接口契约固定，实装等 P3。提前抛错让 UI 知道这是预留入口。
    raise BaseAPIException(
        code=ErrorCode.AI_PATCH_STATE_CONFLICT,
        message="AI Patch 审核能力将在 P3 上线",
        status_code=409,
    )
