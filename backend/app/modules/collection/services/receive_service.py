"""
接收登记服务（档案室侧）。

闭环：
  签收预检 precheck  → 四性闸门评分落库，移交单 submitted → received
  接收通过 accept     → 闸门通过(或强制)，明细物化为 repo_archive_staging
                       (pending_review) + 生成档号(DH) + ES 同步 + 审计
  退回    return      → 置 returned，附退回原因 + 审计

跨模块互通：
  - repository：ArchiveStaging 暂存库 + ArchiveNoEngine 档号规则
  - repository：es_sync_service 写入检索索引（与批量导入同链路）
  - audit：接收/退回动作落审计日志
  - preservation：物化后的暂存件可继续走完整四性检测（本预检为前置元数据闸门）
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.audit.models import AuditLog
from app.modules.collection.models.transfer import TransferBatch, TransferEntry
from app.modules.collection.repositories.transfer_repo import (
    TransferBatchRepository,
    TransferEntryRepository,
)
from app.modules.collection.services.precheck_service import (
    PrecheckResult,
    precheck_entries,
)
from app.modules.collection.services.transfer_service import entry_to_input
from app.modules.repository.models.archive import ArchiveStaging
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.models.fonds import Fonds

logger = logging.getLogger(__name__)


class ReceiveService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._batches = TransferBatchRepository(db)
        self._entries = TransferEntryRepository(db)

    # ── 签收 + 四性预检闸门 ────────────────────────────────────────

    async def precheck(
        self, batch_id: uuid.UUID, user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> tuple[TransferBatch, PrecheckResult]:
        batch = await self._require_batch(batch_id, tenant_id)
        if batch.status not in ("submitted", "received"):
            raise ValidationException(
                message=f"移交单状态为 {batch.status}，无法执行接收预检"
            )
        entries = await self._entries.list_by_batch(batch_id)
        result = precheck_entries(
            [entry_to_input(e) for e in entries],
            expected_count=batch.expected_count,
            handover_person=batch.handover_person,
        )

        # 落库：批级总分 + 逐条状态
        batch.precheck_score = round(result.score, 1)
        batch.precheck_passed = result.passed
        batch.precheck_detail = result.to_detail()
        batch.status = "received"
        batch.received_at = datetime.now(timezone.utc)
        batch.handler_id = user_id

        issue_map = {r.row_no: r for r in result.entries}
        for e in entries:
            r = issue_map.get(e.row_no)
            if r:
                e.precheck_status = r.status
                e.precheck_issues = r.issues or None

        await self._db.flush()
        return batch, result

    # ── 接收通过 → 物化入暂存库 ────────────────────────────────────

    async def accept(
        self, batch_id: uuid.UUID, user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
        catalog_id: Optional[uuid.UUID] = None, force: bool = False,
    ) -> TransferBatch:
        batch = await self._require_batch(batch_id, tenant_id)
        if batch.status != "received":
            raise ValidationException(message="请先完成接收预检（received）后再接收入库")

        if batch.precheck_passed is False and not force:
            raise ValidationException(
                code=ErrorCode.INTEGRITY_CHECK_FAILED,
                message="四性预检未通过闸门，如确需接收请走强制接收（force）",
            )

        target_catalog = catalog_id or batch.catalog_id
        if not target_catalog:
            raise ValidationException(message="请指定目标目录（catalog_id）")
        batch.catalog_id = target_catalog

        entries = await self._entries.list_by_batch(batch_id)
        if not entries:
            raise ValidationException(message="移交清单为空，无法接收")

        qzh = await self._resolve_qzh(batch.fonds_id)
        rule = await self._resolve_active_rule(batch.category_id)
        engine = None
        if rule is not None:
            from app.modules.repository.services.no_rule_engine import ArchiveNoEngine
            engine = ArchiveNoEngine(self._db)

        staging_records: list[tuple[TransferEntry, ArchiveStaging]] = []
        for e in entries:
            staging = self._build_staging(e, batch, qzh, target_catalog, tenant_id)
            if engine is not None and rule is not None:
                try:
                    staging.DH = await engine.generate(rule, staging)
                except Exception as exc:  # 档号生成失败不阻断接收
                    logger.warning("档号生成失败 entry=%s: %s", e.id, exc)
            self._db.add(staging)
            staging_records.append((e, staging))

        await self._db.flush()

        # 回填 staging_id + ES 同步
        for e, staging in staging_records:
            e.staging_id = staging.id
        await self._sync_es([s for _, s in staging_records])

        batch.status = "accepted"
        batch.accepted_at = datetime.now(timezone.utc)
        batch.handler_id = user_id

        self._audit(
            user_id, tenant_id, "accept",
            {
                "transfer_no": batch.transfer_no,
                "count": len(entries),
                "precheck_score": batch.precheck_score,
                "forced": bool(force and batch.precheck_passed is False),
            },
        )
        await self._db.flush()
        return batch

    # ── 退回 ──────────────────────────────────────────────────────

    async def return_batch(
        self, batch_id: uuid.UUID, user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID], reason: str,
    ) -> TransferBatch:
        batch = await self._require_batch(batch_id, tenant_id)
        if batch.status not in ("submitted", "received"):
            raise ValidationException(message=f"移交单状态为 {batch.status}，无法退回")
        batch.status = "returned"
        batch.return_reason = reason
        batch.handler_id = user_id
        self._audit(
            user_id, tenant_id, "return",
            {"transfer_no": batch.transfer_no, "reason": reason},
        )
        await self._db.flush()
        return batch

    # ── 内部 ──────────────────────────────────────────────────────

    def _build_staging(
        self, e: TransferEntry, batch: TransferBatch, qzh: str,
        catalog_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
    ) -> ArchiveStaging:
        return ArchiveStaging(
            fonds_id=batch.fonds_id,
            catalog_id=catalog_id,
            category_id=batch.category_id,
            QZH=qzh,
            TM=e.TM,
            RZZ=e.RZZ,
            ND=e.ND if e.ND is not None else batch.year,
            WJRQ=e.WJRQ,
            YS=e.YS,
            MJ=e.MJ or "public",
            BGQX=e.BGQX or "permanent",
            ext_fields=e.ext_fields,
            status="pending_review",
            tenant_id=tenant_id,
            create_by=batch.create_by,
        )

    async def _resolve_qzh(self, fonds_id: uuid.UUID) -> str:
        result = await self._db.execute(select(Fonds).where(Fonds.id == fonds_id))
        fonds = result.scalar_one_or_none()
        return fonds.fonds_code if fonds else ""

    async def _resolve_active_rule(self, category_id: uuid.UUID):
        result = await self._db.execute(
            select(ArchiveCategory).where(ArchiveCategory.id == category_id)
        )
        category = result.scalar_one_or_none()
        if not category or not category.archive_no_rule_id:
            return None
        from app.modules.repository.services.no_rule_service import NoRuleService
        try:
            return await NoRuleService(self._db).get(category.archive_no_rule_id)
        except Exception:
            return None

    async def _sync_es(self, archives: list[ArchiveStaging]) -> None:
        try:
            from app.modules.repository.services.es_sync_service import bulk_sync
            await bulk_sync(archives)
        except Exception as exc:  # 检索同步失败不阻断接收
            logger.warning("接收入库 ES 同步失败: %s", exc)

    def _audit(
        self, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
        action: str, details: dict,
    ) -> None:
        self._db.add(
            AuditLog(
                user_id=user_id,
                tenant_id=tenant_id,
                action=f"collection.receive.{action}",
                module="collection",
                status="SUCCESS",
                details=details,
            )
        )

    async def _require_batch(
        self, batch_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
    ) -> TransferBatch:
        batch = await self._batches.get_by_id(batch_id, tenant_id)
        if not batch:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message="移交单不存在")
        return batch
