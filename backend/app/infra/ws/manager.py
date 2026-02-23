"""
WebSocket 连接管理器

职责：
- 维护活跃 WebSocket 连接（per-user 单连接）
- 提供点对点推送 / 全局广播能力
- 统一消息格式：{ event: str, data: Any }
"""

import json
import logging
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    全局 WebSocket 连接管理器。

    每个用户仅保留一条活跃连接：新连接接入时自动关闭旧连接，
    避免同一用户多标签页导致的幽灵连接问题。
    """

    def __init__(self) -> None:
        # user_id (str) → WebSocket
        self._connections: dict[str, WebSocket] = {}

    @property
    def active_count(self) -> int:
        """当前在线连接数"""
        return len(self._connections)

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """
        注册新连接。若该用户已有连接，先关闭旧连接再替换。
        """
        # 如果同一用户已有连接，关闭旧连接
        if user_id in self._connections:
            old_ws = self._connections[user_id]
            try:
                await old_ws.close(code=4001, reason="replaced_by_new_connection")
            except Exception:
                pass  # 旧连接可能已断开，忽略
            logger.info("已关闭用户 %s 的旧连接（被新连接替换）", user_id)

        self._connections[user_id] = websocket
        logger.info("用户 %s 已连接 WebSocket（在线: %d）", user_id, self.active_count)

    def disconnect(self, user_id: str) -> None:
        """移除连接（断开时调用）"""
        self._connections.pop(user_id, None)
        logger.info("用户 %s 已断开 WebSocket（在线: %d）", user_id, self.active_count)

    async def send_personal(self, user_id: str, event: str, data: Any = None) -> bool:
        """
        向指定用户推送消息。

        Returns:
            True 若推送成功，False 若用户不在线或发送失败。
        """
        websocket = self._connections.get(user_id)
        if websocket is None:
            return False
        try:
            message = json.dumps({"event": event, "data": data}, ensure_ascii=False)
            await websocket.send_text(message)
            return True
        except Exception:
            # 连接可能已断开，清理
            self.disconnect(user_id)
            logger.warning("向用户 %s 推送消息失败，已移除连接", user_id)
            return False

    async def broadcast(self, event: str, data: Any = None) -> int:
        """
        向所有在线用户广播消息。

        Returns:
            成功推送的连接数量。
        """
        message = json.dumps({"event": event, "data": data}, ensure_ascii=False)
        dead_connections: list[str] = []
        success_count = 0

        for user_id, websocket in self._connections.items():
            try:
                await websocket.send_text(message)
                success_count += 1
            except Exception:
                dead_connections.append(user_id)

        # 清理已断开的连接
        for user_id in dead_connections:
            self.disconnect(user_id)

        return success_count

    def is_online(self, user_id: str) -> bool:
        """检查用户是否在线"""
        return user_id in self._connections


# ── 模块级单例 ──
ws_manager = ConnectionManager()
