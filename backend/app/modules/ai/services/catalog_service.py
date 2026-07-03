"""智能著录 - 比对、候选列表、写入、审计。

- 抽取结果 vs 当前条目 → 逐字段建议（补足/更正/保持），≥阈值自动预勾选
- 候选列表：有原文(full_text)的档案，标注完整度与状态
- 写入：用户确认后回写暂存库/正式库 + ES 同步 + 审计留痕
"""

import difflib
import logging
import uuid
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models.catalog_log import AiCatalogLog
from app.modules.ai.services import catalog_extract_service as extract
from app.modules.ai.services.catalog_extract_service import BASE_COLUMNS
from app.modules.repository.models.archive import Archive, ArchiveStaging
from app.modules.repository.models.category import ArchiveCategory

logger = logging.getLogger(__name__)

DEFAULT_THRESHOLD = 80
THRESHOLD_DICT_TYPE = "AI_CATALOG_CONFIG"


def _model(doc_source: str):
    return ArchiveStaging if doc_source == "staging" else Archive


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a or "", b or "").ratio()


# ── 阈值（系统可配，存 sys_dict）────────────────────────────────────────────────
async def get_threshold(db: AsyncSession) -> int:
    from app.modules.iam.models.dict import SysDictItem

    row = (
        await db.execute(
            select(SysDictItem.item_value)
            .where(
                SysDictItem.dict_type == THRESHOLD_DICT_TYPE,
                SysDictItem.is_deleted.is_(False),
            )
            .order_by(SysDictItem.sort_order)
            .limit(1)
        )
    ).scalar_one_or_none()
    try:
        v = int(row)
        return min(100, max(0, v))
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD


# ── 门类 schema / 当前条目取值 ──────────────────────────────────────────────────
async def category_schema(db: AsyncSession, category_id) -> list[dict]:
    if not category_id:
        return []
    cat = (
        await db.execute(select(ArchiveCategory).where(ArchiveCategory.id == category_id))
    ).scalars().first()
    return extract.compact_schema(cat.field_schema if cat else None)


def archive_values(archive, schema: list[dict]) -> dict[str, str]:
    ext = archive.ext_fields or {}
    vals: dict[str, str] = {}
    for f in schema:
        name = f["name"]
        if name in BASE_COLUMNS and hasattr(archive, name):
            v = getattr(archive, name)
        else:
            v = ext.get(name)
        vals[name] = "" if v is None else str(v)
    return vals


# ── 比对 → 建议 ────────────────────────────────────────────────────────────────
def build_suggestions(
    schema: list[dict],
    current: dict[str, str],
    extracted: dict[str, dict],
    threshold: int,
) -> list[dict]:
    out: list[dict] = []
    for f in schema:
        name = f["name"]
        ext = extracted.get(name) or {}
        sval = (ext.get("value") or "").strip()
        conf = int(ext.get("confidence") or 0)
        cur = (current.get(name) or "").strip()

        sim: Optional[int] = None
        if not sval:
            kind, preselect = "none", False
        elif not cur:
            kind, preselect = "fill", conf >= threshold
        else:
            sim = round(_similarity(cur, sval) * 100)
            if sim >= 95:
                kind, preselect = "keep", False
            else:
                kind, preselect = "correct", conf >= threshold

        out.append(
            {
                "name": name,
                "label": f["label"],
                "type": f["type"],
                "required": f["required"],
                "options": f["options"],
                "current": cur,
                "suggested": sval,
                "confidence": conf,
                "evidence": ext.get("evidence", ""),
                "similarity": sim,
                "kind": kind,  # none | fill | correct | keep
                "preselect": preselect,
                "changed": kind in ("fill", "correct"),
            }
        )
    return out


async def suggest(
    db: AsyncSession, archive_id: uuid.UUID, doc_source: str, user_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> dict:
    model = _model(doc_source)
    stmt = select(model).where(model.id == archive_id, model.is_deleted.is_(False))
    if tenant_id:
        stmt = stmt.where(model.tenant_id == tenant_id)
    archive = (await db.execute(stmt)).scalars().first()
    if archive is None:
        return {"ok": False, "reason": "档案不存在"}

    schema = await category_schema(db, archive.category_id)
    current = archive_values(archive, schema)
    threshold = await get_threshold(db)
    info = {"id": str(archive.id), "DH": archive.DH, "TM": archive.TM,
            "doc_source": doc_source}

    full_text = (getattr(archive, "full_text", None) or "").strip()
    if not full_text:
        # 无识别全文：返回纯手动编辑表单（无 AI 建议），前端可就地 OCR 后重新分析
        return {
            "ok": True,
            "need_ocr": True,
            "threshold": threshold,
            "archive": info,
            "full_text": "",
            "suggestions": build_suggestions(schema, current, {}, threshold),
        }

    extracted = await _cached_extract(
        db, archive.id, full_text, _raw_schema(schema), current, str(user_id), tenant_id
    )
    suggestions = build_suggestions(schema, current, extracted, threshold)
    return {
        "ok": True,
        "threshold": threshold,
        "archive": info,
        "full_text": full_text,
        "suggestions": suggestions,
    }


async def _cached_extract(
    db: AsyncSession, archive_id, full_text: str, raw_schema: list[dict],
    current: dict, user_id: str, tenant_id,
) -> dict:
    """抽取结果按 full_text 哈希缓存：原文没变就复用，不再重跑 Dify。"""
    import hashlib

    from app.modules.ai.models.catalog_extract import CatalogExtractCache

    h = hashlib.sha256((full_text or "").encode("utf-8")).hexdigest()
    row = (
        await db.execute(
            select(CatalogExtractCache)
            .where(
                CatalogExtractCache.archive_id == archive_id,
                CatalogExtractCache.is_deleted.is_(False),
            )
            .order_by(CatalogExtractCache.create_time.desc())
            .limit(1)
        )
    ).scalars().first()
    if row and row.text_hash == h and row.data:
        return row.data  # 命中缓存，跳过 Dify

    extracted = await extract.extract_from_text(full_text, raw_schema, current, user_id)
    if row:
        row.is_deleted = True
    db.add(
        CatalogExtractCache(
            archive_id=archive_id, text_hash=h, data=extracted, tenant_id=tenant_id
        )
    )
    await db.commit()
    return extracted


def _raw_schema(compact: list[dict]) -> list[dict]:
    # extract_from_text 内部会再 compact，这里把 options 还原成定义形态即可直接复用
    return [
        {**c, "options": [{"value": o, "label": o} for o in (c.get("options") or [])]}
        for c in compact
    ]


# ── 写入（确认后回写）──────────────────────────────────────────────────────────
def _coerce(name: str, value: str):
    if value == "" or value is None:
        return None
    if name in ("ND", "YS"):
        try:
            return int(str(value).strip())
        except ValueError:
            return None
    return value


async def apply(
    db: AsyncSession, archive_id: uuid.UUID, doc_source: str,
    adopted: dict[str, str], user_id: uuid.UUID, tenant_id: Optional[uuid.UUID],
) -> dict:
    model = _model(doc_source)
    stmt = select(model).where(model.id == archive_id, model.is_deleted.is_(False))
    if tenant_id:
        stmt = stmt.where(model.tenant_id == tenant_id)
    archive = (await db.execute(stmt)).scalars().first()
    if archive is None:
        return {"ok": False, "reason": "档案不存在"}

    ext = dict(archive.ext_fields or {})
    changes: dict[str, dict] = {}
    had_value = False
    for name, value in (adopted or {}).items():
        old = getattr(archive, name, None) if name in BASE_COLUMNS else ext.get(name)
        new = _coerce(name, value)
        if name in BASE_COLUMNS and hasattr(archive, name):
            setattr(archive, name, new)
        else:
            ext[name] = new
        if (old or "") != "":
            had_value = True
        changes[name] = {"old": "" if old is None else str(old), "new": value}
    archive.ext_fields = ext
    await db.flush()

    log = AiCatalogLog(
        archive_id=archive.id,
        doc_source=doc_source,
        action="correct" if had_value else "fill",
        archive_dh=archive.DH,
        archive_tm=archive.TM,
        changes=changes,
        operator_id=user_id,
        tenant_id=tenant_id,
        create_by=user_id,
    )
    db.add(log)
    await db.commit()

    try:
        from app.modules.repository.services.es_sync_service import sync_one
        await sync_one(archive)
    except Exception:  # noqa: BLE001
        logger.warning("智能著录写入后 ES 同步失败 archive=%s", archive.id)
    return {"ok": True, "changed": len(changes)}


async def log_ingest(
    db: AsyncSession, archive, adopted_meta: dict, user_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID],
) -> None:
    db.add(
        AiCatalogLog(
            archive_id=archive.id,
            doc_source="staging",
            action="ingest",
            archive_dh=archive.DH,
            archive_tm=archive.TM,
            changes=adopted_meta or {},
            operator_id=user_id,
            tenant_id=tenant_id,
            create_by=user_id,
        )
    )


# ── 候选列表 ────────────────────────────────────────────────────────────────────
async def _required_map(db: AsyncSession) -> dict[Any, list[str]]:
    cats = (await db.execute(select(ArchiveCategory))).scalars().all()
    out: dict[Any, list[str]] = {}
    for c in cats:
        out[c.id] = [
            f.get("name")
            for f in (c.field_schema or [])
            if isinstance(f, dict) and f.get("required") and f.get("name")
        ]
    return out


def _completeness(archive, required: list[str]) -> tuple[int, int]:
    if not required:
        return (0, 0)
    ext = archive.ext_fields or {}
    filled = 0
    for name in required:
        v = getattr(archive, name, None) if name in BASE_COLUMNS else ext.get(name)
        if v not in (None, ""):
            filled += 1
    return (filled, len(required))


async def list_candidates(
    db: AsyncSession, tenant_id: Optional[uuid.UUID], doc_source: str = "all",
    only_issues: bool = False, skip: int = 0, limit: int = 50,
) -> dict:
    required = await _required_map(db)
    sources = ["staging", "formal"] if doc_source == "all" else [doc_source]
    items: list[dict] = []
    for src in sources:
        model = _model(src)
        # 全部档案都列出来（没原文的也显示，只是「查看原文/AI 著录」置灰）
        stmt = select(model).where(model.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(model.tenant_id == tenant_id)
        rows = (await db.execute(stmt.order_by(model.update_time.desc()))).scalars().all()
        for a in rows:
            filled, total = _completeness(a, required.get(a.category_id, []))
            items.append(
                {
                    "id": str(a.id), "_uid": a.id, "doc_source": src, "DH": a.DH, "TM": a.TM,
                    "QZH": a.QZH, "ND": a.ND, "category_id": str(a.category_id) if a.category_id else None,
                    "filled": filled, "total": total,
                    "_has_text": bool((a.full_text or "").strip()),
                }
            )

    # 附件数（数字化成果原文）——没附件=无原文，决定「查看原文/AI 著录」是否可点
    counts = await _attachment_counts(db, [it["_uid"] for it in items])
    result_items: list[dict] = []
    for it in items:
        ac = counts.get(it.pop("_uid"), 0)
        has_text = it.pop("_has_text")
        if not ac:
            status = "no_source"          # 无原文：不能查看原文、不能 AI 著录
        elif not has_text:
            status = "need_ocr"           # 有原文未识别：先 OCR
        elif it["filled"] == 0:
            status = "empty"
        elif it["total"] and it["filled"] < it["total"]:
            status = "missing"
        else:
            status = "complete"
        # 仅看待处理：排除无原文（无法著录）与已完整（无需著录）
        if only_issues and status in ("complete", "no_source"):
            continue
        it["attachment_count"] = ac
        it["status"] = status
        result_items.append(it)

    total = len(result_items)
    return {"total": total, "items": result_items[skip : skip + limit]}


async def suggest_next_dh(
    db: AsyncSession, category_id, tenant_id: Optional[uuid.UUID]
) -> str:
    """该门类最后一条档案的档号，末位数字 +1（用户可改）。无则返回空。"""
    import re

    if not category_id:
        return ""
    dhs: list[str] = []
    for model in (Archive, ArchiveStaging):
        stmt = select(model.DH).where(
            model.category_id == category_id,
            model.is_deleted.is_(False),
            model.DH.isnot(None),
        )
        if tenant_id:
            stmt = stmt.where(model.tenant_id == tenant_id)
        dhs += [r for (r,) in (await db.execute(stmt)).all() if r]
    if not dhs:
        return ""

    def trailing(s: str):
        m = re.search(r"(\d+)(?!.*\d)", s)
        return int(m.group(1)) if m else -1

    last = max(dhs, key=trailing)
    m = re.search(r"(\d+)(?!.*\d)", last)
    if not m:
        return last
    width = len(m.group(1))
    nxt = str(int(m.group(1)) + 1).zfill(width)
    return last[: m.start(1)] + nxt + last[m.end(1) :]


async def _attachment_counts(db: AsyncSession, ids: list) -> dict:
    from app.modules.repository.models.archive import ArchiveAttachment

    if not ids:
        return {}
    rows = await db.execute(
        select(ArchiveAttachment.archive_id, func.count())
        .where(
            ArchiveAttachment.archive_id.in_(ids),
            ArchiveAttachment.is_deleted.is_(False),
        )
        .group_by(ArchiveAttachment.archive_id)
    )
    return {r[0]: r[1] for r in rows.all()}
