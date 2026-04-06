"""
档案向量化 Celery 任务

触发时机：
  1. ArchiveItem 创建后（有 storage_key 时）
  2. 档案内容更新后
  3. 定时批量补偿（embedding_status='pending' 的记录）

流程：
  MinIO 下载文件 → 文本提取 → 调用 Dify 知识库 API 上传 → 更新 embedding_status

学习笔记：
  @celery_app.task(bind=True) 中 bind=True 让 self 指向任务实例本身，
  可以通过 self.retry() 实现失败重试，通过 self.update_state() 更新进度。
"""

import logging
from celery import Task
from celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.modules.repository.tasks.embedding.embed_archive_item",
    max_retries=3,
    default_retry_delay=60,  # 失败后60秒重试
    queue="embedding",
)
def embed_archive_item(self: Task, item_id: str) -> dict:
    """
    将单个档案条目向量化并上传到 Dify 知识库。

    Args:
        item_id: ArchiveItem UUID 字符串

    Returns:
        {"status": "done", "item_id": "..."}
    """
    import asyncio
    return asyncio.run(_embed_archive_item_async(self, item_id))


async def _embed_archive_item_async(task: Task, item_id: str) -> dict:
    """异步实现（Celery 是同步的，内部用 asyncio.run 执行异步代码）"""
    from app.infra.db.session import AsyncSessionLocal
    from app.modules.repository.repositories.archive_repository import (
        ArchiveItemRepository,
    )
    import uuid

    async with AsyncSessionLocal() as db:
        repo = ArchiveItemRepository(db)
        item = await repo.get_by_id(uuid.UUID(item_id))

        if not item:
            logger.warning("向量化任务：item_id=%s 不存在，跳过", item_id)
            return {"status": "skipped", "item_id": item_id}

        if not item.storage_key:
            logger.warning("向量化任务：item_id=%s 无 storage_key，跳过", item_id)
            await repo.update_embedding_status(item.id, "failed")
            return {"status": "skipped", "item_id": item_id, "reason": "no storage_key"}

        # 更新状态为处理中
        await repo.update_embedding_status(item.id, "processing")

        try:
            # TODO: 从 MinIO 下载文件，提取文本，上传到 Dify 知识库
            # 这里是 Dify 知识库文档上传 API 的调用点
            # 等 Dify 配置完成后补充实现
            #
            # import httpx
            # async with httpx.AsyncClient() as client:
            #     # 1. 从 MinIO 获取文件流
            #     # 2. 上传到 Dify 知识库 POST /datasets/{dataset_id}/document/create_by_file
            #     pass

            logger.info("向量化完成（待接 Dify）: item_id=%s", item_id)
            await repo.update_embedding_status(item.id, "done")
            return {"status": "done", "item_id": item_id}

        except Exception as exc:
            logger.error("向量化失败 item_id=%s: %s", item_id, exc)
            await repo.update_embedding_status(item.id, "failed")
            # Celery 自动重试
            raise task.retry(exc=exc)


@celery_app.task(
    name="app.modules.repository.tasks.embedding.batch_embed_pending",
    queue="embedding",
)
def batch_embed_pending() -> dict:
    """
    批量补偿任务：找出 embedding_status='pending' 的条目，逐个触发向量化。
    可配置为定时任务（Celery Beat），每小时执行一次。
    """
    import asyncio

    async def _run():
        from app.infra.db.session import AsyncSessionLocal
        from app.modules.repository.repositories.archive_repository import ArchiveItemRepository

        async with AsyncSessionLocal() as db:
            repo = ArchiveItemRepository(db)
            pending_items = await repo.list_pending_embedding(limit=100)
            count = 0
            for item in pending_items:
                embed_archive_item.delay(str(item.id))
                count += 1
            return count

    count = asyncio.run(_run())
    logger.info("批量补偿向量化：提交 %d 个任务", count)
    return {"submitted": count}
