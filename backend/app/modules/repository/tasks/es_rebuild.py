"""
ES 全量重建任务。
管理员在后台触发后，逐页扫描 repo_archive 表，bulk index 到 ES。
"""
import asyncio
import logging

from celery import Task
from celery_app import celery_app

logger = logging.getLogger(__name__)
PAGE_SIZE = 500


@celery_app.task(
    bind=True,
    name="app.modules.repository.tasks.es_rebuild.rebuild_archive_index",
    max_retries=0,
    queue="default",
)
def rebuild_archive_index(self: Task, tenant_id: str | None = None) -> dict:
    return asyncio.run(_rebuild_async(tenant_id))


async def _rebuild_async(tenant_id_str: str | None) -> dict:
    import uuid
    from sqlalchemy import select, and_
    from app.infra.db.session import AsyncSessionLocal
    from app.modules.repository.models.archive import Archive
    from app.modules.repository.services.es_sync_service import bulk_sync
    from app.infra.search.es_client import get_es_client, ARCHIVE_INDEX

    tid = uuid.UUID(tenant_id_str) if tenant_id_str else None
    total = 0
    offset = 0

    async with AsyncSessionLocal() as db:
        while True:
            conds = [Archive.is_deleted == False]
            if tid is not None:
                conds.append(Archive.tenant_id == tid)
            result = await db.execute(
                select(Archive).where(and_(*conds)).offset(offset).limit(PAGE_SIZE)
            )
            batch = list(result.scalars().all())
            if not batch:
                break
            synced = await bulk_sync(batch)
            total += synced
            offset += PAGE_SIZE
            logger.info("ES 重建进度: offset=%d synced=%d", offset, synced)

    logger.info("ES 全量重建完成，共同步 %d 条", total)
    return {"synced": total}
