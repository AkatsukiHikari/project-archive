"""
WebSocket 端点

流程：
1. 客户端通过 ?token=xxx 传递 JWT
2. 服务端解码 JWT → 验证用户 → 注册到 ConnectionManager
3. 进入消息循环：处理 ping/pong 心跳
4. 断开时自动清理连接
"""

import json
import logging

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
        username = payload.get("sub")
        if username is None:
            return None
    except jwt.PyJWTError:
        return None

    repo = SQLAlchemyIAMRepository(db)
    service = IAMService(repo)
    user = await service.get_user(username=username)
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
