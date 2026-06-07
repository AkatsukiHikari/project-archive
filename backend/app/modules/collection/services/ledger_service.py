"""
收集台账 + 催交看板聚合。

将归档计划（应交）与移交单（已交/在途）按 年度×移交单位×全宗×门类 聚合：
  应交 planned    — 计划件数
  已交 accepted   — 已接收入库件数
  在途 submitted  — 已提交但未接收完成
  完成率 / 逾期欠交 — 催交依据

纯内存聚合，避免 N+1，适合台账/看板规模数据。
"""
import uuid
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.collection.repositories.transfer_repo import (
    TransferBatchRepository,
    TransferPlanRepository,
)
from app.modules.collection.schemas.transfer import LedgerRow, LedgerSummary

# 已进入接收流水但未完成的状态（在途）
_IN_FLIGHT = {"submitted", "received"}


def _key(year: int, unit: str, fonds_id, category_id) -> tuple:
    return (year, unit, str(fonds_id), str(category_id))


class LedgerService:
    def __init__(self, db: AsyncSession) -> None:
        self._plans = TransferPlanRepository(db)
        self._batches = TransferBatchRepository(db)

    async def build(
        self, tenant_id: Optional[uuid.UUID], year: Optional[int] = None,
    ) -> LedgerSummary:
        plans = await self._plans.list(tenant_id, year=year, limit=10000)
        batches = await self._batches.list_all(tenant_id)
        if year is not None:
            batches = [b for b in batches if b.year == year]

        # 聚合桶
        buckets: dict[tuple, dict] = {}

        def bucket(year_: int, unit: str, fonds_id, category_id) -> dict:
            k = _key(year_, unit, fonds_id, category_id)
            if k not in buckets:
                buckets[k] = {
                    "year": year_,
                    "source_unit": unit,
                    "fonds_id": fonds_id,
                    "category_id": category_id,
                    "planned_count": 0,
                    "accepted_count": 0,
                    "submitted_count": 0,
                    "batch_total": 0,
                    "due_date": None,
                }
            return buckets[k]

        for p in plans:
            b = bucket(p.year, p.source_unit, p.fonds_id, p.category_id)
            b["planned_count"] += p.planned_count
            if p.due_date and (b["due_date"] is None or p.due_date < b["due_date"]):
                b["due_date"] = p.due_date

        for batch in batches:
            b = bucket(batch.year, batch.source_unit, batch.fonds_id, batch.category_id)
            b["batch_total"] += 1
            if batch.status == "accepted":
                b["accepted_count"] += batch.expected_count
            elif batch.status in _IN_FLIGHT:
                b["submitted_count"] += batch.expected_count

        today = date.today()
        rows: list[LedgerRow] = []
        for b in buckets.values():
            planned = b["planned_count"]
            accepted = b["accepted_count"]
            rate = round(accepted / planned * 100, 1) if planned > 0 else (
                100.0 if accepted > 0 else 0.0
            )
            overdue = bool(
                b["due_date"] and b["due_date"] < today and accepted < planned
            )
            rows.append(
                LedgerRow(
                    year=b["year"],
                    source_unit=b["source_unit"],
                    fonds_id=b["fonds_id"],
                    category_id=b["category_id"],
                    planned_count=planned,
                    accepted_count=accepted,
                    submitted_count=b["submitted_count"],
                    batch_total=b["batch_total"],
                    completion_rate=rate,
                    overdue=overdue,
                    due_date=b["due_date"],
                )
            )

        rows.sort(key=lambda r: (-r.year, r.overdue is False, r.source_unit))

        total_planned = sum(r.planned_count for r in rows)
        total_accepted = sum(r.accepted_count for r in rows)
        total_submitted = sum(r.submitted_count for r in rows)
        overall_rate = (
            round(total_accepted / total_planned * 100, 1) if total_planned > 0 else 0.0
        )
        overdue_units = sum(1 for r in rows if r.overdue)

        return LedgerSummary(
            year=year,
            total_planned=total_planned,
            total_accepted=total_accepted,
            total_submitted=total_submitted,
            overall_completion_rate=overall_rate,
            overdue_units=overdue_units,
            rows=rows,
        )
