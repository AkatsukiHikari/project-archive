"""
AI 知识库管理 API

- GET  /v1/ai/kb/status   各 KB（meta/rules/ocr）的状态快照
- POST /v1/ai/kb/rebuild  全量重建指定 KB（同步执行，P2 起转 Celery 异步）

设计稿 §4.2/⑧ "知识库交互管理"：P1 读侧暴露 + 重建触发；P3 写入走 ai_patch。
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import BaseAPIException
from app.common.response import ResponseModel
from app.infra.db.session import get_db
from app.modules.ai._tenant_helper import ensure_tenant_id
from app.modules.ai.services.kb_sync_service import KBSyncService
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User


router = APIRouter()


class KBStatusItem(BaseModel):
    kb_type: str
    db_count: int
    es_count: int | None
    synced: bool
    last_synced_at: str | None
    note: str | None = None


class KBStatusResponse(BaseModel):
    items: list[KBStatusItem]


@router.get(
    "/status",
    summary="知识库状态",
    response_model=ResponseModel[KBStatusResponse],
)
async def status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[KBStatusResponse]:
    tenant_id = await ensure_tenant_id(db, current_user)
    svc = KBSyncService(db)
    stats = await svc.get_stats(tenant_id)
    items = [
        KBStatusItem(
            kb_type=s.kb_type,
            db_count=s.db_count,
            es_count=s.es_count,
            synced=s.synced,
            last_synced_at=s.last_synced_at,
            note=s.note,
        )
        for s in stats
    ]
    return ResponseModel(data=KBStatusResponse(items=items))


class RebuildRequest(BaseModel):
    kb_type: Literal["meta"] = Field(default="meta", description="P1 仅支持 meta")
    batch_size: int = Field(default=200, ge=10, le=2000)


class RebuildResponse(BaseModel):
    kb_type: str
    scanned: int
    synced: int
    failed: int
    duration_ms: int


@router.post(
    "/rebuild",
    summary="重建知识库",
    description="**注意**：P1 同步执行；超过 1 万条建议先停掉，P2 转 Celery 异步任务。",
    response_model=ResponseModel[RebuildResponse],
)
async def rebuild(
    body: RebuildRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[RebuildResponse]:
    if body.kb_type != "meta":
        raise BaseAPIException(
            code=ErrorCode.AI_CAPABILITY_DISABLED,
            message=f"KB 类型 '{body.kb_type}' 暂未实装",
            status_code=400,
        )
    tenant_id = await ensure_tenant_id(db, current_user)
    svc = KBSyncService(db)
    res = await svc.rebuild_meta(tenant_id, batch_size=body.batch_size)
    return ResponseModel(
        data=RebuildResponse(
            kb_type=res.kb_type,
            scanned=res.scanned,
            synced=res.synced,
            failed=res.failed,
            duration_ms=res.duration_ms,
        )
    )
