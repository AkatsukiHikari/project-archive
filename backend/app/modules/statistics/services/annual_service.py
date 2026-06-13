"""年报：自动指标计算 + 草稿/定稿管理。"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.appraisal.models import AppraisalItem, AppraisalTask
from app.modules.collection.models.import_task import ImportTask
from app.modules.collection.models.transfer import TransferBatch, TransferEntry
from app.modules.repository.models.archive import (Archive, ArchiveAttachment,
                                                   ArchiveStaging, Catalog)
from app.modules.repository.models.fonds import Fonds
from app.modules.statistics.models import StatAnnualReport
from app.modules.statistics.services.annual_indicators import (
    INDICATOR_GROUPS, MANUAL_KEYS)
from app.modules.utilization.models.application import (UtilizationApplication,
                                                        UtilizationItem)


class AnnualReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 查询 ──────────────────────────────────────────────────────────────────

    async def list_reports(
        self, tenant_id: Optional[uuid.UUID]
    ) -> list[StatAnnualReport]:
        stmt = select(StatAnnualReport).where(StatAnnualReport.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(StatAnnualReport.tenant_id == tenant_id)
        return list(
            (
                await self.db.execute(stmt.order_by(StatAnnualReport.year.desc()))
            ).scalars()
        )

    async def get_report(
        self, year: int, tenant_id: Optional[uuid.UUID]
    ) -> Optional[StatAnnualReport]:
        stmt = select(StatAnnualReport).where(
            StatAnnualReport.year == year, StatAnnualReport.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(StatAnnualReport.tenant_id == tenant_id)
        return (await self.db.execute(stmt)).scalars().first()

    @staticmethod
    def definitions() -> list[dict]:
        return INDICATOR_GROUPS

    # ── 生成 / 重算 ───────────────────────────────────────────────────────────

    async def generate(
        self, year: int, user_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> StatAnnualReport:
        report = await self.get_report(year, tenant_id)
        if report and report.status == "final":
            raise ValidationException(
                code=ErrorCode.STAT_REPORT_FINALIZED,
                message=f"{year} 年报已定稿，不能重算",
            )
        auto = await self._compute_auto(year, tenant_id)
        if report is None:
            report = StatAnnualReport(
                year=year,
                status="draft",
                auto_data=auto,
                manual_data={},
                tenant_id=tenant_id,
                create_by=user_id,
            )
            self.db.add(report)
        else:
            report.auto_data = auto
        report.generated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return report

    async def save_manual(
        self, year: int, manual: dict, tenant_id: Optional[uuid.UUID]
    ) -> StatAnnualReport:
        report = await self._require_draft(year, tenant_id)
        cleaned = {
            k: v for k, v in manual.items() if k in MANUAL_KEYS and v is not None
        }
        report.manual_data = {**(report.manual_data or {}), **cleaned}
        await self.db.flush()
        return report

    async def finalize(
        self, year: int, tenant_id: Optional[uuid.UUID]
    ) -> StatAnnualReport:
        report = await self._require_draft(year, tenant_id)
        report.status = "final"
        report.finalized_at = datetime.now(timezone.utc)
        await self.db.flush()
        return report

    async def reopen(
        self, year: int, tenant_id: Optional[uuid.UUID]
    ) -> StatAnnualReport:
        report = await self.get_report(year, tenant_id)
        if not report:
            raise NotFoundException(
                code=ErrorCode.STAT_REPORT_NOT_FOUND, message="年报不存在"
            )
        report.status = "draft"
        report.finalized_at = None
        await self.db.flush()
        return report

    async def _require_draft(
        self, year: int, tenant_id: Optional[uuid.UUID]
    ) -> StatAnnualReport:
        report = await self.get_report(year, tenant_id)
        if not report:
            raise NotFoundException(
                code=ErrorCode.STAT_REPORT_NOT_FOUND, message="年报不存在，请先生成"
            )
        if report.status == "final":
            raise ValidationException(
                code=ErrorCode.STAT_REPORT_FINALIZED,
                message="年报已定稿，如需修改请先撤回",
            )
        return report

    # ── 自动指标计算 ──────────────────────────────────────────────────────────

    async def _compute_auto(self, year: int, tenant_id: Optional[uuid.UUID]) -> dict:
        def tenant_filter(stmt, col):
            return stmt.where(col == tenant_id) if tenant_id else stmt

        async def count(stmt) -> int:
            return (await self.db.execute(stmt)).scalar_one() or 0

        # 馆藏（正式库，未销毁）
        base = (
            select(func.count())
            .select_from(Archive)
            .where(Archive.is_deleted.is_(False), Archive.status != "destroyed")
        )
        base = tenant_filter(base, Archive.tenant_id)
        holdings_total = await count(base)

        # 卷 / 件拆分：所属目录类型为案卷目录的算"卷"
        volume_stmt = (
            select(func.count())
            .select_from(Archive)
            .join(Catalog, Archive.catalog_id == Catalog.id)
            .where(
                Archive.is_deleted.is_(False),
                Archive.status != "destroyed",
                Catalog.catalog_type == "案卷目录",
            )
        )
        holdings_volume = await count(tenant_filter(volume_stmt, Archive.tenant_id))
        holdings_piece = holdings_total - holdings_volume

        pre_1949 = await count(base.where(Archive.ND < 1949))

        fonds_count = await count(
            tenant_filter(
                select(func.count())
                .select_from(Fonds)
                .where(Fonds.is_deleted.is_(False)),
                Fonds.tenant_id,
            )
        )

        # 电子原文 / 数字化成果
        att_agg = (
            select(
                func.count(),
                func.coalesce(func.sum(ArchiveAttachment.file_size), 0),
                func.coalesce(func.sum(ArchiveAttachment.page_count), 0),
            )
            .select_from(ArchiveAttachment)
            .where(ArchiveAttachment.is_deleted.is_(False))
        )
        att_agg = tenant_filter(att_agg, ArchiveAttachment.tenant_id)
        e_count, e_bytes, frames = (await self.db.execute(att_agg)).one()

        # 数字化率以正式库口径：正式库中挂了原文的档案 / 馆藏总量
        digitized_stmt = (
            select(func.count(func.distinct(ArchiveAttachment.archive_id)))
            .select_from(ArchiveAttachment)
            .join(Archive, ArchiveAttachment.archive_id == Archive.id)
            .where(
                ArchiveAttachment.is_deleted.is_(False),
                ArchiveAttachment.is_staging.is_(False),
                Archive.is_deleted.is_(False),
            )
        )
        digitized_count = await count(tenant_filter(digitized_stmt, Archive.tenant_id))

        # 编目
        staging_count = await count(
            tenant_filter(
                select(func.count())
                .select_from(ArchiveStaging)
                .where(ArchiveStaging.is_deleted.is_(False)),
                ArchiveStaging.tenant_id,
            )
        )

        # 本年接收（接收入库的移交条目）
        received_stmt = (
            select(func.count())
            .select_from(TransferEntry)
            .join(TransferBatch, TransferEntry.batch_id == TransferBatch.id)
            .where(
                TransferBatch.status == "accepted",
                extract("year", TransferBatch.accepted_at) == year,
            )
        )
        year_received = await count(
            tenant_filter(received_stmt, TransferBatch.tenant_id)
        )

        year_archived = await count(
            base.where(extract("year", Archive.create_time) == year)
        )

        year_imported = await count(
            tenant_filter(
                select(func.coalesce(func.sum(ImportTask.success), 0)).where(
                    ImportTask.status == "done",
                    extract("year", ImportTask.create_time) == year,
                ),
                ImportTask.tenant_id,
            )
        )

        # 本年开放鉴定
        appraised_stmt = (
            select(func.count())
            .select_from(AppraisalItem)
            .join(AppraisalTask, AppraisalItem.task_id == AppraisalTask.id)
            .where(
                AppraisalItem.is_deleted.is_(False),
                AppraisalTask.status == "approved",
                extract("year", AppraisalTask.reviewed_at) == year,
            )
        )
        year_appraised = await count(
            tenant_filter(appraised_stmt, AppraisalItem.tenant_id)
        )
        year_opened = await count(
            appraised_stmt.where(AppraisalItem.final_kfzt == "开放")
        )

        # 本年利用
        util_stmt = (
            select(func.count())
            .select_from(UtilizationApplication)
            .where(
                UtilizationApplication.is_deleted.is_(False),
                extract("year", UtilizationApplication.create_time) == year,
            )
        )
        year_util_visits = await count(
            tenant_filter(util_stmt, UtilizationApplication.tenant_id)
        )

        util_items_stmt = (
            select(func.count())
            .select_from(UtilizationItem)
            .join(
                UtilizationApplication,
                UtilizationItem.application_id == UtilizationApplication.id,
            )
            .where(
                UtilizationItem.is_deleted.is_(False),
                extract("year", UtilizationApplication.create_time) == year,
            )
        )
        year_util_items = await count(
            tenant_filter(util_items_stmt, UtilizationItem.tenant_id)
        )

        gb = 1024**3
        e_bytes = float(e_bytes or 0)
        frames = int(frames or 0)
        return {
            "fonds_count": fonds_count,
            "holdings_volume": holdings_volume,
            "holdings_piece": holdings_piece,
            "pre_1949": pre_1949,
            "e_archive_count": e_count,
            "e_capacity_gb": round(e_bytes / gb, 2),
            "digitized_count": digitized_count,
            "digitized_gb": round(e_bytes / gb, 2),
            "digitized_rate": (
                round(digitized_count / holdings_total * 100, 1)
                if holdings_total
                else 0
            ),
            "digitized_frames": frames,
            "catalog_file_level": staging_count + holdings_total,
            "catalog_volume_level": holdings_volume,
            "year_received": year_received,
            "year_archived": year_archived,
            "year_imported": year_imported,
            "year_appraised": year_appraised,
            "year_opened": year_opened,
            "year_util_visits": year_util_visits,
            "year_util_items": year_util_items,
        }
