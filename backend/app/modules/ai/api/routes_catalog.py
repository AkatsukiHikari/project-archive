"""智能著录路由（挂在 /ai 前缀下）。

- GET  /ai/catalog/candidates          有原文待著录/补正的候选列表
- POST /ai/catalog/suggest/{id}        对已有档案 AI 出逐字段建议
- POST /ai/catalog/apply/{id}          用户确认后回写采用的字段
- POST /ai/catalog/extract             自动录入：传 PDF/OFD + 门类 → OCR + 抽取
- POST /ai/catalog/ingest              自动录入：确认后新增入暂存库
- GET  /ai/catalog/threshold           当前相似度/置信度阈值
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.ai.services import catalog_extract_service as extract
from app.modules.ai.services import catalog_service
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.schemas.archive import ArchiveCreate, ArchiveRead
from app.modules.repository.services.archive_service import ArchiveService

router = APIRouter()


class SuggestBody(BaseModel):
    doc_source: str = "staging"  # staging | formal


class ApplyBody(BaseModel):
    doc_source: str = "staging"
    adopted: dict[str, str]


@router.get("/catalog/candidates", response_model=ResponseModel[dict])
async def candidates(
    doc_source: str = "all",
    only_issues: bool = False,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await catalog_service.list_candidates(
        db, current_user.tenant_id, doc_source, only_issues, skip, limit
    )
    return success(data)


@router.get("/catalog/threshold", response_model=ResponseModel[dict])
async def threshold(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return success({"threshold": await catalog_service.get_threshold(db)})


@router.post("/catalog/suggest/{archive_id}", response_model=ResponseModel[dict])
async def suggest(
    archive_id: uuid.UUID,
    body: SuggestBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await catalog_service.suggest(
        db, archive_id, body.doc_source, current_user.id, current_user.tenant_id
    )
    return success(data)


@router.post("/catalog/apply/{archive_id}", response_model=ResponseModel[dict])
async def apply(
    archive_id: uuid.UUID,
    body: ApplyBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = await catalog_service.apply(
        db, archive_id, body.doc_source, body.adopted,
        current_user.id, current_user.tenant_id,
    )
    return success(data)


@router.post("/catalog/extract", response_model=ResponseModel[dict])
async def extract_for_ingest(
    file: UploadFile = File(...),
    category_id: uuid.UUID = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """自动录入：上传数字化成果 → OCR 取全文 → 按门类 schema 抽字段 → 出建议。"""
    content = await file.read()
    full_text = await extract.ocr_file_bytes(
        content, file.filename or "upload.pdf", str(current_user.id)
    )
    schema = await catalog_service.category_schema(db, category_id)
    if not (full_text or "").strip():
        return success({"ok": False, "reason": "OCR 未识别出原文内容"})
    extracted = await extract.extract_from_text(
        full_text, _to_raw(schema), {}, str(current_user.id)
    )
    th = await catalog_service.get_threshold(db)
    suggestions = catalog_service.build_suggestions(schema, {}, extracted, th)
    suggested_dh = await catalog_service.suggest_next_dh(
        db, category_id, current_user.tenant_id
    )
    return success(
        {
            "ok": True,
            "threshold": th,
            "chars": len(full_text),
            "full_text": full_text,
            "suggested_dh": suggested_dh,
            "suggestions": suggestions,
        }
    )


@router.post("/catalog/ingest", response_model=ResponseModel[ArchiveRead])
async def ingest(
    file: UploadFile = File(...),
    payload: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """自动录入：确认后新增入暂存库，并把上传的 PDF 挂接为该档案原文 + 存全文。

    payload 是 ArchiveCreate 字段 + full_text 的 JSON 串。**档号必填**。
    """
    import json

    from app.common.exceptions.base import ValidationException
    from app.modules.repository.services.attachment_service import AttachmentService

    raw = json.loads(payload)
    dh = (raw.get("DH") or "").strip()
    if not dh:
        raise ValidationException(message="档号必填，没有档号的档案不可入库")
    raw["DH"] = dh
    full_text = (raw.pop("full_text", "") or "").strip()

    data = ArchiveCreate(**raw)
    svc = ArchiveService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.flush()

    # 把上传的 PDF/OFD 挂接为该档案的原文（数字化成果）
    content = await file.read()
    att_svc = AttachmentService(db)
    await att_svc.upload(
        item.id, file.filename or f"{dh}.pdf", content,
        current_user.id, current_user.tenant_id, is_primary=True,
    )
    # 原文已识别的全文一并存上（链：条目→原文→OCR 全文）
    if full_text:
        item.full_text = full_text

    await catalog_service.log_ingest(
        db, item, {"source": "auto_ingest", "DH": dh}, current_user.id, current_user.tenant_id
    )
    await db.commit()
    try:
        from app.modules.repository.services.es_sync_service import sync_one
        await sync_one(item)
    except Exception:  # noqa: BLE001
        pass
    return success(ArchiveRead.model_validate(item))


def _to_raw(compact: list[dict]) -> list[dict]:
    return [
        {**c, "options": [{"value": o, "label": o} for o in (c.get("options") or [])]}
        for c in compact
    ]
