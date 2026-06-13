"""开放鉴定到期圈定。

判断一件档案是否到了该鉴定的时间：
  基准日 = 最近鉴定日期 JDRQ → 成文/文件日期 WJRQ → 年度 ND 年末 → 归档时间
  到期   = 基准日 + 保管期限年数 ≤ 今天

保管期限年数从 BGQX 字典解析（"30年"→30）；"永久"或解析不到数字的，
按《档案法》满 25 年进入开放鉴定范围。
兼容旧数据中的英文存值（permanent/long/short）。
"""

import calendar
import re
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.appraisal.models import AppraisalItem, AppraisalTask
from app.modules.iam.models.dict import SysDictItem
from app.modules.repository.models.archive import Archive
from app.modules.repository.models.fonds import Fonds

# 《档案法》第二十七条：档案自形成之日起满二十五年向社会开放
OPEN_APPRAISAL_YEARS = 25

# 旧数据英文存值兜底映射
LEGACY_BGQX_YEARS: dict[str, Optional[int]] = {
    "permanent": None,
    "long": 30,
    "short": 10,
}


class DueArchive:
    """到期待鉴定档案（圈定结果的一行）。"""

    __slots__ = ("archive", "base_date", "years", "due_basis")

    def __init__(self, archive: Archive, base_date: date, years: int, basis_label: str):
        self.archive = archive
        self.base_date = base_date
        self.years = years
        self.due_basis = f"{basis_label} {base_date.isoformat()} + {years}年"


class ScopeService:
    """到期圈定：扫描正式库，筛出已到开放鉴定时间的档案。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_bgqx_years(self) -> dict[str, Optional[int]]:
        """BGQX 字典值 → 年数（None=永久）。叠加旧英文值兜底。"""
        rows = (
            (
                await self.db.execute(
                    select(SysDictItem.item_value).where(
                        SysDictItem.dict_type == "BGQX",
                        SysDictItem.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        mapping: dict[str, Optional[int]] = dict(LEGACY_BGQX_YEARS)
        for value in rows:
            m = re.search(r"(\d+)", value)
            mapping[value] = int(m.group(1)) if m else None
        return mapping

    async def find_due_archives(
        self, tenant_id: Optional[uuid.UUID], fonds_id: Optional[uuid.UUID] = None
    ) -> list[DueArchive]:
        """全量扫描到期档案（排除已在进行中鉴定任务里的档案）。"""
        years_map = await self.load_bgqx_years()
        in_progress = await self._archive_ids_in_active_tasks(tenant_id)

        stmt = select(Archive).where(
            Archive.is_deleted.is_(False),
            Archive.status.in_(["archived", "active"]),
        )
        if tenant_id:
            stmt = stmt.where(Archive.tenant_id == tenant_id)
        if fonds_id:
            stmt = stmt.where(Archive.fonds_id == fonds_id)

        today = date.today()
        due: list[DueArchive] = []
        for archive in (await self.db.execute(stmt)).scalars():
            if archive.id in in_progress:
                continue
            result = self._evaluate_due(archive, years_map, today)
            if result is not None:
                due.append(result)
        return due

    async def _archive_ids_in_active_tasks(
        self, tenant_id: Optional[uuid.UUID]
    ) -> set[uuid.UUID]:
        """已挂在未完结任务（approved 之外）里的档案，不重复圈定。"""
        stmt = (
            select(AppraisalItem.archive_id)
            .join(AppraisalTask, AppraisalItem.task_id == AppraisalTask.id)
            .where(
                AppraisalItem.is_deleted.is_(False),
                AppraisalTask.is_deleted.is_(False),
                AppraisalTask.status != "approved",
            )
        )
        if tenant_id:
            stmt = stmt.where(AppraisalItem.tenant_id == tenant_id)
        return set((await self.db.execute(stmt)).scalars().all())

    def _evaluate_due(
        self,
        archive: Archive,
        years_map: dict[str, Optional[int]],
        today: date,
    ) -> Optional[DueArchive]:
        base_date, basis_label = self._base_date(archive)
        if base_date is None:
            return None

        years = years_map.get(archive.BGQX, None) if archive.BGQX else None
        if years is None:
            # 永久 / 未知期限：按满 25 年进入开放鉴定
            years = OPEN_APPRAISAL_YEARS

        try:
            due_date = base_date.replace(year=base_date.year + years)
        except ValueError:  # 2 月 29 日 + N 年
            due_date = base_date.replace(year=base_date.year + years, day=28)

        if due_date > today:
            return None
        return DueArchive(archive, base_date, years, basis_label)

    @staticmethod
    def _base_date(archive: Archive) -> tuple[Optional[date], str]:
        """基准日：JDRQ → WJRQ → ND 年末 → 归档时间。"""
        parsed = _parse_partial_date(archive.JDRQ)
        if parsed:
            return parsed, "上次鉴定"
        parsed = _parse_partial_date(archive.WJRQ)
        if parsed:
            return parsed, "成文日期"
        if archive.ND:
            return date(archive.ND, 12, 31), "年度"
        if isinstance(archive.create_time, datetime):
            return archive.create_time.date(), "归档时间"
        return None, ""

    async def group_by_fonds(
        self, due: list[DueArchive], tenant_id: Optional[uuid.UUID]
    ) -> list[dict]:
        """按全宗分组统计（圈定预览）。"""
        counts: dict[uuid.UUID, int] = {}
        for d in due:
            counts[d.archive.fonds_id] = counts.get(d.archive.fonds_id, 0) + 1
        if not counts:
            return []

        stmt = select(Fonds).where(
            Fonds.id.in_(counts.keys()), Fonds.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(Fonds.tenant_id == tenant_id)
        fonds_rows = (await self.db.execute(stmt)).scalars().all()
        return [
            {
                "fonds_id": f.id,
                "QZH": f.fonds_code,
                "fonds_name": f.name,
                "due_count": counts[f.id],
            }
            for f in sorted(fonds_rows, key=lambda f: f.fonds_code)
        ]


def _parse_partial_date(value: Optional[str]) -> Optional[date]:
    """解析 YYYY-MM-DD / YYYY-MM / YYYY；月日缺失按该年(月)末补齐。"""
    if not value:
        return None
    value = value.strip()
    for fmt, builder in (
        (r"^(\d{4})-(\d{1,2})-(\d{1,2})$", lambda y, m, d: date(y, m, d)),
        (
            r"^(\d{4})-(\d{1,2})$",
            lambda y, m, _: date(y, m, calendar.monthrange(y, m)[1]),
        ),
        (r"^(\d{4})$", lambda y, *_: date(y, 12, 31)),
    ):
        match = re.match(fmt, value)
        if match:
            parts = [int(g) for g in match.groups() if g is not None]
            while len(parts) < 3:
                parts.append(0)
            try:
                return builder(*parts)
            except ValueError:
                return None
    return None
