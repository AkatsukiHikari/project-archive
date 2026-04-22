"""
WebSocket 端点

流程：
1. 客户端通过 ?token=xxx 传递 JWT
2. 服务端解码 JWT → 验证用户 → 注册到 ConnectionManager
3. 进入消息循环：处理 ping/pong 心跳
4. 断开时自动清理连接
"""

import asyncio
import json
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import jwt

from app.core.config import settings
from app.core.security.token import ALGORITHM
from app.infra.db.session import get_db
from app.infra.ws.manager import ws_manager
from app.modules.iam.repositories.iam_repository import SQLAlchemyIAMRepository
from app.modules.iam.services.iam_service import IAMService

logger = logging.getLogger(__name__)

router = APIRouter()


async def _authenticate_ws(token: str, db: AsyncSession):
    """
    解码 JWT 并验证用户。

    Returns:
        User 对象（如果认证成功），否则返回 None。
    """
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str = payload.get("sub")
        if user_id_str is None:
            return None
        import uuid
        user_id = uuid.UUID(user_id_str)
    except (jwt.PyJWTError, ValueError):
        return None

    repo = SQLAlchemyIAMRepository(db)
    service = IAMService(repo)
    user = await service.get_user_by_id(user_id)
    if user is None or not user.is_active:
        return None
    return user


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket, token: str = ""):
    """
    主 WebSocket 端点。

    连接 URL 示例: ws://host/api/v1/ws?token=<jwt_access_token>
    """
    # ── 1. Accept 连接（必须先 accept 才能发送错误消息） ──
    await websocket.accept()

    # ── 2. JWT 认证 ──
    # WebSocket 无法使用 FastAPI Depends(get_db)，需手动获取 session
    from app.infra.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        user = await _authenticate_ws(token, db)

    if user is None:
        await websocket.send_text(
            json.dumps({"event": "error", "data": {"message": "认证失败：无效或过期的 Token"}})
        )
        await websocket.close(code=4001, reason="authentication_failed")
        return

    user_id = str(user.id)

    # ── 3. 注册到 ConnectionManager ──
    await ws_manager.connect(user_id, websocket)

    await websocket.send_text(
        json.dumps(
            {"event": "connected", "data": {"user_id": user_id}},
            ensure_ascii=False,
        )
    )

    # ── 4. 消息循环 ──
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue  # 忽略非法 JSON

            event = message.get("event")

            if event == "ping":
                await websocket.send_text(json.dumps({"event": "pong"}))

    except WebSocketDisconnect:
        logger.info("用户 %s WebSocket 断开", user_id)
    except Exception as e:
        logger.error("用户 %s WebSocket 异常: %s", user_id, str(e))
    finally:
        ws_manager.disconnect(user_id)


@router.websocket("/import/{task_id}")
async def import_progress_ws(
    websocket: WebSocket,
    task_id: uuid.UUID,
    token: str = "",
):
    """
    导入任务实时进度推送端点。

    连接 URL: ws://host/ws/import/{task_id}?token=<jwt>

    服务端订阅 Redis pub/sub 频道 import_progress:{task_id}，
    将 Celery worker 推送的进度 JSON 转发给前端，直到任务结束或客户端断开。

    进度消息格式（由 execute_import task 发布）：
      {"type": "progress", "processed": 120, "total": 500, "success": 118, "failed": 2}
      {"type": "done",     "success": 490, "failed": 10, "skipped": 0, "report_url": "..."}
      {"type": "failed",   "reason": "..."}
    """
    await websocket.accept()

    # ── 认证 ──
    from app.infra.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        user = await _authenticate_ws(token, db)

    if user is None:
        await websocket.send_text(
            json.dumps({"event": "error", "data": {"message": "认证失败"}})
        )
        await websocket.close(code=4001, reason="authentication_failed")
        return

    # ── 订阅 Redis 频道 ──
    from app.infra.cache.redis import redis_service

    channel = f"import_progress:{task_id}"
    pubsub = redis_service.pubsub()
    await pubsub.subscribe(channel)

    logger.info("用户 %s 订阅导入进度频道 %s", user.id, channel)

    async def _forward():
        """从 Redis pub/sub 读消息并转发，遇到终态消息后退出。"""
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            raw: str = message["data"]
            await websocket.send_text(raw)
            try:
                payload = json.loads(raw)
                if payload.get("type") in ("done", "failed"):
                    return
            except (json.JSONDecodeError, AttributeError):
                pass

    async def _receive():
        """接收客户端心跳，维持连接并检测断开。"""
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                if msg.get("event") == "ping":
                    await websocket.send_text(json.dumps({"event": "pong"}))
            except (json.JSONDecodeError, AttributeError):
                pass

    try:
        # 同时跑 forward 和 receive，任一完成则停止
        forward_task = asyncio.ensure_future(_forward())
        receive_task = asyncio.ensure_future(_receive())
        done, pending = await asyncio.wait(
            [forward_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for t in pending:
            t.cancel()
    except WebSocketDisconnect:
        logger.info("用户 %s 断开导入进度频道 %s", user.id, channel)
    except Exception as e:
        logger.error("导入进度 WebSocket 异常 [%s]: %s", channel, str(e))
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        try:
            await websocket.close()
        except Exception:
            pass
