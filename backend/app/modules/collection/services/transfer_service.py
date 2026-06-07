"""
归档移交服务：归档计划 + 移交单（移交清单）生命周期。

移交单状态机： draft → submitted →（档案室）received → accepted / returned
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.collection.models.transfer import TransferBatch, TransferEntry
from app.modules.collection.models.transfer_plan import TransferPlan
from app.modules.collection.repositories.transfer_repo import (
    TransferBatchRepository,
    TransferEntryRepository,
    TransferPlanRepository,
)
from app.modules.collection.schemas.transfer import (
    TransferBatchCreate,
    TransferEntryIn,
    TransferPlanCreate,
    TransferPlanUpdate,
)
from app.modules.collection.services.precheck_service import (
    EntryInput,
    PrecheckResult,
    precheck_entries,
)

# 提交后不可再编辑明细的状态
_LOCKED_STATUSES = {"submitted", "received", "accepted"}


def _gen_transfer_no(year: int) -> str:
    """移交单号：YJ{年度}{月日}{4位随机}，全局可读且基本唯一。"""
    now = datetime.now(timezone.utc)
    return f"YJ{year}{now:%m%d}{uuid.uuid4().hex[:4].upper()}"


def entry_to_input(entry: TransferEntry) -> EntryInput:
    return EntryInput(
        row_no=entry.row_no,
        TM=entry.TM,
        RZZ=entry.RZZ,
        ND=entry.ND,
        WJRQ=entry.WJRQ,
        YS=entry.YS,
        MJ=entry.MJ,
        BGQX=entry.BGQX,
    )


class TransferService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._plans = TransferPlanRepository(db)
        self._batches = TransferBatchRepository(db)
        self._entries = TransferEntryRepository(db)

    # ── 归档计划 ──────────────────────────────────────────────────

    async def create_plan(
        self, data: TransferPlanCreate, user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> TransferPlan:
        plan = TransferPlan(
            year=data.year,
            source_unit=data.source_unit,
            source_org_id=data.source_org_id,
            fonds_id=data.fonds_id,
            category_id=data.category_id,
            planned_count=data.planned_count,
            due_date=data.due_date,
            notes=data.notes,
            status="active",
            tenant_id=tenant_id,
            create_by=user_id,
        )
        return await self._plans.create(plan)

    async def update_plan(
        self, plan_id: uuid.UUID, data: TransferPlanUpdate,
        tenant_id: Optional[uuid.UUID],
    ) -> TransferPlan:
        plan = await self._plans.get_by_id(plan_id, tenant_id)
        if not plan:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message="归档计划不存在")
        if data.planned_count is not None:
            plan.planned_count = data.planned_count
        if data.due_date is not None:
            plan.due_date = data.due_date
        if data.status is not None:
            plan.status = data.status
        if data.notes is not None:
            plan.notes = data.notes
        await self._db.flush()
        return plan

    async def list_plans(
        self, tenant_id: Optional[uuid.UUID], year: Optional[int] = None,
        skip: int = 0, limit: int = 100,
    ) -> list[TransferPlan]:
        return await self._plans.list(tenant_id, year=year, skip=skip, limit=limit)

    # ── 移交单 ────────────────────────────────────────────────────

    async def create_batch(
        self, data: TransferBatchCreate, user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
    ) -> TransferBatch:
        batch = TransferBatch(
            transfer_no=_gen_transfer_no(data.year),
            plan_id=data.plan_id,
            source_unit=data.source_unit,
            source_org_id=data.source_org_id,
            fonds_id=data.fonds_id,
            category_id=data.category_id,
            catalog_id=data.catalog_id,
            year=data.year,
            handover_person=data.handover_person,
            handover_date=data.handover_date,
            expected_count=len(data.entries),
            status="draft",
            notes=data.notes,
            tenant_id=tenant_id,
            create_by=user_id,
        )
        batch = await self._batches.create(batch)
        if data.entries:
            self._materialize_entries(batch, data.entries, tenant_id)
            await self._db.flush()
        return batch

    async def replace_entries(
        self, batch_id: uuid.UUID, entries: list[TransferEntryIn],
        tenant_id: Optional[uuid.UUID],
    ) -> TransferBatch:
        batch = await self._require_batch(batch_id, tenant_id)
        if batch.status in _LOCKED_STATUSES:
            raise ValidationException(message=f"移交单状态为 {batch.status}，不可编辑明细")
        await self._entries.delete_by_batch(batch_id)
        self._materialize_entries(batch, entries, tenant_id)
        batch.expected_count = len(entries)
        await self._db.flush()
        return batch

    async def submit_batch(
        self, batch_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
    ) -> TransferBatch:
        batch = await self._require_batch(batch_id, tenant_id)
        if batch.status not in ("draft", "returned"):
            raise ValidationException(message=f"移交单状态为 {batch.status}，无法提交移交")
        entries = await self._entries.list_by_batch(batch_id)
        if not entries:
            raise ValidationException(message="移交清单为空，无法提交")
        batch.status = "submitted"
        batch.submitted_at = datetime.now(timezone.utc)
        batch.return_reason = None
        await self._db.flush()
        return batch

    # ── 查询 ──────────────────────────────────────────────────────

    async def list_batches(
        self, tenant_id: Optional[uuid.UUID], status: Optional[str] = None,
        year: Optional[int] = None, skip: int = 0, limit: int = 50,
    ) -> list[TransferBatch]:
        return await self._batches.list(
            tenant_id, status=status, year=year, skip=skip, limit=limit
        )

    async def get_batch(
        self, batch_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
    ) -> tuple[TransferBatch, list[TransferEntry]]:
        batch = await self._require_batch(batch_id, tenant_id)
        entries = await self._entries.list_by_batch(batch_id)
        return batch, entries

    async def preview_precheck(
        self, batch_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
    ) -> PrecheckResult:
        """对移交单运行四性预检（不落库，供前端预演）。"""
        batch = await self._require_batch(batch_id, tenant_id)
        entries = await self._entries.list_by_batch(batch_id)
        return precheck_entries(
            [entry_to_input(e) for e in entries],
            expected_count=batch.expected_count,
            handover_person=batch.handover_person,
        )

    # ── 内部 ──────────────────────────────────────────────────────

    def _materialize_entries(
        self, batch: TransferBatch, entries: list[TransferEntryIn],
        tenant_id: Optional[uuid.UUID],
    ) -> None:
        for i, e in enumerate(entries, start=1):
            self._entries.add(
                TransferEntry(
                    batch_id=batch.id,
                    row_no=i,
                    TM=e.TM,
                    RZZ=e.RZZ,
                    ND=e.ND,
                    WJRQ=e.WJRQ,
                    YS=e.YS,
                    MJ=e.MJ,
                    BGQX=e.BGQX,
                    ext_fields=e.ext_fields,
                    precheck_status="pending",
                    tenant_id=tenant_id,
                    create_by=batch.create_by,
                )
            )

    async def _require_batch(
        self, batch_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
    ) -> TransferBatch:
        batch = await self._batches.get_by_id(batch_id, tenant_id)
        if not batch:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message="移交单不存在")
        return batch
