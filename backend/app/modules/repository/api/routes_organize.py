"""档案整理 API。

挂载路径： /archive/organize

批量修改    PUT  /records/batch
批量重编档号 POST /renumber/preview | /renumber/apply
挂接数字化成果 POST /attach/preview（文件名预检）| /attach/batch（多文件执行）
单条附件    POST /attachments/upload, DELETE /attachments/{id},
            PATCH /attachments/{id}/primary
归档入库    POST /archive-to-formal
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.schemas.archive import AttachmentRead
from app.modules.repository.schemas.organize import (
    ArchiveToFormalRequest,
    ArchiveToFormalResult,
    AttachBatchResult,
    AttachMatchPreview,
    AttachMatchRequest,
    BatchDeleteRequest,
    BatchUpdateRequest,
    BatchUpdateResult,
    RenumberPreview,
    RenumberRequest,
    RenumberResult,
)
from app.modules.repository.services.attachment_service import AttachmentService
from app.modules.repository.services.organize_service import OrganizeService

router = APIRouter(prefix="/archive/organize", tags=["档案整理"])


# ── 批量修改字段 ──────────────────────────────────────────────────────────────


@router.put("/records/batch", response_model=ResponseModel[BatchUpdateResult])
async def batch_update(
    body: BatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrganizeService(db)
    updated = await svc.batch_update(body, current_user.tenant_id)
    await db.commit()
    return success({"updated": updated})


@router.post("/records/batch-delete", response_model=ResponseModel[dict])
async def batch_delete(
    body: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """批量删除暂存库档案（软删 + 从 ES 移除）。"""
    from app.modules.repository.services.es_sync_service import delete_one

    svc = OrganizeService(db)
    deleted = await svc.batch_delete(body.ids, current_user.tenant_id)
    await db.commit()
    for i in deleted:
        try:
            await delete_one(i)
        except Exception:  # noqa: BLE001
            pass
    return success({"deleted": len(deleted)})


# ── 批量重编档号 ──────────────────────────────────────────────────────────────


@router.post("/renumber/preview", response_model=ResponseModel[RenumberPreview])
async def renumber_preview(
    body: RenumberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrganizeService(db)
    rows = await svc.renumber_preview(body, current_user.tenant_id)
    payload = {
        "total": len(rows),
        "conflicts": sum(1 for r in rows if r.conflict),
        "rows": [r.model_dump(mode="json") for r in rows],
    }
    return success(payload)


@router.post("/renumber/apply", response_model=ResponseModel[RenumberResult])
async def renumber_apply(
    body: RenumberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrganizeService(db)
    renumbered = await svc.renumber_apply(body, current_user.tenant_id)
    await db.commit()
    return success({"renumbered": renumbered})


# ── 挂接数字化成果 ────────────────────────────────────────────────────────────


@router.post("/attach/preview", response_model=ResponseModel[AttachMatchPreview])
async def attach_preview(
    body: AttachMatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AttachmentService(db)
    rows = await svc.match_preview(body.filenames, current_user.tenant_id)
    payload = {
        "total": len(rows),
        "matched": sum(1 for r in rows if r["status"] == "matched"),
        "not_found": sum(1 for r in rows if r["status"] == "not_found"),
        "has_primary": sum(1 for r in rows if r["status"] == "has_primary"),
        "rows": rows,
    }
    return success(AttachMatchPreview.model_validate(payload).model_dump(mode="json"))


@router.post("/attach/batch", response_model=ResponseModel[AttachBatchResult])
async def attach_batch(
    files: list[UploadFile] = File(...),
    overwrite: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AttachmentService(db)
    payload = [(f.filename or "unnamed", await f.read()) for f in files]
    batch, rows = await svc.batch_attach(
        payload, current_user.id, current_user.tenant_id, overwrite=overwrite
    )
    await db.commit()

    # 挂接成功的档案 → 后台投递 OCR 作业（不阻塞本请求）
    from app.modules.ai.services import ocr_job_service

    for r in rows:
        if r.get("status") == "attached" and r.get("archive_id"):
            await ocr_job_service.enqueue(
                db, r["archive_id"], current_user.id, current_user.tenant_id
            )

    result = {
        "batch_no": batch.batch_no,
        "attached": batch.attached,
        "skipped": batch.skipped,
        "not_found": batch.not_found,
        "rows": rows,
    }
    return success(AttachBatchResult.model_validate(result).model_dump(mode="json"))


@router.get("/attach/batches", response_model=ResponseModel[dict])
async def list_attach_batches(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """挂接历史批次列表（留痕报表）。"""
    svc = AttachmentService(db)
    total, batches = await svc.list_batches(
        current_user.tenant_id, skip=skip, limit=min(limit, 100)
    )
    items = [
        {
            "id": str(b.id),
            "batch_no": b.batch_no,
            "total": b.total,
            "attached": b.attached,
            "skipped": b.skipped,
            "not_found": b.not_found,
            "overwrite": b.overwrite,
            "create_time": b.create_time.isoformat() if b.create_time else None,
        }
        for b in batches
    ]
    return success({"total": total, "items": items})


@router.get("/attach/batches/{batch_id}", response_model=ResponseModel[dict])
async def get_attach_batch(
    batch_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """挂接批次详情（逐文件明细）。"""
    svc = AttachmentService(db)
    batch = await svc.get_batch(batch_id, current_user.tenant_id)
    return success(
        {
            "id": str(batch.id),
            "batch_no": batch.batch_no,
            "total": batch.total,
            "attached": batch.attached,
            "skipped": batch.skipped,
            "not_found": batch.not_found,
            "overwrite": batch.overwrite,
            "create_time": batch.create_time.isoformat() if batch.create_time else None,
            "rows": batch.rows or [],
        }
    )


# ── 单条附件管理 ──────────────────────────────────────────────────────────────


@router.post("/attachments/upload", response_model=ResponseModel[AttachmentRead])
async def upload_attachment(
    archive_id: uuid.UUID = Form(...),
    is_primary: bool = Form(True),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AttachmentService(db)
    filename = file.filename or "unnamed.pdf"
    attachment = await svc.upload(
        archive_id,
        filename,
        await file.read(),
        current_user.id,
        current_user.tenant_id,
        is_primary=is_primary,
    )
    await db.commit()

    # 挂接 PDF → 后台投递 OCR 作业（不阻塞本请求）
    if filename.lower().endswith(".pdf"):
        from app.modules.ai.services import ocr_job_service

        await ocr_job_service.enqueue(
            db, archive_id, current_user.id, current_user.tenant_id
        )

    return success(AttachmentRead.model_validate(attachment).model_dump(mode="json"))


@router.delete("/attachments/{attachment_id}", response_model=ResponseModel[None])
async def delete_attachment(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AttachmentService(db)
    await svc.delete(attachment_id, current_user.tenant_id)
    await db.commit()
    return success(None)


@router.patch(
    "/attachments/{attachment_id}/primary", response_model=ResponseModel[AttachmentRead]
)
async def set_primary_attachment(
    attachment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = AttachmentService(db)
    attachment = await svc.set_primary(attachment_id, current_user.tenant_id)
    await db.commit()
    return success(AttachmentRead.model_validate(attachment).model_dump(mode="json"))


# ── 归档入库 ──────────────────────────────────────────────────────────────────


@router.post("/archive-to-formal", response_model=ResponseModel[ArchiveToFormalResult])
async def archive_to_formal(
    body: ArchiveToFormalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = OrganizeService(db)
    rows = await svc.archive_to_formal(
        body.ids, current_user.id, current_user.tenant_id
    )
    await db.commit()
    result = {
        "archived": sum(1 for r in rows if r["status"] == "ok"),
        "failed": sum(1 for r in rows if r["status"] == "failed"),
        "rows": rows,
    }
    return success(ArchiveToFormalResult.model_validate(result).model_dump(mode="json"))
