"""智能校对路由（挂在 /ai 前缀下）。

- POST /ai/proofread/preview            按范围预检：可校对件数/需先OCR件数
- POST /ai/proofread/start              发起批量校对（后台执行）
- GET  /ai/proofread/batches            批次列表（历史批次面板）
- GET  /ai/proofread/batches/{id}       批次详情（进度轮询）
- POST /ai/proofread/batches/{id}/cancel 取消运行中批次
- POST /ai/proofread/records            范围内档案 + 最新校对结论（表格）
- POST /ai/proofread/resolve/{id}       整改写库后标记「已整改」
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.ai.services import proofread_service
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.schemas.archive import ArchiveListQuery

router = APIRouter()

DOC_SOURCE_PATTERN = "^(all|staging|formal)$"


class ScopeBody(BaseModel):
    """检索范围（目录导航 + 字段检索），与档案列表同一套过滤条件。"""

    doc_source: str = Field(default="all", pattern=DOC_SOURCE_PATTERN)
    query: ArchiveListQuery = Field(default_factory=ArchiveListQuery)


class StartBody(ScopeBody):
    scope_label: Optional[str] = Field(default=None, max_length=512)
    force: bool = Field(default=False, description="强制重新校对（无视原文抽取缓存）")


class RecordsBody(ScopeBody):
    verdict: Optional[str] = Field(
        default=None,
        pattern="^(none|no_pdf|consistent|flagged|resolved|no_text|failed|pending)$",
        description="按校对状态过滤",
    )


@router.post("/proofread/preview", response_model=ResponseModel[dict])
async def preview(
    body: ScopeBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await proofread_service.preview(
        db, body.query, body.doc_source, current_user.tenant_id
    )
    return success(data)


@router.post("/proofread/start", response_model=ResponseModel[dict])
async def start(
    body: StartBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await proofread_service.start(
        db,
        body.query,
        body.doc_source,
        body.scope_label,
        body.force,
        current_user.id,
        current_user.tenant_id,
    )
    return success(data)


@router.get("/proofread/batches", response_model=ResponseModel[dict])
async def batches(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await proofread_service.list_batches(db, current_user.tenant_id, skip, limit)
    return success(data)


@router.get("/proofread/batches/{batch_id}", response_model=ResponseModel[dict])
async def batch_detail(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await proofread_service.get_batch(db, batch_id, current_user.tenant_id)
    if data is None:
        return success({"ok": False, "reason": "批次不存在"})
    return success(data)


@router.post("/proofread/batches/{batch_id}/cancel", response_model=ResponseModel[dict])
async def cancel(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await proofread_service.cancel(db, batch_id, current_user.tenant_id)
    return success(data)


@router.post("/proofread/records", response_model=ResponseModel[dict])
async def records(
    body: RecordsBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await proofread_service.list_records(
        db, body.query, body.doc_source, current_user.tenant_id, body.verdict
    )
    return success(data)


@router.post("/proofread/resolve/{archive_id}", response_model=ResponseModel[dict])
async def resolve(
    archive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await proofread_service.resolve(db, archive_id, current_user.tenant_id)
    return success(data)
