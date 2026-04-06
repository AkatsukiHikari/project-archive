from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.infra.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    # 初始化 ES 索引（不可用时降级，不阻断启动）
    from app.infra.search.es_client import ensure_index
    await ensure_index()

    yield

    # ── Shutdown ──
    await engine.dispose()

    from app.modules.ai.services.dify_service import dify_service
    await dify_service.close()

    from app.infra.search.es_client import close_es_client
    await close_es_client()
