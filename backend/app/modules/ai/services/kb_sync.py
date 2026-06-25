"""知识库同步：把档案（元数据 + OCR 全文）推进 Dify 知识库。

仅同步正式库 Archive。增量靠 archive.kb_doc_id 记录文档 ID。
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services import dify_kb
from app.modules.repository.models.archive import Archive

logger = logging.getLogger(__name__)


def _doc_name(a: Archive) -> str:
    return f"{a.DH or a.id} {a.TM}"[:240]


def _doc_text(a: Archive) -> str:
    parts = [
        f"档号：{a.DH or '—'}",
        f"题名：{a.TM}",
        f"责任者：{a.RZZ or '—'}",
        f"年度：{a.ND or '—'}　全宗号：{a.QZH or '—'}",
        f"密级：{a.MJ or '—'}　保管期限：{a.BGQX or '—'}",
        f"文件日期：{a.WJRQ or '—'}",
    ]
    body = (a.full_text or "").strip()
    if body:
        parts.append(f"\n【原文】\n{body}")
    return "\n".join(parts)


async def sync_archive(db: AsyncSession, archive: Archive) -> Optional[str]:
    """同步单条档案到知识库；回写 kb_doc_id。未配置 KB 时 no-op。"""
    doc_id = await dify_kb.upsert_text(
        archive.kb_doc_id, _doc_name(archive), _doc_text(archive)
    )
    if doc_id and doc_id != archive.kb_doc_id:
        archive.kb_doc_id = doc_id
        await db.flush()
    return doc_id


async def rebuild(db: AsyncSession, tenant_id: Optional[uuid.UUID]) -> int:
    """全量重建：把所有正式库档案推进知识库。"""
    stmt = select(Archive).where(Archive.is_deleted.is_(False))
    if tenant_id:
        stmt = stmt.where(Archive.tenant_id == tenant_id)
    rows = (await db.execute(stmt)).scalars().all()
    n = 0
    for a in rows:
        try:
            if await sync_archive(db, a):
                n += 1
        except Exception:  # noqa: BLE001
            logger.exception("KB 同步失败 archive=%s", a.id)
    await db.commit()
    return n
