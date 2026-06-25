"""OCR 作业编排：建作业 + 进程内异步后台执行 + 列表查询。

执行用进程内 asyncio 后台任务（不卡请求）。本部署是「原生 API + 容器化 worker」，
worker 容器到不了 localhost 的 Dify，所以默认在 API 进程里跑。
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models.ocr_job import OcrJob
from app.modules.repository.models.archive import (
    Archive,
    ArchiveAttachment,
    ArchiveStaging,
)

logger = logging.getLogger(__name__)


async def _archive_snapshot(db: AsyncSession, archive_id: uuid.UUID):
    for model in (Archive, ArchiveStaging):
        a = (
            await db.execute(
                select(model).where(model.id == archive_id, model.is_deleted.is_(False))
            )
        ).scalar_one_or_none()
        if a:
            return a
    return None


async def _primary_pdf_id(
    db: AsyncSession, archive_id: uuid.UUID
) -> Optional[uuid.UUID]:
    rows = (
        (
            await db.execute(
                select(ArchiveAttachment)
                .where(
                    ArchiveAttachment.archive_id == archive_id,
                    ArchiveAttachment.is_deleted.is_(False),
                )
                .order_by(ArchiveAttachment.is_primary.desc())
            )
        )
        .scalars()
        .all()
    )
    for a in rows:
        if (a.original_name or "").lower().endswith(".pdf") or (
            a.file_format or ""
        ).lower() == "pdf":
            return a.id
    return None


async def enqueue(
    db: AsyncSession,
    archive_id: uuid.UUID,
    user_id: Optional[uuid.UUID],
    tenant_id: Optional[uuid.UUID],
) -> Optional[OcrJob]:
    """建一条 OCR 作业并投递队列。无 PDF 则不建，返回 None。"""
    a = await _archive_snapshot(db, archive_id)
    if a is None:
        return None
    att_id = await _primary_pdf_id(db, archive_id)
    if att_id is None:
        return None
    job = OcrJob(
        archive_id=archive_id,
        attachment_id=att_id,
        archive_dh=a.DH,
        archive_tm=a.TM,
        status="pending",
        tenant_id=tenant_id,
        create_by=user_id,
    )
    db.add(job)
    await db.flush()
    job_id = str(job.id)
    await db.commit()

    # 进程内后台执行（不阻塞当前请求），用独立 session
    asyncio.create_task(run_job(job_id))
    return job


async def run_job(job_id: str) -> dict:
    """后台执行一条 OCR 作业（独立 session）。供 asyncio 后台任务/Celery 调用。"""
    from app.infra.db.session import AsyncSessionLocal
    from app.modules.ai.services.ocr_service import OcrService

    async with AsyncSessionLocal() as db:
        job = (
            await db.execute(select(OcrJob).where(OcrJob.id == uuid.UUID(job_id)))
        ).scalar_one_or_none()
        if job is None:
            return {"ok": False, "reason": "job not found"}
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        await db.commit()
        try:
            result = await OcrService(db).ocr_archive(
                job.archive_id, job.create_by or uuid.uuid4(), job.tenant_id
            )
            job.status = "succeeded" if result.get("ok") else "failed"
            job.chars = result.get("chars")
            if not result.get("ok"):
                job.error = result.get("reason")
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return result
        except Exception as exc:  # noqa: BLE001
            logger.exception("OCR 作业失败 job=%s", job_id)
            job.status = "failed"
            job.error = str(exc)[:500]
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            return {"ok": False, "reason": str(exc)}


async def list_jobs(
    db: AsyncSession,
    tenant_id: Optional[uuid.UUID],
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[int, list[OcrJob]]:
    stmt = select(OcrJob).where(OcrJob.is_deleted.is_(False))
    if tenant_id:
        stmt = stmt.where(OcrJob.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(OcrJob.status == status)
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(OcrJob.create_time.desc()).offset(skip).limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return total, list(rows)


async def batch_enqueue(
    db: AsyncSession, user_id: Optional[uuid.UUID], tenant_id: Optional[uuid.UUID]
) -> int:
    """给"有 PDF 附件但还没 full_text"的正式档案批量建作业。"""
    stmt = (
        select(Archive.id)
        .join(ArchiveAttachment, ArchiveAttachment.archive_id == Archive.id)
        .where(
            Archive.is_deleted.is_(False),
            Archive.full_text.is_(None),
            ArchiveAttachment.is_deleted.is_(False),
            ArchiveAttachment.original_name.ilike("%.pdf"),
        )
        .distinct()
    )
    if tenant_id:
        stmt = stmt.where(Archive.tenant_id == tenant_id)
    ids = (await db.execute(stmt)).scalars().all()
    n = 0
    for aid in ids:
        if await enqueue(db, aid, user_id, tenant_id):
            n += 1
    return n
