"""综合统计 / 大屏驾驶舱 聚合查询（全部只读）。"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appraisal.models import AppraisalTask
from app.modules.collection.models.transfer import TransferBatch
from app.modules.preservation.models.run import DetectionBatch
from app.modules.repository.models.archive import (Archive, ArchiveAttachment,
                                                   ArchiveStaging)
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.models.fonds import Fonds
from app.modules.utilization.models.application import UtilizationApplication

MJ_LABELS = {
    "public": "公开",
    "internal": "内部",
    "secret": "秘密",
    "confidential": "机密",
}
BGQX_LABELS = {"permanent": "永久", "long": "长期", "short": "短期"}
USE_TYPE_LABELS = {
    "read": "查阅",
    "borrow": "借阅",
    "copy": "复制",
    "certificate": "出具证明",
}


class OverviewService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def overview(
        self, tenant_id: Optional[uuid.UUID], fonds_id: Optional[uuid.UUID] = None
    ) -> dict:
        kpi = await self._kpi(tenant_id, fonds_id)
        return {
            "kpi": kpi,
            "charts": {
                "holdings_by_year": await self._holdings_by_year(tenant_id, fonds_id),
                "by_category": await self._group(
                    ArchiveCategory.name, tenant_id, fonds_id, join_category=True
                ),
                "by_bgqx": self._relabel(
                    await self._group(Archive.BGQX, tenant_id, fonds_id), BGQX_LABELS
                ),
                "by_mj": self._relabel(
                    await self._group(Archive.MJ, tenant_id, fonds_id), MJ_LABELS
                ),
                "by_kfzt": await self._kfzt_dist(tenant_id, fonds_id),
                "by_fonds": await self._by_fonds(tenant_id),
                "monthly_new": await self._monthly_new(tenant_id, fonds_id),
                "util_by_type": await self._util_by_type(tenant_id),
                "util_monthly": await self._util_monthly(tenant_id),
            },
        }

    async def cockpit(self, tenant_id: Optional[uuid.UUID]) -> dict:
        kpi = await self._kpi(tenant_id, None)
        today = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        today_util = await self._count(
            self._tenant(
                select(func.count())
                .select_from(UtilizationApplication)
                .where(
                    UtilizationApplication.is_deleted.is_(False),
                    UtilizationApplication.create_time >= today,
                ),
                UtilizationApplication.tenant_id,
                tenant_id,
            )
        )
        transit_transfers = await self._count(
            self._tenant(
                select(func.count())
                .select_from(TransferBatch)
                .where(
                    TransferBatch.is_deleted.is_(False),
                    TransferBatch.status.in_(["submitted", "received"]),
                ),
                TransferBatch.tenant_id,
                tenant_id,
            )
        )
        active_appraisal = await self._count(
            self._tenant(
                select(func.count())
                .select_from(AppraisalTask)
                .where(
                    AppraisalTask.is_deleted.is_(False),
                    AppraisalTask.status != "approved",
                ),
                AppraisalTask.tenant_id,
                tenant_id,
            )
        )

        since = datetime.now(timezone.utc) - timedelta(days=90)
        det = (
            await self.db.execute(
                self._tenant(
                    select(
                        func.coalesce(
                            func.sum(DetectionBatch.passed + DetectionBatch.warned), 0
                        ),
                        func.coalesce(func.sum(DetectionBatch.total), 0),
                    )
                    .select_from(DetectionBatch)
                    .where(
                        DetectionBatch.is_deleted.is_(False),
                        DetectionBatch.create_time >= since,
                    ),
                    DetectionBatch.tenant_id,
                    tenant_id,
                )
            )
        ).one()
        detection_pass_rate = round(det[0] / det[1] * 100, 1) if det[1] else None

        return {
            "kpi": kpi,
            "dynamic": {
                "today_util": today_util,
                "transit_transfers": transit_transfers,
                "active_appraisal_tasks": active_appraisal,
                "detection_pass_rate": detection_pass_rate,
            },
            "charts": {
                "holdings_by_year": await self._holdings_by_year(tenant_id, None),
                "by_category": await self._group(
                    ArchiveCategory.name, tenant_id, None, join_category=True
                ),
                "by_kfzt": await self._kfzt_dist(tenant_id, None),
                "by_fonds": await self._by_fonds(tenant_id),
                "util_monthly": await self._util_monthly(tenant_id),
                "by_bgqx": self._relabel(
                    await self._group(Archive.BGQX, tenant_id, None), BGQX_LABELS
                ),
            },
        }

    # ── KPI ───────────────────────────────────────────────────────────────────

    async def _kpi(
        self, tenant_id: Optional[uuid.UUID], fonds_id: Optional[uuid.UUID]
    ) -> dict:
        base = self._archive_base(tenant_id, fonds_id)
        total = await self._count(base)
        this_year = date.today().year
        year_new = await self._count(
            base.where(extract("year", Archive.create_time) == this_year)
        )

        staging_stmt = (
            select(func.count())
            .select_from(ArchiveStaging)
            .where(ArchiveStaging.is_deleted.is_(False))
        )
        staging_stmt = self._tenant(staging_stmt, ArchiveStaging.tenant_id, tenant_id)
        if fonds_id:
            staging_stmt = staging_stmt.where(ArchiveStaging.fonds_id == fonds_id)
        staging_pending = await self._count(staging_stmt)

        fonds_count = await self._count(
            self._tenant(
                select(func.count())
                .select_from(Fonds)
                .where(Fonds.is_deleted.is_(False)),
                Fonds.tenant_id,
                tenant_id,
            )
        )

        digitized_stmt = (
            select(func.count(func.distinct(ArchiveAttachment.archive_id)))
            .select_from(ArchiveAttachment)
            .join(Archive, ArchiveAttachment.archive_id == Archive.id)
            .where(
                ArchiveAttachment.is_deleted.is_(False),
                Archive.is_deleted.is_(False),
                Archive.status != "destroyed",
            )
        )
        digitized_stmt = self._tenant(digitized_stmt, Archive.tenant_id, tenant_id)
        if fonds_id:
            digitized_stmt = digitized_stmt.where(Archive.fonds_id == fonds_id)
        digitized = await self._count(digitized_stmt)

        cap_stmt = self._tenant(
            select(func.coalesce(func.sum(ArchiveAttachment.file_size), 0)).where(
                ArchiveAttachment.is_deleted.is_(False)
            ),
            ArchiveAttachment.tenant_id,
            tenant_id,
        )
        capacity_bytes = float((await self.db.execute(cap_stmt)).scalar_one() or 0)

        opened = await self._count(base.where(Archive.KFZT == "开放"))

        util_stmt = self._tenant(
            select(func.count())
            .select_from(UtilizationApplication)
            .where(
                UtilizationApplication.is_deleted.is_(False),
                extract("year", UtilizationApplication.create_time) == this_year,
            ),
            UtilizationApplication.tenant_id,
            tenant_id,
        )
        year_util = await self._count(util_stmt)

        return {
            "holdings_total": total,
            "staging_pending": staging_pending,
            "fonds_count": fonds_count,
            "year_new": year_new,
            "digitized_count": digitized,
            "digitized_rate": round(digitized / total * 100, 1) if total else 0,
            "capacity_gb": round(capacity_bytes / 1024**3, 2),
            "year_util_visits": year_util,
            "opened_count": opened,
            "open_rate": round(opened / total * 100, 1) if total else 0,
        }

    # ── 图表 ──────────────────────────────────────────────────────────────────

    async def _holdings_by_year(self, tenant_id, fonds_id) -> list[dict]:
        stmt = (
            select(Archive.ND, func.count())
            .where(Archive.is_deleted.is_(False), Archive.status != "destroyed")
            .group_by(Archive.ND)
            .order_by(Archive.ND)
        )
        stmt = self._tenant(stmt, Archive.tenant_id, tenant_id)
        if fonds_id:
            stmt = stmt.where(Archive.fonds_id == fonds_id)
        rows = (await self.db.execute(stmt)).all()
        return [{"name": str(r[0]), "value": r[1]} for r in rows if r[0] is not None]

    async def _group(
        self, column, tenant_id, fonds_id, join_category: bool = False
    ) -> list[dict]:
        stmt = (
            select(column, func.count())
            .select_from(Archive)
            .where(Archive.is_deleted.is_(False), Archive.status != "destroyed")
        )
        if join_category:
            stmt = stmt.join(ArchiveCategory, Archive.category_id == ArchiveCategory.id)
        stmt = self._tenant(stmt, Archive.tenant_id, tenant_id)
        if fonds_id:
            stmt = stmt.where(Archive.fonds_id == fonds_id)
        rows = (
            await self.db.execute(stmt.group_by(column).order_by(func.count().desc()))
        ).all()
        return [{"name": r[0] or "未填", "value": r[1]} for r in rows]

    async def _kfzt_dist(self, tenant_id, fonds_id) -> list[dict]:
        col = func.coalesce(Archive.KFZT, "未鉴定")
        stmt = (
            select(col, func.count())
            .select_from(Archive)
            .where(Archive.is_deleted.is_(False), Archive.status != "destroyed")
        )
        stmt = self._tenant(stmt, Archive.tenant_id, tenant_id)
        if fonds_id:
            stmt = stmt.where(Archive.fonds_id == fonds_id)
        rows = (await self.db.execute(stmt.group_by(col))).all()
        order = {"开放": 0, "控制使用": 1, "延期开放": 2, "不开放": 3, "未鉴定": 4}
        return sorted(
            [{"name": r[0], "value": r[1]} for r in rows],
            key=lambda x: order.get(x["name"], 9),
        )

    async def _by_fonds(self, tenant_id) -> list[dict]:
        stmt = (
            select(Fonds.fonds_code, Fonds.name, func.count(Archive.id))
            .select_from(Fonds)
            .outerjoin(
                Archive, (Archive.fonds_id == Fonds.id) & Archive.is_deleted.is_(False)
            )
            .where(Fonds.is_deleted.is_(False))
            .group_by(Fonds.id, Fonds.fonds_code, Fonds.name)
            .order_by(Fonds.fonds_code)
        )
        stmt = self._tenant(stmt, Fonds.tenant_id, tenant_id)
        rows = (await self.db.execute(stmt)).all()
        return [{"name": f"{r[0]} {r[1]}", "value": r[2]} for r in rows]

    async def _monthly_new(self, tenant_id, fonds_id) -> list[dict]:
        return await self._monthly_trend(
            Archive, Archive.create_time, tenant_id, extra_fonds=fonds_id
        )

    async def _util_monthly(self, tenant_id) -> list[dict]:
        return await self._monthly_trend(
            UtilizationApplication, UtilizationApplication.create_time, tenant_id
        )

    async def _monthly_trend(
        self, model, time_col, tenant_id, extra_fonds=None
    ) -> list[dict]:
        since = (
            datetime.now(timezone.utc).replace(day=1) - timedelta(days=335)
        ).replace(day=1)
        month = func.to_char(time_col, "YYYY-MM")
        stmt = (
            select(month, func.count())
            .select_from(model)
            .where(model.is_deleted.is_(False), time_col >= since)
        )
        stmt = self._tenant(stmt, model.tenant_id, tenant_id)
        if extra_fonds is not None and hasattr(model, "fonds_id"):
            stmt = stmt.where(model.fonds_id == extra_fonds)
        rows = dict((await self.db.execute(stmt.group_by(month))).all())

        out: list[dict] = []
        cursor = since
        now = datetime.now(timezone.utc)
        while cursor <= now:
            key = cursor.strftime("%Y-%m")
            out.append({"name": key, "value": rows.get(key, 0)})
            cursor = (cursor + timedelta(days=32)).replace(day=1)
        return out

    async def _util_by_type(self, tenant_id) -> list[dict]:
        stmt = select(UtilizationApplication.use_type, func.count()).where(
            UtilizationApplication.is_deleted.is_(False)
        )
        stmt = self._tenant(stmt, UtilizationApplication.tenant_id, tenant_id)
        rows = (
            await self.db.execute(stmt.group_by(UtilizationApplication.use_type))
        ).all()
        return [{"name": USE_TYPE_LABELS.get(r[0], r[0]), "value": r[1]} for r in rows]

    # ── 内部 ──────────────────────────────────────────────────────────────────

    def _archive_base(self, tenant_id, fonds_id):
        stmt = (
            select(func.count())
            .select_from(Archive)
            .where(Archive.is_deleted.is_(False), Archive.status != "destroyed")
        )
        stmt = self._tenant(stmt, Archive.tenant_id, tenant_id)
        if fonds_id:
            stmt = stmt.where(Archive.fonds_id == fonds_id)
        return stmt

    @staticmethod
    def _tenant(stmt, col, tenant_id):
        return stmt.where(col == tenant_id) if tenant_id else stmt

    async def _count(self, stmt) -> int:
        return (await self.db.execute(stmt)).scalar_one() or 0

    @staticmethod
    def _relabel(rows: list[dict], labels: dict) -> list[dict]:
        return [
            {"name": labels.get(r["name"], r["name"]), "value": r["value"]}
            for r in rows
        ]
