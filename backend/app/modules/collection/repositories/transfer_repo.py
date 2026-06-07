from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collection.models.transfer import TransferBatch, TransferEntry
from app.modules.collection.models.transfer_plan import TransferPlan


def _scope(model, tenant_id: Optional[uuid.UUID]) -> list:
    conds = [model.is_deleted == False]  # noqa: E712
    if tenant_id is not None:
        conds.append(model.tenant_id == tenant_id)
    return conds


class TransferPlanRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, plan: TransferPlan) -> TransferPlan:
        self._db.add(plan)
        await self._db.flush()
        await self._db.refresh(plan)
        return plan

    async def get_by_id(
        self, plan_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[TransferPlan]:
        conds = [TransferPlan.id == plan_id, *_scope(TransferPlan, tenant_id)]
        result = await self._db.execute(select(TransferPlan).where(and_(*conds)))
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: Optional[uuid.UUID],
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[TransferPlan]:
        conds = _scope(TransferPlan, tenant_id)
        if year is not None:
            conds.append(TransferPlan.year == year)
        result = await self._db.execute(
            select(TransferPlan)
            .where(and_(*conds))
            .order_by(TransferPlan.year.desc(), TransferPlan.source_unit)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())


class TransferBatchRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, batch: TransferBatch) -> TransferBatch:
        self._db.add(batch)
        await self._db.flush()
        await self._db.refresh(batch)
        return batch

    async def get_by_id(
        self, batch_id: uuid.UUID, tenant_id: Optional[uuid.UUID] = None
    ) -> Optional[TransferBatch]:
        conds = [TransferBatch.id == batch_id, *_scope(TransferBatch, tenant_id)]
        result = await self._db.execute(select(TransferBatch).where(and_(*conds)))
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: Optional[uuid.UUID],
        status: Optional[str] = None,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[TransferBatch]:
        conds = _scope(TransferBatch, tenant_id)
        if status:
            conds.append(TransferBatch.status == status)
        if year is not None:
            conds.append(TransferBatch.year == year)
        result = await self._db.execute(
            select(TransferBatch)
            .where(and_(*conds))
            .order_by(TransferBatch.create_time.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_all(self, tenant_id: Optional[uuid.UUID]) -> list[TransferBatch]:
        """台账聚合用：拉取全部（未删除）移交单。"""
        conds = _scope(TransferBatch, tenant_id)
        result = await self._db.execute(select(TransferBatch).where(and_(*conds)))
        return list(result.scalars().all())


class TransferEntryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_by_batch(self, batch_id: uuid.UUID) -> list[TransferEntry]:
        result = await self._db.execute(
            select(TransferEntry)
            .where(
                and_(
                    TransferEntry.batch_id == batch_id,
                    TransferEntry.is_deleted == False,  # noqa: E712
                )
            )
            .order_by(TransferEntry.row_no)
        )
        return list(result.scalars().all())

    async def delete_by_batch(self, batch_id: uuid.UUID) -> None:
        """物理清空某移交单的明细（仅 draft 状态重置时使用）。"""
        for entry in await self.list_by_batch(batch_id):
            await self._db.delete(entry)
        await self._db.flush()

    def add(self, entry: TransferEntry) -> None:
        self._db.add(entry)
