"""四性检测：方案 CRUD + 检测运行编排 + 人工判定。"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone, date
from typing import Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.preservation.models.run import DetectionBatch, DetectionResultItem, DetectionRun
from app.modules.preservation.models.scheme import CheckItem, DetectionScheme, SchemeItem
from app.modules.preservation.schemas.scheme import SchemeCreate, SchemeItemIn, SchemeUpdate
from app.modules.preservation.services import detection_engine


class PreservationService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── 检测项目录 ────────────────────────────────────────────────
    async def list_check_items(self) -> list[CheckItem]:
        return list((await self._db.execute(
            select(CheckItem).where(CheckItem.enabled == True).order_by(CheckItem.dimension, CheckItem.code)  # noqa: E712
        )).scalars().all())

    # ── 方案 ──────────────────────────────────────────────────────
    def _scope(self, tenant_id):
        conds = [DetectionScheme.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(DetectionScheme.tenant_id == tenant_id)
        return conds

    async def list_schemes(self, tenant_id) -> list[dict]:
        schemes = list((await self._db.execute(
            select(DetectionScheme).where(and_(*self._scope(tenant_id))).order_by(DetectionScheme.is_default.desc(), DetectionScheme.create_time.desc())
        )).scalars().all())
        counts = dict((await self._db.execute(
            select(SchemeItem.scheme_id, func.count()).where(SchemeItem.is_deleted == False).group_by(SchemeItem.scheme_id)  # noqa: E712
        )).all())
        out = []
        for s in schemes:
            d = {c: getattr(s, c) for c in ("id", "name", "description", "carrier_type", "is_default", "version", "status", "create_time")}
            d["item_count"] = counts.get(s.id, 0)
            out.append(d)
        return out

    async def get_scheme(self, scheme_id, tenant_id) -> DetectionScheme:
        s = (await self._db.execute(
            select(DetectionScheme).where(and_(DetectionScheme.id == scheme_id, *self._scope(tenant_id)))
        )).scalar_one_or_none()
        if not s:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message="检测方案不存在")
        return s

    async def scheme_items_enriched(self, scheme_id) -> list[dict]:
        items = list((await self._db.execute(
            select(SchemeItem).where(SchemeItem.scheme_id == scheme_id, SchemeItem.is_deleted == False)  # noqa: E712
            .order_by(SchemeItem.sort_order)
        )).scalars().all())
        catalog = {c.code: c for c in (await self._db.execute(select(CheckItem))).scalars().all()}
        out = []
        for it in items:
            meta = catalog.get(it.check_code)
            out.append({
                "id": it.id, "check_code": it.check_code, "enabled": it.enabled,
                "weight": it.weight, "is_blocking": it.is_blocking, "params": it.params, "sort_order": it.sort_order,
                "check_name": meta.name if meta else it.check_code,
                "dimension": meta.dimension if meta else None,
                "exec_type": meta.exec_type if meta else None,
                "standard_ref": meta.standard_ref if meta else None,
            })
        return out

    async def create_scheme(self, data: SchemeCreate, tenant_id) -> DetectionScheme:
        if data.is_default:
            await self._db.execute(update(DetectionScheme).where(and_(*self._scope(tenant_id))).values(is_default=False))
        scheme = DetectionScheme(
            name=data.name, description=data.description, carrier_type=data.carrier_type,
            is_default=data.is_default, version=1, status="active", tenant_id=tenant_id,
        )
        self._db.add(scheme)
        await self._db.flush()
        self._add_items(scheme.id, data.items, tenant_id)
        await self._db.flush()
        return scheme

    async def update_scheme(self, scheme_id, data: SchemeUpdate, tenant_id) -> DetectionScheme:
        scheme = await self.get_scheme(scheme_id, tenant_id)
        if data.name is not None:
            scheme.name = data.name
        if data.description is not None:
            scheme.description = data.description
        if data.status is not None:
            scheme.status = data.status
        if data.items is not None:
            await self._db.execute(
                update(SchemeItem).where(SchemeItem.scheme_id == scheme_id).values(is_deleted=True)
            )
            self._add_items(scheme_id, data.items, tenant_id)
            scheme.version = (scheme.version or 1) + 1
        await self._db.flush()
        return scheme

    async def set_default(self, scheme_id, tenant_id) -> DetectionScheme:
        scheme = await self.get_scheme(scheme_id, tenant_id)
        await self._db.execute(update(DetectionScheme).where(and_(*self._scope(tenant_id))).values(is_default=False))
        scheme.is_default = True
        await self._db.flush()
        return scheme

    async def delete_scheme(self, scheme_id, tenant_id) -> None:
        scheme = await self.get_scheme(scheme_id, tenant_id)
        scheme.is_deleted = True
        await self._db.flush()

    def _add_items(self, scheme_id, items: list[SchemeItemIn], tenant_id) -> None:
        for i, it in enumerate(items):
            self._db.add(SchemeItem(
                scheme_id=scheme_id, check_code=it.check_code, enabled=it.enabled,
                params=it.params, weight=it.weight if it.weight is not None else 10,
                is_blocking=bool(it.is_blocking), sort_order=it.sort_order or i,
            ))

    # ── 运行检测（每次=一个批次） ────────────────────────────────
    async def _new_batch(self, scheme, scope_type, scope_label, operator_id, tenant_id) -> DetectionBatch:
        start = datetime.combine(date.today(), datetime.min.time(), tzinfo=timezone.utc)
        seq = (await self._db.execute(
            select(func.count()).select_from(DetectionBatch).where(DetectionBatch.create_time >= start)
        )).scalar_one()
        batch = DetectionBatch(
            batch_no=f"SX{date.today():%Y%m%d}{seq + 1:03d}", scope_type=scope_type, scope_label=scope_label,
            scheme_id=scheme.id, scheme_name=scheme.name, status="done",
            operator_id=operator_id, tenant_id=tenant_id, started_at=datetime.now(timezone.utc),
            create_by=operator_id,
        )
        self._db.add(batch)
        await self._db.flush()
        return batch

    async def run_single(self, archive_id, scheme_id, operator_id, tenant_id) -> DetectionBatch:
        scheme = await self._resolve_scheme(scheme_id, tenant_id)
        batch = await self._new_batch(scheme, "single", None, operator_id, tenant_id)
        try:
            run = await detection_engine.run_scheme(
                self._db, archive_id=archive_id, scheme=scheme,
                operator_id=operator_id, tenant_id=tenant_id, batch_id=batch.id,
            )
        except ValueError as exc:
            raise NotFoundException(code=ErrorCode.ARCHIVE_NOT_FOUND, message=str(exc))
        batch.scope_label = run.target_label
        await self._aggregate_batch(batch)
        return batch

    async def run_batch(self, *, scheme_id, fonds_id, catalog_id, category_id, nd, operator_id, tenant_id) -> DetectionBatch:
        from app.modules.repository.models.archive import ArchiveStaging
        if not any([fonds_id, catalog_id, category_id, nd]):
            raise ValidationException(message="请至少指定 全宗 / 目录 / 门类 / 年度 之一")
        scheme = await self._resolve_scheme(scheme_id, tenant_id)

        conds = [ArchiveStaging.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(ArchiveStaging.tenant_id == tenant_id)
        if fonds_id:
            conds.append(ArchiveStaging.fonds_id == fonds_id)
        if catalog_id:
            conds.append(ArchiveStaging.catalog_id == catalog_id)
        if category_id:
            conds.append(ArchiveStaging.category_id == category_id)
        if nd is not None:
            conds.append(ArchiveStaging.ND == nd)
        ids = list((await self._db.execute(
            select(ArchiveStaging.id).where(and_(*conds)).limit(2000)
        )).scalars().all())

        scope_type, scope_label = await self._resolve_scope(fonds_id, catalog_id, category_id, nd)
        batch = await self._new_batch(scheme, scope_type, scope_label, operator_id, tenant_id)
        for aid in ids:
            await detection_engine.run_scheme(
                self._db, archive_id=aid, scheme=scheme,
                operator_id=operator_id, tenant_id=tenant_id, batch_id=batch.id,
            )
        await self._aggregate_batch(batch)
        return batch

    async def _resolve_scope(self, fonds_id, catalog_id, category_id, nd) -> tuple[str, str]:
        """把筛选条件翻成客户能看懂的具体范围名，例如：
        全宗 J001·机关文书 ＞ 目录 2021-WS-01·会议纪要 ＞ 2021年度。
        scope_type 取最细一级（catalog > category > fonds > year）。"""
        from app.modules.repository.models.archive import Catalog
        from app.modules.repository.models.category import ArchiveCategory
        from app.modules.repository.models.fonds import Fonds

        parts: list[str] = []
        if fonds_id:
            f = (await self._db.execute(select(Fonds).where(Fonds.id == fonds_id))).scalar_one_or_none()
            if f:
                parts.append(f"全宗 {f.fonds_code}·{f.name}")
        if category_id:
            c = (await self._db.execute(select(ArchiveCategory).where(ArchiveCategory.id == category_id))).scalar_one_or_none()
            if c:
                parts.append(f"门类 {c.code}·{c.name}")
        if catalog_id:
            cat = (await self._db.execute(select(Catalog).where(Catalog.id == catalog_id))).scalar_one_or_none()
            if cat:
                parts.append(f"目录 {cat.catalog_no}·{cat.name}")
        if nd is not None:
            parts.append(f"{nd}年度")

        scope_type = "catalog" if catalog_id else "category" if category_id else "fonds" if fonds_id else "year"
        return scope_type, " ＞ ".join(parts) or "全部暂存档案"

    async def _aggregate_batch(self, batch: DetectionBatch) -> None:
        runs = list((await self._db.execute(
            select(DetectionRun).where(DetectionRun.batch_id == batch.id, DetectionRun.is_deleted == False)  # noqa: E712
        )).scalars().all())
        c = {"pass": 0, "warn": 0, "fail": 0, "pending": 0}
        dim_acc: dict[str, list[float]] = {}
        score_sum = 0.0
        for r in runs:
            c[r.conclusion] = c.get(r.conclusion, 0) + 1
            score_sum += r.overall_score
            for d, v in (r.dim_scores or {}).items():
                dim_acc.setdefault(d, []).append(v)
        n = len(runs)
        batch.total = n
        batch.passed, batch.warned, batch.failed, batch.pending = c["pass"], c["warn"], c["fail"], c["pending"]
        batch.avg_score = round(score_sum / n, 1) if n else 0.0
        batch.dim_scores = {d: round(sum(v) / len(v), 1) for d, v in dim_acc.items()}
        batch.conclusion = "fail" if c["fail"] else "pending" if c["pending"] else "warn" if c["warn"] else "pass"
        batch.finished_at = datetime.now(timezone.utc)
        await self._db.flush()

    async def list_batches(self, tenant_id) -> list[DetectionBatch]:
        conds = [DetectionBatch.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(DetectionBatch.tenant_id == tenant_id)
        return list((await self._db.execute(
            select(DetectionBatch).where(and_(*conds)).order_by(DetectionBatch.create_time.desc()).limit(500)
        )).scalars().all())

    async def get_batch(self, batch_id, tenant_id) -> tuple[DetectionBatch, list[DetectionRun]]:
        conds = [DetectionBatch.id == batch_id, DetectionBatch.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(DetectionBatch.tenant_id == tenant_id)
        batch = (await self._db.execute(select(DetectionBatch).where(and_(*conds)))).scalar_one_or_none()
        if not batch:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message="检测批次不存在")
        runs = list((await self._db.execute(
            select(DetectionRun).where(DetectionRun.batch_id == batch_id).order_by(DetectionRun.create_time)
        )).scalars().all())
        return batch, runs

    async def _resolve_scheme(self, scheme_id, tenant_id) -> DetectionScheme:
        if scheme_id:
            return await self.get_scheme(scheme_id, tenant_id)
        scheme = (await self._db.execute(
            select(DetectionScheme).where(and_(DetectionScheme.is_default == True, *self._scope(tenant_id))).limit(1)  # noqa: E712
        )).scalar_one_or_none()
        if not scheme:
            raise ValidationException(message="未配置默认检测方案，请先创建或指定方案")
        return scheme

    async def list_runs(self, tenant_id, target_id: Optional[uuid.UUID] = None) -> list[DetectionRun]:
        conds = [DetectionRun.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(DetectionRun.tenant_id == tenant_id)
        if target_id:
            conds.append(DetectionRun.target_id == target_id)
        return list((await self._db.execute(
            select(DetectionRun).where(and_(*conds)).order_by(DetectionRun.create_time.desc()).limit(500)
        )).scalars().all())

    async def get_run(self, run_id, tenant_id) -> tuple[DetectionRun, list[DetectionResultItem]]:
        conds = [DetectionRun.id == run_id, DetectionRun.is_deleted == False]  # noqa: E712
        if tenant_id is not None:
            conds.append(DetectionRun.tenant_id == tenant_id)
        run = (await self._db.execute(select(DetectionRun).where(and_(*conds)))).scalar_one_or_none()
        if not run:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message="检测记录不存在")
        results = list((await self._db.execute(
            select(DetectionResultItem).where(DetectionResultItem.run_id == run_id).order_by(DetectionResultItem.dimension)
        )).scalars().all())
        return run, results

    async def decide_manual(self, run_id, item_id, result, message, user_id, tenant_id) -> DetectionRun:
        run, results = await self.get_run(run_id, tenant_id)
        item = next((r for r in results if r.id == item_id), None)
        if not item:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message="检测明细不存在")
        item.result = result
        item.score = {"pass": 100.0, "warn": 60.0, "fail": 0.0}.get(result, 0.0)
        item.message = message or item.message
        item.decided_by = user_id
        await self._db.flush()
        await self._recompute(run, results)
        if run.batch_id:
            batch = (await self._db.execute(
                select(DetectionBatch).where(DetectionBatch.id == run.batch_id)
            )).scalar_one_or_none()
            if batch:
                await self._aggregate_batch(batch)
        return run

    async def _recompute(self, run: DetectionRun, results: list[DetectionResultItem]) -> None:
        dim_acc: dict[str, list[tuple[float, int]]] = {}
        all_acc: list[tuple[float, int]] = []
        passed = warned = failed = manual_pending = blocking_fail = 0
        for r in results:
            if r.result == "pass":
                passed += 1
            elif r.result == "warn":
                warned += 1
            elif r.result == "fail":
                failed += 1
                if r.is_blocking:
                    blocking_fail += 1
            elif r.result == "manual_pending":
                manual_pending += 1
            if r.result in ("pass", "warn", "fail"):
                dim_acc.setdefault(r.dimension, []).append((r.score, r.weight))
                all_acc.append((r.score, r.weight))

        def wavg(acc):
            tw = sum(w for _, w in acc)
            return round(sum(s * w for s, w in acc) / tw, 1) if tw else 0.0

        run.dim_scores = {d: wavg(a) for d, a in dim_acc.items()}
        run.overall_score = wavg(all_acc)
        run.passed, run.warned, run.failed, run.manual_pending = passed, warned, failed, manual_pending
        run.conclusion = "fail" if (blocking_fail or failed) else "pending" if manual_pending else "warn" if warned else "pass"
        await self._db.flush()
