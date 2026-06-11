"""四性检测引擎：按方案逐项执行 → 维度加权 + 一票否决 → 结论 + 明细。

引擎不认识具体检测项：rule 走注册表实现、ai 走 AI 能力(暂转待检)、manual 进人工待办。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.preservation.models.run import DetectionRun, DetectionResultItem
from app.modules.preservation.models.scheme import CheckItem, DetectionScheme, SchemeItem
from app.modules.preservation.services.checks import builtin  # noqa: F401  注册内置检测项
from app.modules.preservation.services.checks.registry import CHECK_REGISTRY, CheckContext

_DIM_LABEL = {"authenticity": "真实性", "integrity": "完整性", "usability": "可用性", "safety": "安全性"}


async def build_context(db: AsyncSession, archive_id: uuid.UUID) -> tuple[CheckContext, str]:
    """从档案 ID 构建检测上下文（元数据 + 附件元信息），返回 (ctx, 题名/档号 label)。"""
    from app.modules.repository.models.archive import Archive, ArchiveAttachment, ArchiveStaging

    obj = (await db.execute(
        select(ArchiveStaging).where(ArchiveStaging.id == archive_id, ArchiveStaging.is_deleted == False)  # noqa: E712
    )).scalar_one_or_none()
    if obj is None:
        obj = (await db.execute(select(Archive).where(Archive.id == archive_id))).scalars().first()
    if obj is None:
        raise ValueError("档案不存在")

    archive = {f: getattr(obj, f, None) for f in ("TM", "RZZ", "ND", "DH", "QZH", "MJ", "WJRQ", "YS", "BGQX", "ext_fields")}
    atts = (await db.execute(
        select(ArchiveAttachment).where(
            ArchiveAttachment.archive_id == archive_id, ArchiveAttachment.is_deleted == False  # noqa: E712
        )
    )).scalars().all()
    attachments = []
    for a in atts:
        # 真下载原文字节，供固化值重算/格式头校验（失败不阻断，data=None）
        data = None
        try:
            from app.infra.storage.factory import storage
            data = storage.get(a.storage_key, a.storage_bucket)
        except Exception:
            data = None
        attachments.append({
            "original_name": a.original_name, "file_format": a.file_format,
            "sha256_hash": a.sha256_hash, "page_count": a.page_count, "file_size": a.file_size,
            "data": data,
        })
    return CheckContext(archive=archive, attachments=attachments), (archive.get("DH") or archive.get("TM") or "")


async def run_scheme(
    db: AsyncSession, *, archive_id: uuid.UUID, scheme: DetectionScheme,
    operator_id: Optional[uuid.UUID], tenant_id: Optional[uuid.UUID],
    batch_id: Optional[uuid.UUID] = None,
) -> DetectionRun:
    ctx, label = await build_context(db, archive_id)

    # 方案勾选项 + 目录元信息
    items = (await db.execute(
        select(SchemeItem).where(and_(SchemeItem.scheme_id == scheme.id, SchemeItem.enabled == True))  # noqa: E712
        .order_by(SchemeItem.sort_order)
    )).scalars().all()
    catalog = {c.code: c for c in (await db.execute(select(CheckItem))).scalars().all()}

    now = datetime.now(timezone.utc)
    run = DetectionRun(
        batch_id=batch_id,
        target_type="archive", target_id=archive_id, target_label=label[:512],
        scheme_id=scheme.id, scheme_name=scheme.name, scheme_version=scheme.version,
        status="done", operator_id=operator_id, tenant_id=tenant_id,
        started_at=now, finished_at=now, create_by=operator_id,
    )
    db.add(run)
    await db.flush()

    dim_acc: dict[str, list[tuple[float, int]]] = {}   # dimension -> [(score, weight)]
    all_acc: list[tuple[float, int]] = []
    passed = warned = failed = manual_pending = blocking_fail = 0

    for si in items:
        meta = catalog.get(si.check_code)
        if meta is None:
            continue
        params = {**(meta.default_params or {}), **(si.params or {})}
        weight = si.weight or meta.default_weight
        blocking = si.is_blocking if si.is_blocking is not None else meta.default_blocking

        if meta.exec_type == "rule" and si.check_code in CHECK_REGISTRY:
            outcome = CHECK_REGISTRY[si.check_code](ctx, params)
            result = outcome.result
            msg, ev, conf = outcome.message, outcome.evidence, outcome.confidence
            score = outcome.score
        elif meta.exec_type == "ai":
            result, msg, ev, conf, score = "manual_pending", "待 AI 检测（OCR 就绪后自动判定）", {}, None, None
        else:  # manual 或 rule 未实装
            result, msg, ev, conf, score = "manual_pending", "待人工核验", {}, None, None

        db.add(DetectionResultItem(
            run_id=run.id, check_code=si.check_code, check_name=meta.name, dimension=meta.dimension,
            exec_type=meta.exec_type, result=result, score=score or 0.0, weight=weight,
            is_blocking=blocking, message=msg, evidence=ev or None, confidence=conf,
            standard_ref=meta.standard_ref, tenant_id=tenant_id, create_by=operator_id,
        ))

        if result == "pass":
            passed += 1
        elif result == "warn":
            warned += 1
        elif result == "fail":
            failed += 1
            if blocking:
                blocking_fail += 1
        elif result == "manual_pending":
            manual_pending += 1

        if score is not None and result != "skip":
            dim_acc.setdefault(meta.dimension, []).append((score, weight))
            all_acc.append((score, weight))

    def wavg(acc: list[tuple[float, int]]) -> float:
        tw = sum(w for _, w in acc)
        return round(sum(s * w for s, w in acc) / tw, 1) if tw else 0.0

    run.dim_scores = {d: wavg(acc) for d, acc in dim_acc.items()}
    run.overall_score = wavg(all_acc)
    run.total = len(items)
    run.passed, run.warned, run.failed, run.manual_pending = passed, warned, failed, manual_pending
    # 结论：一票否决/任何不通过→不合格;有待人工/AI→待复核;有警告→基本合格;否则合格
    if blocking_fail or failed:
        run.conclusion = "fail"
    elif manual_pending:
        run.conclusion = "pending"
    elif warned:
        run.conclusion = "warn"
    else:
        run.conclusion = "pass"

    await db.flush()
    return run
