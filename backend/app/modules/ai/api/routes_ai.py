"""AI 路由（重构版）。挂载前缀 /ai。

- POST /ai/chat        档案问答（ES 检索 + DeepSeek 合成），SSE 流式
- POST /ai/interpret   解读单份档案（喂完整信息），SSE 流式

OCR / 知识库同步分别在 routes_ocr / routes_kb。
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.ai.services import dify_kb, kb_sync, ocr_job_service
from app.modules.ai.services.qa_service import QaService
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.models.archive import Archive, ArchiveStaging

router = APIRouter()

_SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


class InterpretRequest(BaseModel):
    archive_id: uuid.UUID


@router.post("/chat")
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = QaService(db)
    return StreamingResponse(
        svc.chat(
            body.query, current_user.id, current_user.tenant_id, body.conversation_id
        ),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


@router.post("/interpret")
async def interpret(
    body: InterpretRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = QaService(db)
    return StreamingResponse(
        svc.interpret(body.archive_id, current_user.id, current_user.tenant_id),
        media_type="text/event-stream",
        headers=_SSE_HEADERS,
    )


# ── OCR ───────────────────────────────────────────────────────────────────────


@router.post("/ocr/{archive_id}", response_model=ResponseModel[dict])
async def ocr_archive(
    archive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """投递 OCR 后台作业（MinerU 识别→存全文→同步），立即返回作业号，不阻塞。"""
    job = await ocr_job_service.enqueue(
        db, archive_id, current_user.id, current_user.tenant_id
    )
    if job is None:
        return success({"ok": False, "reason": "该档案没有可识别的 PDF 原文"})
    return success({"ok": True, "job_id": str(job.id)})


@router.post("/ocr/batch", response_model=ResponseModel[dict])
async def ocr_batch(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """给所有"有 PDF 但还没 OCR"的档案批量投递作业。"""
    n = await ocr_job_service.batch_enqueue(db, current_user.id, current_user.tenant_id)
    return success({"queued": n})


@router.get("/ocr/text/{archive_ref}", response_model=ResponseModel[dict])
async def ocr_text(
    archive_ref: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取档案存下的 OCR 全文（供查看原文界面展示）。

    archive_ref 接受 UUID 或 档号(DH)；暂存库 + 正式库都查。
    """
    try:
        aid = uuid.UUID(archive_ref)
    except (ValueError, AttributeError, TypeError):
        aid = None

    text = ""
    for model in (ArchiveStaging, Archive):
        cond = (model.id == aid) if aid is not None else (model.DH == archive_ref)
        stmt = select(model).where(cond, model.is_deleted.is_(False))
        if current_user.tenant_id:
            stmt = stmt.where(model.tenant_id == current_user.tenant_id)
        a = (await db.execute(stmt)).scalars().first()
        if a is not None:
            text = a.full_text or ""
            break
    return success({"full_text": text, "chars": len(text)})


@router.get("/ocr/jobs", response_model=ResponseModel[dict])
async def ocr_jobs(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total, jobs = await ocr_job_service.list_jobs(
        db, current_user.tenant_id, status=status, skip=skip, limit=limit
    )
    return success(
        {
            "total": total,
            "items": [
                {
                    "id": str(j.id),
                    "archive_id": str(j.archive_id),
                    "archive_dh": j.archive_dh,
                    "archive_tm": j.archive_tm,
                    "status": j.status,
                    "chars": j.chars,
                    "error": j.error,
                    "create_time": j.create_time.isoformat() if j.create_time else None,
                    "finished_at": j.finished_at.isoformat() if j.finished_at else None,
                }
                for j in jobs
            ],
        }
    )


# ── 知识库 ────────────────────────────────────────────────────────────────────


@router.post("/kb/sync/{archive_id}", response_model=ResponseModel[dict])
async def kb_sync_one(
    archive_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Archive).where(
        Archive.id == archive_id, Archive.is_deleted.is_(False)
    )
    if current_user.tenant_id:
        stmt = stmt.where(Archive.tenant_id == current_user.tenant_id)
    archive = (await db.execute(stmt)).scalars().first()
    if archive is None:
        return success({"ok": False, "reason": "档案不存在"})
    doc_id = await kb_sync.sync_archive(db, archive)
    await db.commit()
    return success({"ok": bool(doc_id), "doc_id": doc_id})


@router.post("/kb/rebuild", response_model=ResponseModel[dict])
async def kb_rebuild(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = await kb_sync.rebuild(db, current_user.tenant_id)
    return success({"synced": n})


@router.get("/kb/status", response_model=ResponseModel[dict])
async def kb_status(current_user: User = Depends(get_current_user)):
    return success(await dify_kb.stats())
