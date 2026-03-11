from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.bootstrap.lifespan import lifespan
from app.common.exceptions.base import BaseAPIException
from app.common.exceptions.handler import api_exception_handler, generic_exception_handler


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_PREFIX}/v1/openapi.json",
        lifespan=lifespan,
        redirect_slashes=False,
    )

    # CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # 全局异常处理
    app.add_exception_handler(BaseAPIException, api_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # 健康检查
    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok"}

    # API 路由注册
    from app.api.v1.router import v1_router
    app.include_router(v1_router, prefix=settings.API_PREFIX)

    # WebSocket 路由（独立于 API 版本）
    from app.api.v1 import ws
    app.include_router(ws.router, prefix="/ws", tags=["websocket"])

    # OAuth2 SSO 路由（不在 /api 版本管理下）
    from app.modules.oauth.api.routes import router as oauth_router
    app.include_router(oauth_router, prefix="/oauth", tags=["oauth"])

    # 静态文件服务（仅本地开发 local 模式），生产环境由 Nginx / MinIO / CDN 接管
    if settings.STORAGE_TYPE.lower() == "local":
        from fastapi.staticfiles import StaticFiles
        from pathlib import Path
        storage_root = Path(settings.STORAGE_LOCAL_ROOT)
        storage_root.mkdir(parents=True, exist_ok=True)
        app.mount("/static", StaticFiles(directory=str(storage_root)), name="static")

    return app
