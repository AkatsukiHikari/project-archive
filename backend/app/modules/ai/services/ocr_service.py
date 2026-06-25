"""OCR：挂接 PDF 时调 Dify OCR 工作流（MinerU）识别 → 存 full_text → 同步 ES + 知识库。"""

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.core.config import settings
from app.infra.storage.factory import storage
from app.modules.ai.services import kb_sync
from app.modules.ai.services.dify_service import dify_service
from app.modules.repository.models.archive import (Archive, ArchiveAttachment,
                                                   ArchiveStaging)
from app.modules.repository.services import es_sync_service

logger = logging.getLogger(__name__)


def _first_text(outputs: dict) -> str:
    if not outputs:
        return ""
    if isinstance(outputs.get("text"), str):
        return outputs["text"]
    for v in outputs.values():
        if isinstance(v, str) and v.strip():
            return v
    return ""


class OcrService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ocr_archive(
        self, archive_id: uuid.UUID, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> dict:
        key = settings.DIFY_OCR_WORKFLOW_KEY
        if not key:
            raise ValidationException(
                message="未配置 OCR 工作流（DIFY_OCR_WORKFLOW_KEY）"
            )

        archive = await self._load_archive(archive_id, tenant_id)
        if archive is None:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_NOT_FOUND, message="档案不存在"
            )

        att = await self._primary_pdf(archive_id)
        if att is None:
            return {"ok": False, "reason": "该档案没有可识别的 PDF 原文"}

        content = storage.get(att.storage_key, att.storage_bucket)
        file_id = await dify_service.upload_file(
            content, att.original_name, str(user_id), key
        )
        outputs = await dify_service.run_workflow(
            {
                "file": {
                    "transfer_method": "local_file",
                    "upload_file_id": file_id,
                    "type": "document",
                }
            },
            str(user_id),
            key,
        )
        text = _first_text(outputs).strip()
        if not text:
            return {"ok": False, "reason": "OCR 未返回文本"}

        archive.full_text = text
        await self.db.flush()
        await es_sync_service.sync_one(archive)
        if isinstance(archive, Archive):
            await kb_sync.sync_archive(self.db, archive)
        await self.db.commit()
        return {"ok": True, "chars": len(text)}

    async def _load_archive(
        self, archive_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ):
        for model in (Archive, ArchiveStaging):
            stmt = select(model).where(
                model.id == archive_id, model.is_deleted.is_(False)
            )
            if tenant_id:
                stmt = stmt.where(model.tenant_id == tenant_id)
            obj = (await self.db.execute(stmt)).scalars().first()
            if obj:
                return obj
        return None

    async def _primary_pdf(self, archive_id: uuid.UUID) -> Optional[ArchiveAttachment]:
        rows = (
            (
                await self.db.execute(
                    select(ArchiveAttachment)
                    .where(
                        ArchiveAttachment.archive_id == archive_id,
                        ArchiveAttachment.is_deleted.is_(False),
                    )
                    .order_by(
                        ArchiveAttachment.is_primary.desc(),
                        ArchiveAttachment.sort_order,
                    )
                )
            )
            .scalars()
            .all()
        )
        for a in rows:
            name = (a.original_name or "").lower()
            fmt = (a.file_format or "").lower()
            if name.endswith(".pdf") or fmt == "pdf":
                return a
        return None
