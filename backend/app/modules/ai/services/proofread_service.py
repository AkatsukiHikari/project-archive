"""智能校对 - 批量条目-原文比对。

按检索范围圈定「有 PDF 原文挂接」的档案，后台逐条比对条目著录值与原文全文：
- 复用智能著录抽取工作流（DIFY_CATALOG_WORKFLOW_KEY）+ CatalogExtractCache 哈希缓存，
  原文没变的条目不重复调 Dify（增量天然免费）
- 无 full_text 的条目自动先补一次 OCR，补不出标「无原文」
- 结论落 ai_proofread_item（每条档案以最新一次为有效），批次完成发站内通知
"""

import asyncio
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.ai.models.proofread import AiProofreadBatch, AiProofreadItem
from app.modules.ai.services import catalog_service
from app.modules.repository.models.archive import (Archive, ArchiveAttachment,
                                                   ArchiveStaging)
from app.modules.repository.repositories.archive_repo import ArchiveRepository
from app.modules.repository.schemas.archive import ArchiveListQuery

logger = logging.getLogger(__name__)

CONCURRENCY = 3  # 单批次同时比对的条目数（每条一次 Dify 调用）

# 需要整改的建议类型：fill=原文有依据但条目缺录，correct=条目与原文不一致（疑错录）
ISSUE_KINDS = ("fill", "correct")
ISSUE_FIELDS = (
    "name",
    "label",
    "kind",
    "current",
    "suggested",
    "confidence",
    "evidence",
    "similarity",
)


def _model(doc_source: str):
    return ArchiveStaging if doc_source == "staging" else Archive


def _sources(doc_source: str) -> list[str]:
    return ["staging", "formal"] if doc_source == "all" else [doc_source]


def _pdf_exists(model):
    """该档案存在未删除的 PDF 挂接（原文）。"""
    return exists(
        select(ArchiveAttachment.id).where(
            ArchiveAttachment.archive_id == model.id,
            ArchiveAttachment.is_deleted.is_(False),
            or_(
                ArchiveAttachment.original_name.ilike("%.pdf"),
                func.lower(ArchiveAttachment.file_format) == "pdf",
            ),
        )
    )


def _scope_conditions(query: ArchiveListQuery, tenant_id, model) -> list:
    return ArchiveRepository.build_conditions(query, tenant_id, model=model)


# ── 发起前预检 ─────────────────────────────────────────────────────────────────
async def preview(
    db: AsyncSession,
    query: ArchiveListQuery,
    doc_source: str,
    tenant_id: Optional[uuid.UUID],
) -> dict:
    """当前范围内：档案总数 / 有PDF可校对数 / 其中还需先OCR识别数。"""
    total = with_pdf = with_text = 0
    for src in _sources(doc_source):
        model = _model(src)
        conds = _scope_conditions(query, tenant_id, model)
        total += (
            await db.execute(
                select(func.count()).select_from(model).where(and_(*conds))
            )
        ).scalar_one()
        with_pdf += (
            await db.execute(
                select(func.count())
                .select_from(model)
                .where(and_(*conds), _pdf_exists(model))
            )
        ).scalar_one()
        with_text += (
            await db.execute(
                select(func.count())
                .select_from(model)
                .where(
                    and_(*conds),
                    _pdf_exists(model),
                    func.coalesce(model.full_text, "") != "",
                )
            )
        ).scalar_one()
    return {
        "total": total,
        "with_pdf": with_pdf,
        "need_ocr": with_pdf - with_text,
        "no_pdf": total - with_pdf,
    }


# ── 发起批次 ───────────────────────────────────────────────────────────────────
async def start(
    db: AsyncSession,
    query: ArchiveListQuery,
    doc_source: str,
    scope_label: Optional[str],
    force: bool,
    user_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> dict:
    if not settings.DIFY_CATALOG_WORKFLOW_KEY:
        return {
            "ok": False,
            "reason": "未配置智能著录工作流（DIFY_CATALOG_WORKFLOW_KEY）",
        }

    running_stmt = select(AiProofreadBatch.id).where(
        AiProofreadBatch.status == "running",
        AiProofreadBatch.is_deleted.is_(False),
    )
    if tenant_id:
        running_stmt = running_stmt.where(AiProofreadBatch.tenant_id == tenant_id)
    if (await db.execute(running_stmt.limit(1))).scalar_one_or_none():
        return {"ok": False, "reason": "已有校对任务在运行中，请等待完成或取消后再发起"}

    # 圈定范围内有 PDF 原文挂接的档案
    targets: list[tuple[uuid.UUID, str, Optional[str], Optional[str]]] = []
    for src in _sources(doc_source):
        model = _model(src)
        conds = _scope_conditions(query, tenant_id, model)
        rows = (
            await db.execute(
                select(model.id, model.DH, model.TM).where(
                    and_(*conds), _pdf_exists(model)
                )
            )
        ).all()
        targets += [(r[0], src, r[1], r[2]) for r in rows]

    if not targets:
        return {"ok": False, "reason": "当前范围内没有已挂接 PDF 原文的档案"}

    batch = AiProofreadBatch(
        scope={
            **query.model_dump(mode="json", exclude_none=True),
            "doc_source": doc_source,
            "force": force,
        },
        scope_label=scope_label or "全库",
        doc_source=doc_source,
        total=len(targets),
        status="running",
        operator_id=user_id,
        started_at=datetime.now(timezone.utc),
        tenant_id=tenant_id,
        create_by=user_id,
    )
    db.add(batch)
    await db.flush()
    for aid, src, dh, tm in targets:
        db.add(
            AiProofreadItem(
                batch_id=batch.id,
                archive_id=aid,
                doc_source=src,
                archive_dh=dh,
                archive_tm=tm,
                verdict="pending",
                tenant_id=tenant_id,
                create_by=user_id,
            )
        )
    batch_id = str(batch.id)
    await db.commit()

    asyncio.create_task(run_batch(batch_id))
    return {"ok": True, "batch_id": batch_id, "total": len(targets)}


# ── 后台执行 ───────────────────────────────────────────────────────────────────
async def run_batch(batch_id: str) -> None:
    """后台跑完一个批次（独立 session；单条失败不中断）。"""
    from app.infra.db.session import AsyncSessionLocal

    bid = uuid.UUID(batch_id)
    async with AsyncSessionLocal() as db:
        batch = (
            await db.execute(select(AiProofreadBatch).where(AiProofreadBatch.id == bid))
        ).scalar_one_or_none()
        if batch is None or batch.status != "running":
            return
        force = bool((batch.scope or {}).get("force"))
        operator_id = batch.operator_id
        item_ids = (
            (
                await db.execute(
                    select(AiProofreadItem.id).where(
                        AiProofreadItem.batch_id == bid,
                        AiProofreadItem.verdict == "pending",
                        AiProofreadItem.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )

    sem = asyncio.Semaphore(CONCURRENCY)
    canceled = False

    async def worker(item_id: uuid.UUID) -> None:
        nonlocal canceled
        async with sem:
            if canceled or await _batch_status(bid) != "running":
                canceled = True
                return
            try:
                await _process_item(bid, item_id, operator_id, force)
            except Exception:  # noqa: BLE001 — 单条兜底，正常路径内部已自行落结果
                logger.exception("智能校对：条目处理异常 item=%s", item_id)

    await asyncio.gather(*[worker(i) for i in item_ids])
    await _finalize(bid)


async def _batch_status(batch_id: uuid.UUID) -> str:
    from app.infra.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return (
            await db.execute(
                select(AiProofreadBatch.status).where(AiProofreadBatch.id == batch_id)
            )
        ).scalar_one_or_none() or "missing"


async def _process_item(
    batch_id: uuid.UUID,
    item_id: uuid.UUID,
    operator_id: Optional[uuid.UUID],
    force: bool,
) -> None:
    """比对单条：取全文（必要时自动 OCR）→ 抽取（带缓存）→ 与条目逐字段比对。"""
    from app.infra.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        item = (
            await db.execute(
                select(AiProofreadItem).where(AiProofreadItem.id == item_id)
            )
        ).scalar_one_or_none()
        if item is None:
            return

        verdict, issues, text_hash, error = "failed", [], None, None
        try:
            model = _model(item.doc_source)
            archive = (
                (
                    await db.execute(
                        select(model).where(
                            model.id == item.archive_id, model.is_deleted.is_(False)
                        )
                    )
                )
                .scalars()
                .first()
            )
            if archive is None:
                error = "档案不存在或已删除"
            else:
                full_text = (archive.full_text or "").strip()
                if not full_text:
                    full_text = await _try_ocr(db, archive, item, operator_id)
                if not full_text:
                    verdict, error = "no_text", error or "原文无法识别出文字"
                else:
                    verdict, issues, text_hash = await _compare(
                        db, archive, full_text, operator_id, item.tenant_id, force
                    )
        except Exception as exc:  # noqa: BLE001 — 单条失败只标记该条，不中断批次
            logger.exception("智能校对失败 archive=%s", item.archive_id)
            error = str(exc)[:500]

        item.verdict = verdict
        item.issues = issues or None
        item.issue_count = len(issues)
        item.text_hash = text_hash
        item.error = error
        item.finished_at = datetime.now(timezone.utc)
        counter = {
            "consistent": AiProofreadBatch.consistent,
            "flagged": AiProofreadBatch.flagged,
            "no_text": AiProofreadBatch.no_text,
        }.get(verdict, AiProofreadBatch.failed)
        await db.execute(
            update(AiProofreadBatch)
            .where(AiProofreadBatch.id == batch_id)
            .values(
                processed=AiProofreadBatch.processed + 1, **{counter.key: counter + 1}
            )
        )
        await db.commit()


async def _try_ocr(
    db: AsyncSession, archive, item: AiProofreadItem, operator_id
) -> str:
    """无全文时就地补一次 OCR（文本层提取或 Dify OCR 工作流），失败返回空。"""
    from app.modules.ai.services.ocr_service import OcrService

    try:
        result = await OcrService(db).ocr_archive(
            item.archive_id, operator_id or uuid.uuid4(), item.tenant_id
        )
        if result.get("ok"):
            await db.refresh(archive)
            return (archive.full_text or "").strip()
    except Exception:  # noqa: BLE001 — OCR 失败按「无原文」处理
        logger.warning("智能校对：自动 OCR 失败 archive=%s", item.archive_id)
    return ""


async def _compare(
    db: AsyncSession,
    archive,
    full_text: str,
    operator_id,
    tenant_id,
    force: bool,
) -> tuple[str, list[dict], str]:
    """复用智能著录的抽取+比对：≥阈值的 补录(fill)/更正(correct) 记为存疑项。"""
    schema = await catalog_service.category_schema(db, archive.category_id)
    current = catalog_service.archive_values(archive, schema)
    threshold = await catalog_service.get_threshold(db)
    extracted = await catalog_service._cached_extract(
        db,
        archive.id,
        full_text,
        catalog_service._raw_schema(schema),
        current,
        str(operator_id or ""),
        tenant_id,
        force=force,
    )
    suggestions = catalog_service.build_suggestions(
        schema, current, extracted, threshold
    )
    issues = [
        {k: s.get(k) for k in ISSUE_FIELDS}
        for s in suggestions
        if s["kind"] in ISSUE_KINDS and s["confidence"] >= threshold
        # 枚举字段建议值必须取自合法选项，模型越界输出直接丢弃
        and not (s.get("options") and s.get("suggested") not in s["options"])
    ]
    text_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    return ("flagged" if issues else "consistent"), issues, text_hash


async def _finalize(batch_id: uuid.UUID) -> None:
    from app.infra.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        batch = (
            await db.execute(
                select(AiProofreadBatch).where(AiProofreadBatch.id == batch_id)
            )
        ).scalar_one_or_none()
        if batch is None:
            return
        if batch.status == "running":
            batch.status = "done"
        batch.finished_at = datetime.now(timezone.utc)
        await db.commit()
        await _notify(db, batch)


async def _notify(db: AsyncSession, batch: AiProofreadBatch) -> None:
    """批次结束给发起人发站内通知（带 WS 实时推送）。"""
    if not batch.operator_id:
        return
    try:
        from app.modules.notification.repositories.notification_repository import \
            SQLAlchemyNotificationRepository
        from app.modules.notification.schemas import NotificationCreate
        from app.modules.notification.services.notification_service import \
            NotificationService

        state = "已取消" if batch.status == "canceled" else "完成"
        parts = [
            f"共 {batch.total} 件",
            f"与原文不符待确认 {batch.flagged} 件",
            f"相符 {batch.consistent} 件",
        ]
        if batch.no_text:
            parts.append(f"原文无法识别 {batch.no_text} 件")
        if batch.failed:
            parts.append(f"失败 {batch.failed} 件")
        await NotificationService(
            SQLAlchemyNotificationRepository(db)
        ).create_notification(
            NotificationCreate(
                user_id=batch.operator_id,
                title=f"智能校对{state}",
                content=f"「{batch.scope_label or '全库'}」{('，'.join(parts))}。待确认条目请到智能校对页逐项人工确认。",
                type="system",
                level="warning" if batch.flagged else "info",
                source_type="ai_proofread_batch",
                source_id=str(batch.id),
            )
        )
    except Exception:  # noqa: BLE001 — 通知失败不影响批次结果
        logger.warning("智能校对：完成通知发送失败 batch=%s", batch.id)


# ── 批次查询 / 取消 ────────────────────────────────────────────────────────────
def _batch_out(b: AiProofreadBatch) -> dict:
    return {
        "id": str(b.id),
        "scope_label": b.scope_label,
        "doc_source": b.doc_source,
        "total": b.total,
        "processed": b.processed,
        "consistent": b.consistent,
        "flagged": b.flagged,
        "no_text": b.no_text,
        "failed": b.failed,
        "status": b.status,
        "started_at": b.started_at.isoformat() if b.started_at else None,
        "finished_at": b.finished_at.isoformat() if b.finished_at else None,
    }


async def list_batches(
    db: AsyncSession,
    tenant_id: Optional[uuid.UUID],
    skip: int = 0,
    limit: int = 20,
) -> dict:
    stmt = select(AiProofreadBatch).where(AiProofreadBatch.is_deleted.is_(False))
    if tenant_id:
        stmt = stmt.where(AiProofreadBatch.tenant_id == tenant_id)
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(AiProofreadBatch.create_time.desc())
                .offset(skip)
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return {"total": total, "items": [_batch_out(b) for b in rows]}


async def get_batch(
    db: AsyncSession,
    batch_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> Optional[dict]:
    stmt = select(AiProofreadBatch).where(
        AiProofreadBatch.id == batch_id, AiProofreadBatch.is_deleted.is_(False)
    )
    if tenant_id:
        stmt = stmt.where(AiProofreadBatch.tenant_id == tenant_id)
    b = (await db.execute(stmt)).scalar_one_or_none()
    return _batch_out(b) if b else None


async def cancel(
    db: AsyncSession,
    batch_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> dict:
    stmt = select(AiProofreadBatch).where(
        AiProofreadBatch.id == batch_id, AiProofreadBatch.is_deleted.is_(False)
    )
    if tenant_id:
        stmt = stmt.where(AiProofreadBatch.tenant_id == tenant_id)
    b = (await db.execute(stmt)).scalar_one_or_none()
    if b is None:
        return {"ok": False, "reason": "批次不存在"}
    if b.status != "running":
        return {"ok": False, "reason": "批次已结束，无法取消"}
    b.status = "canceled"
    await db.commit()
    return {"ok": True}


# ── 条目列表（表格）/ 整改 ─────────────────────────────────────────────────────
async def list_records(
    db: AsyncSession,
    query: ArchiveListQuery,
    doc_source: str,
    tenant_id: Optional[uuid.UUID],
    verdict: Optional[str] = None,
) -> dict:
    """范围内档案 + 完整度 + 最新校对结论（内存合并两库，口径与智能著录候选列表一致）。"""
    required = await catalog_service._required_map(db)
    rows_all: list[dict] = []
    for src in _sources(doc_source):
        model = _model(src)
        conds = _scope_conditions(query, tenant_id, model)
        rows = (
            await db.execute(
                select(model, _pdf_exists(model).label("has_pdf")).where(and_(*conds))
            )
        ).all()
        for a, has_pdf in rows:
            filled, total_req = catalog_service._completeness(
                a, required.get(a.category_id, [])
            )
            rows_all.append(
                {
                    "id": str(a.id),
                    "_uid": a.id,
                    "doc_source": src,
                    "DH": a.DH,
                    "TM": a.TM,
                    "QZH": a.QZH,
                    "ND": a.ND,
                    "category_id": str(a.category_id) if a.category_id else None,
                    "filled": filled,
                    "total_required": total_req,
                    "_ut": a.update_time,
                    "has_pdf": bool(has_pdf),
                }
            )
    _epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    rows_all.sort(key=lambda x: x["_ut"] or _epoch, reverse=True)

    # 最新校对结论（全量范围内一次查出，按 archive_id 取最新）
    latest = await _latest_items(db, [r["_uid"] for r in rows_all])
    out: list[dict] = []
    for r in rows_all:
        it = latest.get(r.pop("_uid"))
        r.pop("_ut")
        r["verdict"] = it["verdict"] if it else ("none" if r["has_pdf"] else "no_pdf")
        r["issue_count"] = it["issue_count"] if it else 0
        r["issues"] = it["issues"] if it else None
        r["checked_at"] = it["checked_at"] if it else None
        if verdict and r["verdict"] != verdict:
            continue
        out.append(r)

    total = len(out)
    offset = (query.page - 1) * query.page_size
    return {"total": total, "items": out[offset : offset + query.page_size]}


async def _latest_items(db: AsyncSession, ids: list) -> dict:
    if not ids:
        return {}
    rows = (
        (
            await db.execute(
                select(AiProofreadItem)
                .where(
                    AiProofreadItem.archive_id.in_(ids),
                    AiProofreadItem.verdict != "pending",
                    AiProofreadItem.is_deleted.is_(False),
                )
                .order_by(AiProofreadItem.create_time.desc())
            )
        )
        .scalars()
        .all()
    )
    latest: dict = {}
    for it in rows:
        if it.archive_id in latest:
            continue
        latest[it.archive_id] = {
            "verdict": it.verdict,
            "issue_count": it.issue_count,
            "issues": it.issues,
            "checked_at": it.finished_at.isoformat() if it.finished_at else None,
        }
    return latest


async def resolve(
    db: AsyncSession,
    archive_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> dict:
    """整改完成（用户在著录抽屉确认写库后调用）：最新存疑结果标记已整改。"""
    conds = [
        AiProofreadItem.archive_id == archive_id,
        AiProofreadItem.verdict.in_(["flagged", "consistent"]),
        AiProofreadItem.is_deleted.is_(False),
    ]
    if tenant_id:
        conds.append(AiProofreadItem.tenant_id == tenant_id)
    stmt = (
        select(AiProofreadItem)
        .where(*conds)
        .order_by(AiProofreadItem.create_time.desc())
        .limit(1)
    )
    it = (await db.execute(stmt)).scalar_one_or_none()
    if it is None:
        return {"ok": False, "reason": "该档案暂无校对结果"}
    if it.verdict == "flagged":
        it.verdict = "resolved"
        await db.commit()
    return {"ok": True}
