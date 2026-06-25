"""数字化成果挂接服务。

单条：上传 PDF/OFD 原文、删除、设主附件。
批量：文件名（去扩展名）= 档号(DH) 匹配，先暂存库后正式库；
     预检（只传文件名）和执行（真上传）两步式。
"""

import hashlib
import io
import logging
import re
import uuid
from typing import BinaryIO, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.infra.storage.factory import storage
from app.modules.repository.models.attach_batch import AttachBatch
from app.modules.repository.models.archive import (Archive, ArchiveAttachment,
                                                   ArchiveStaging)

logger = logging.getLogger(__name__)

ALLOWED_FORMATS = {"pdf": "application/pdf", "ofd": "application/ofd"}
ATTACHMENT_BUCKET = "archives"
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200MB


class MatchTarget:
    """档号匹配结果（暂存库或正式库的一条档案）。"""

    __slots__ = ("archive_id", "TM", "DH", "source", "is_staging", "tenant_id")

    def __init__(self, archive_id: uuid.UUID, tm: str, dh: str, source: str, tenant_id):
        self.archive_id = archive_id
        self.TM = tm
        self.DH = dh  # 档号——挂接后附件统一以此命名
        self.source = source  # staging | formal
        self.is_staging = source == "staging"
        self.tenant_id = tenant_id


class AttachmentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 单条上传 / 删除 / 主附件 ──────────────────────────────────────────────

    async def upload(
        self,
        archive_id: uuid.UUID,
        filename: str,
        content: bytes,
        user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
        is_primary: bool = True,
    ) -> ArchiveAttachment:
        target = await self._find_by_id(archive_id, tenant_id)
        if target is None:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_NOT_FOUND, message="档案不存在"
            )
        fmt = self._validate_file(filename, content)
        if is_primary:
            await self._demote_primary(target.archive_id)
        attachment = self._build_attachment(
            target, filename, content, fmt, user_id, is_primary=is_primary
        )
        self.db.add(attachment)
        await self.db.flush()
        return attachment

    async def delete(
        self, attachment_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> None:
        attachment = await self._require_attachment(attachment_id, tenant_id)
        attachment.is_deleted = True

    async def set_primary(
        self, attachment_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ArchiveAttachment:
        attachment = await self._require_attachment(attachment_id, tenant_id)
        await self._demote_primary(attachment.archive_id)
        attachment.is_primary = True
        await self.db.flush()
        return attachment

    # ── 批量挂接 ──────────────────────────────────────────────────────────────

    async def match_preview(
        self, filenames: list[str], tenant_id: Optional[uuid.UUID]
    ) -> list[dict]:
        """预检：按 文件名去扩展名=DH 匹配，返回每个文件的匹配情况。"""
        rows: list[dict] = []
        for name in filenames:
            dh = self._strip_ext(name)
            target = await self._find_by_dh(dh, tenant_id)
            if target is None:
                rows.append({"filename": name, "DH": dh, "status": "not_found"})
                continue
            status = (
                "has_primary"
                if await self._has_primary(target.archive_id)
                else "matched"
            )
            rows.append(
                {
                    "filename": name,
                    "DH": dh,
                    "status": status,
                    "source": target.source,
                    "archive_id": target.archive_id,
                    "TM": target.TM,
                }
            )
        return rows

    async def batch_attach(
        self,
        files: list[tuple[str, bytes]],
        user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
        overwrite: bool = False,
    ) -> tuple[AttachBatch, list[dict]]:
        """执行挂接：matched 的存储并建附件记录；已有原文按 overwrite 决定跳过或替换。

        每次执行落一条挂接批次（repo_attach_batch），含逐文件明细，供历史追溯。
        """
        rows: list[dict] = []
        for name, content in files:
            dh = self._strip_ext(name)
            base = {"filename": name, "DH": dh}
            target = await self._find_by_dh(dh, tenant_id)
            if target is None:
                rows.append({**base, "status": "not_found"})
                continue
            base.update(
                {
                    "source": target.source,
                    "archive_id": target.archive_id,
                    "TM": target.TM,
                }
            )

            has_primary = await self._has_primary(target.archive_id)
            if has_primary and not overwrite:
                rows.append({**base, "status": "skipped"})
                continue

            try:
                fmt = self._validate_file(name, content)
            except ValidationException as exc:
                rows.append({**base, "status": "skipped", "reason": exc.message})
                continue

            if has_primary:
                await self._demote_primary(target.archive_id, soft_delete=True)
            attachment = self._build_attachment(
                target, name, content, fmt, user_id, is_primary=True
            )
            self.db.add(attachment)
            # 逐条 flush：同一档号在一批里有多个文件时，后续 _has_primary 才能看到前一条
            await self.db.flush()
            rows.append({**base, "status": "attached"})

        batch = AttachBatch(
            batch_no=await self._next_batch_no(),
            total=len(rows),
            attached=sum(1 for r in rows if r["status"] == "attached"),
            skipped=sum(1 for r in rows if r["status"] == "skipped"),
            not_found=sum(1 for r in rows if r["status"] == "not_found"),
            overwrite=overwrite,
            rows=[{**r, "archive_id": str(r["archive_id"])} if r.get("archive_id") else r for r in rows],
            operator_id=user_id,
            tenant_id=tenant_id,
            create_by=user_id,
        )
        self.db.add(batch)
        await self.db.flush()
        return batch, rows

    # ── 挂接历史 ──────────────────────────────────────────────────────────────

    async def list_batches(
        self, tenant_id: Optional[uuid.UUID], skip: int = 0, limit: int = 20
    ) -> tuple[int, list[AttachBatch]]:
        stmt = select(AttachBatch).where(AttachBatch.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(AttachBatch.tenant_id == tenant_id)
        total = (await self.db.execute(
            select(func.count()).select_from(stmt.subquery())
        )).scalar_one()
        batches = (await self.db.execute(
            stmt.order_by(AttachBatch.create_time.desc()).offset(skip).limit(limit)
        )).scalars().all()
        return total, list(batches)

    async def get_batch(
        self, batch_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> AttachBatch:
        stmt = select(AttachBatch).where(
            AttachBatch.id == batch_id, AttachBatch.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(AttachBatch.tenant_id == tenant_id)
        batch = (await self.db.execute(stmt)).scalars().first()
        if not batch:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_FILE_NOT_FOUND, message="挂接批次不存在"
            )
        return batch

    async def _next_batch_no(self) -> str:
        from datetime import date

        prefix = f"GJ{date.today().strftime('%Y%m%d')}"
        count = (await self.db.execute(
            select(func.count()).select_from(AttachBatch).where(
                AttachBatch.batch_no.like(f"{prefix}%")
            )
        )).scalar_one()
        return f"{prefix}{count + 1:03d}"

    # ── 内部 ──────────────────────────────────────────────────────────────────

    def _build_attachment(
        self,
        target: MatchTarget,
        filename: str,
        content: bytes,
        fmt: str,
        user_id: uuid.UUID,
        is_primary: bool,
    ) -> ArchiveAttachment:
        # 挂接后统一以档号命名（无论上传时原文件名是什么）；无档号时兜底用原名
        display_name = f"{target.DH}.{fmt}" if target.DH else filename
        key = f"archive/{target.archive_id}/{uuid.uuid4().hex[:8]}_{self._safe_name(display_name)}"
        storage.save(io.BytesIO(content), key, ATTACHMENT_BUCKET, ALLOWED_FORMATS[fmt])
        return ArchiveAttachment(
            archive_id=target.archive_id,
            is_staging=target.is_staging,
            is_primary=is_primary,
            original_name=display_name[:500],
            storage_key=key,
            storage_bucket=ATTACHMENT_BUCKET,
            file_size=len(content),
            file_format=fmt,
            page_count=self._pdf_page_count(content) if fmt == "pdf" else None,
            sha256_hash=hashlib.sha256(content).hexdigest(),
            tenant_id=target.tenant_id,
            create_by=user_id,
        )

    @staticmethod
    def _validate_file(filename: str, content: bytes) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_FORMATS:
            raise ValidationException(message=f"仅支持 PDF / OFD 格式，收到 .{ext}")
        if not content:
            raise ValidationException(message="文件内容为空")
        if len(content) > MAX_FILE_SIZE:
            raise ValidationException(message="文件超过 200MB 上限")
        if ext == "pdf" and not content.lstrip()[:5].startswith(b"%PDF-"):
            raise ValidationException(message="文件内容不是有效的 PDF")
        return ext

    @staticmethod
    def _strip_ext(filename: str) -> str:
        name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return name.rsplit(".", 1)[0] if "." in name else name

    @staticmethod
    def _safe_name(filename: str) -> str:
        name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return re.sub(r"[^\w.\-一-鿿]", "_", name)[:120]

    @staticmethod
    def _pdf_page_count(content: bytes) -> Optional[int]:
        """轻量启发式统计 PDF 页数（不引第三方库；失败返回 None）。"""
        try:
            count = len(re.findall(rb"/Type\s*/Page[^s]", content))
            return count or None
        except Exception:
            return None

    async def _find_by_dh(
        self, dh: str, tenant_id: Optional[uuid.UUID]
    ) -> Optional[MatchTarget]:
        stmt = select(ArchiveStaging).where(
            ArchiveStaging.DH == dh, ArchiveStaging.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(ArchiveStaging.tenant_id == tenant_id)
        staging = (await self.db.execute(stmt.limit(1))).scalars().first()
        if staging:
            return MatchTarget(staging.id, staging.TM, staging.DH, "staging", staging.tenant_id)

        stmt = select(Archive).where(Archive.DH == dh, Archive.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(Archive.tenant_id == tenant_id)
        formal = (await self.db.execute(stmt.limit(1))).scalars().first()
        if formal:
            return MatchTarget(formal.id, formal.TM, formal.DH, "formal", formal.tenant_id)
        return None

    async def _find_by_id(
        self, archive_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> Optional[MatchTarget]:
        staging = (
            (
                await self.db.execute(
                    select(ArchiveStaging).where(
                        ArchiveStaging.id == archive_id,
                        ArchiveStaging.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .first()
        )
        if staging:
            return MatchTarget(staging.id, staging.TM, staging.DH, "staging", staging.tenant_id)
        formal = (
            (
                await self.db.execute(
                    select(Archive).where(
                        Archive.id == archive_id, Archive.is_deleted.is_(False)
                    )
                )
            )
            .scalars()
            .first()
        )
        if formal:
            return MatchTarget(formal.id, formal.TM, formal.DH, "formal", formal.tenant_id)
        return None

    async def _has_primary(self, archive_id: uuid.UUID) -> bool:
        count = (
            await self.db.execute(
                select(func.count())
                .select_from(ArchiveAttachment)
                .where(
                    ArchiveAttachment.archive_id == archive_id,
                    ArchiveAttachment.is_primary.is_(True),
                    ArchiveAttachment.is_deleted.is_(False),
                )
            )
        ).scalar_one()
        return count > 0

    async def _demote_primary(
        self, archive_id: uuid.UUID, soft_delete: bool = False
    ) -> None:
        attachments = (
            (
                await self.db.execute(
                    select(ArchiveAttachment).where(
                        ArchiveAttachment.archive_id == archive_id,
                        ArchiveAttachment.is_primary.is_(True),
                        ArchiveAttachment.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        for att in attachments:
            if soft_delete:
                att.is_deleted = True
            else:
                att.is_primary = False

    async def _require_attachment(
        self, attachment_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> ArchiveAttachment:
        stmt = select(ArchiveAttachment).where(
            ArchiveAttachment.id == attachment_id,
            ArchiveAttachment.is_deleted.is_(False),
        )
        if tenant_id:
            stmt = stmt.where(ArchiveAttachment.tenant_id == tenant_id)
        attachment = (await self.db.execute(stmt)).scalars().first()
        if not attachment:
            raise NotFoundException(
                code=ErrorCode.ARCHIVE_FILE_NOT_FOUND, message="附件不存在"
            )
        return attachment
