from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.infra.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # 表结构由 Alembic 管理，请使用 alembic upgrade head 进行迁移
    # 不再在此处调用 Base.metadata.create_all

    yield

    # Shutdown
    await engine.dispose()
