"""
知识库同步服务

设计稿 §4.1：P1 交付 L1 元数据全量 + 增量同步。
本服务负责把 DB 中的档案元数据推到 ES 索引（已由 ``repository/services/es_sync_service``
负责单条/批量推送），并提供：

- ``get_stats(tenant_id)``  返回 ES 文档数 / DB 档案数 / 最近同步时间，供后台监控
- ``rebuild_meta(tenant_id, batch_size)`` 全量重建：分批扫 DB 推 ES（幂等覆盖）
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.search.es_client import ARCHIVE_INDEX, get_es_client
from app.modules.repository.models.archive import ArchiveStaging
from app.modules.repository.services import es_sync_service

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KBStats:
    """知识库状态快照。"""

    kb_type: str
    db_count: int
    es_count: int | None      # ES 不可达时为 None
    synced: bool              # db_count == es_count
    last_synced_at: str | None  # 最近一次同步的时间戳（ISO）
    note: str | None = None


@dataclass(frozen=True)
class RebuildResult:
    kb_type: str
    scanned: int
    synced: int
    failed: int
    duration_ms: int


class KBSyncService:
    """L1 元数据同步（DB → ES）。"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def get_stats(self, tenant_id: uuid.UUID) -> list[KBStats]:
        """返回各 KB 类型的状态。当前实装：meta（archive） + rules / ocr 占位。"""
        return [
            await self._meta_stats(tenant_id),
            KBStats(kb_type="rules", db_count=0, es_count=0, synced=True, last_synced_at=None,
                    note="L4 业务规则：暂用静态种子，无需同步"),
            KBStats(kb_type="ocr",   db_count=0, es_count=None, synced=False, last_synced_at=None,
                    note="L2 OCR 全文：P3 接入"),
        ]

    async def rebuild_meta(
        self, tenant_id: uuid.UUID, *, batch_size: int = 200
    ) -> RebuildResult:
        """全量重建 meta KB：分批扫 ArchiveStaging 推 ES。"""
        started = time.time()
        scanned = synced = failed = 0
        offset = 0

        while True:
            stmt = (
                select(ArchiveStaging)
                .where(
                    ArchiveStaging.tenant_id == tenant_id,
                    ArchiveStaging.is_deleted.is_(False),
                )
                .order_by(ArchiveStaging.id)
                .offset(offset)
                .limit(batch_size)
            )
            batch = (await self._db.execute(stmt)).scalars().all()
            if not batch:
                break

            try:
                ok = await es_sync_service.bulk_sync(batch)
                synced += ok
                failed += len(batch) - ok
            except Exception:
                logger.exception("kb_sync rebuild_meta 批次失败 offset=%d size=%d", offset, len(batch))
                failed += len(batch)

            scanned += len(batch)
            offset += batch_size

        duration = int((time.time() - started) * 1000)
        logger.info(
            "kb_sync rebuild_meta done tenant=%s scanned=%d synced=%d failed=%d duration=%dms",
            tenant_id, scanned, synced, failed, duration,
        )
        return RebuildResult(
            kb_type="meta",
            scanned=scanned,
            synced=synced,
            failed=failed,
            duration_ms=duration,
        )

    # ── 内部：单类型 stats ─────────────────────────────────────────────

    async def _meta_stats(self, tenant_id: uuid.UUID) -> KBStats:
        db_count = (
            await self._db.execute(
                select(func.count(ArchiveStaging.id)).where(
                    ArchiveStaging.tenant_id == tenant_id,
                    ArchiveStaging.is_deleted.is_(False),
                )
            )
        ).scalar_one()

        last_synced = (
            await self._db.execute(
                select(func.max(ArchiveStaging.es_synced_at)).where(
                    ArchiveStaging.tenant_id == tenant_id,
                    ArchiveStaging.is_deleted.is_(False),
                )
            )
        ).scalar_one_or_none()

        es_count: int | None = None
        note: str | None = None
        try:
            client = get_es_client()
            resp = await client.count(
                index=ARCHIVE_INDEX,
                body={"query": {"term": {"tenant_id": str(tenant_id)}}},
            )
            es_count = int(resp.get("count", 0))
        except Exception as exc:
            note = f"ES 不可达：{exc.__class__.__name__}"
            logger.warning("kb_sync get_stats ES 不可达: %s", exc)

        synced = es_count is not None and es_count == db_count
        return KBStats(
            kb_type="meta",
            db_count=db_count,
            es_count=es_count,
            synced=synced,
            last_synced_at=str(last_synced) if last_synced else None,
            note=note,
        )
