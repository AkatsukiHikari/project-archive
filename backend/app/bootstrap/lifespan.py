from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.infra.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    # 初始化 ES 索引（不可用时降级，不阻断启动）
    from app.infra.search.es_client import ensure_index
    await ensure_index()

    # 幂等种子数据（SKIP_SEED=true 可跳过）
    from app.scripts.seed import run_seed
    await run_seed()

    # OCR 后台任务是进程内 asyncio：上次进程退出时未完成的作业已丢失，
    # 标记为失败，避免摘要/进度页对着僵尸任务无限等待
    from sqlalchemy import update
    from app.infra.db.session import AsyncSessionLocal
    from app.modules.ai.models.ocr_job import OcrJob
    async with AsyncSessionLocal() as db:
        await db.execute(
            update(OcrJob)
            .where(OcrJob.status.in_(["pending", "running"]))
            .values(status="failed", error="服务重启中断，请重试")
        )
        await db.commit()

    yield

    # ── Shutdown ──
    await engine.dispose()

    from app.modules.ai.services.dify_service import dify_service
    await dify_service.close()

    from app.infra.search.es_client import close_es_client
    await close_es_client()
