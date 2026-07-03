"""档案摘要：结合条目著录信息 + 原文 OCR 全文生成简明摘要。
提示词在 Dify「档案摘要」工作流内维护，本服务只组装数据并转发。

状态机（供查看原文页轮询）：
  ready        已生成，返回 summary（按 条目信息+全文 哈希缓存，内容不变即复用）
  ocr_running  正在 OCR 识别原文，请稍后重试
  ocr_started  刚触发 OCR，请稍后重试
  no_source    无挂接原文，无法生成摘要
"""

import hashlib
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions.base import ValidationException
from app.core.config import settings
from app.modules.ai.models.archive_summary import ArchiveSummary
from app.modules.ai.models.ocr_job import OcrJob
from app.modules.ai.services import ocr_job_service
from app.modules.ai.services.dify_service import dify_service
from app.modules.repository.models.archive import (Archive, ArchiveAttachment,
                                                   ArchiveStaging)

MAX_TEXT = 48000


async def summarize(
    db: AsyncSession,
    archive_ref: str,
    user_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> dict:
    archive = await _find_archive(db, archive_ref, tenant_id)
    if archive is None:
        return {"status": "no_source", "message": "档案不存在"}

    full_text = (getattr(archive, "full_text", None) or "").strip()
    if full_text:
        summary = await _get_or_generate(db, archive, full_text, user_id, tenant_id)
        return {"status": "ready", "summary": summary}

    # 无全文：有原文附件才谈得上提取/OCR
    if not await _has_attachment(db, archive.id):
        return {"status": "no_source", "message": "该档案未挂接数字化原文"}

    # 文字型 PDF：直接读文本层即得全文，无需 OCR（OCR 只服务真扫描件）
    layer_text = await _extract_pdf_text_layer(db, archive.id)
    if layer_text:
        archive.full_text = layer_text
        await db.commit()
        try:
            from app.modules.repository.services.es_sync_service import sync_one
            await sync_one(archive)
        except Exception:  # noqa: BLE001
            pass
        summary = await _get_or_generate(db, archive, layer_text, user_id, tenant_id)
        return {"status": "ready", "summary": summary}

    last = await _latest_ocr_job(db, archive.id)
    if last is not None and last.status in ("pending", "running"):
        from datetime import datetime, timedelta, timezone

        age = datetime.now(timezone.utc) - (last.create_time or datetime.now(timezone.utc))
        if age < timedelta(minutes=15):
            return {"status": "ocr_running"}
        # 超时僵尸（如服务重启丢任务）：按失败处理，由用户手动重试
        return {"status": "ocr_failed", "message": "识别任务超时中断，可点击重试"}
    if last is not None and last.status == "failed":
        # 失败不自动重试（否则无限循环刷任务），由用户手动重试
        return {"status": "ocr_failed", "message": last.error or "OCR 识别失败"}

    queued = await ocr_job_service.enqueue(db, archive.id, user_id, tenant_id)
    if queued is None:
        return {"status": "no_source", "message": "该档案没有可识别的 PDF 原文"}
    return {"status": "ocr_started"}


def _meta_block(archive) -> str:
    """条目著录信息块（基础字段 + 门类扩展字段），与原文一起喂给摘要工作流。"""
    parts = [
        f"档号：{archive.DH or '—'}",
        f"题名：{archive.TM or '—'}",
        f"责任者：{archive.RZZ or '—'}",
        f"年度：{archive.ND or '—'}　全宗号：{archive.QZH or '—'}",
        f"密级：{archive.MJ or '—'}　保管期限：{archive.BGQX or '—'}",
        f"文件日期：{archive.WJRQ or '—'}",
    ]
    for k, v in (getattr(archive, "ext_fields", None) or {}).items():
        if v not in (None, ""):
            parts.append(f"{k}：{v}")
    return "\n".join(parts)


async def _get_or_generate(
    db: AsyncSession,
    archive,
    full_text: str,
    user_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> str:
    key = settings.DIFY_SUMMARY_WORKFLOW_KEY
    if not key:
        raise ValidationException(message="未配置摘要工作流（DIFY_SUMMARY_WORKFLOW_KEY）")

    meta = _meta_block(archive)
    # 缓存键 = 条目信息 + 全文（任一变化都重新生成）
    h = hashlib.sha256((meta + "\n" + full_text).encode("utf-8")).hexdigest()
    row = (
        await db.execute(
            select(ArchiveSummary)
            .where(
                ArchiveSummary.archive_id == archive.id,
                ArchiveSummary.is_deleted.is_(False),
            )
            .order_by(ArchiveSummary.create_time.desc())
            .limit(1)
        )
    ).scalars().first()
    if row and row.text_hash == h and row.summary:
        return row.summary

    outputs = await dify_service.run_workflow(
        inputs={
            "meta": meta,
            "full_text": full_text[:MAX_TEXT],
        },
        user_id=str(user_id),
        api_key=key,
        timeout_s=180.0,
    )
    text = outputs.get("text") if isinstance(outputs, dict) else None
    if not text and isinstance(outputs, dict):
        text = next((v for v in outputs.values() if isinstance(v, str)), "")
    text = (text or "").strip()
    if not text:
        raise ValidationException(message="AI 未返回摘要，请稍后重试")

    if row:
        row.is_deleted = True
    db.add(
        ArchiveSummary(
            archive_id=archive.id, text_hash=h, summary=text, tenant_id=tenant_id
        )
    )
    await db.commit()
    return text


async def _find_archive(db: AsyncSession, ref: str, tenant_id: Optional[uuid.UUID]):
    try:
        aid = uuid.UUID(ref)
    except (ValueError, AttributeError, TypeError):
        aid = None
    for model in (ArchiveStaging, Archive):
        cond = (model.id == aid) if aid is not None else (model.DH == ref)
        stmt = select(model).where(cond, model.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(model.tenant_id == tenant_id)
        obj = (await db.execute(stmt)).scalars().first()
        if obj:
            return obj
    return None


async def _extract_pdf_text_layer(db: AsyncSession, archive_id: uuid.UUID) -> str:
    """主附件为文字型 PDF 时直接提取文本层（视同 OCR 结果）。"""
    from app.infra.storage.factory import storage
    from app.modules.ai.services.ocr_service import extract_pdf_text_layer

    att = (
        await db.execute(
            select(ArchiveAttachment)
            .where(
                ArchiveAttachment.archive_id == archive_id,
                ArchiveAttachment.is_deleted.is_(False),
                ArchiveAttachment.file_format == "pdf",
            )
            .order_by(ArchiveAttachment.is_primary.desc())
            .limit(1)
        )
    ).scalars().first()
    if att is None:
        return ""
    try:
        content = storage.get(att.storage_key, att.storage_bucket)
    except Exception:  # noqa: BLE001
        return ""
    return extract_pdf_text_layer(content)


async def _has_attachment(db: AsyncSession, archive_id: uuid.UUID) -> bool:
    row = (
        await db.execute(
            select(ArchiveAttachment.id)
            .where(
                ArchiveAttachment.archive_id == archive_id,
                ArchiveAttachment.is_deleted.is_(False),
            )
            .limit(1)
        )
    ).first()
    return row is not None


async def _latest_ocr_job(db: AsyncSession, archive_id: uuid.UUID):
    return (
        await db.execute(
            select(OcrJob)
            .where(
                OcrJob.archive_id == archive_id,
                OcrJob.is_deleted.is_(False),
            )
            .order_by(OcrJob.create_time.desc())
            .limit(1)
        )
    ).scalars().first()
