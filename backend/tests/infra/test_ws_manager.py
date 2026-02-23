"""
ConnectionManager 单元测试
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infra.ws.manager import ConnectionManager


@pytest.fixture
def manager():
    """每个测试使用独立的 ConnectionManager 实例"""
    return ConnectionManager()


@pytest.fixture
def mock_ws():
    """创建模拟 WebSocket 连接"""
    ws = AsyncMock()
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


class TestConnectionManager:
    """ConnectionManager 基础功能测试"""

    @pytest.mark.asyncio
    async def test_connect_registers_user(self, manager, mock_ws):
        """连接后应注册用户"""
        await manager.connect("user-1", mock_ws)
        assert manager.active_count == 1
        assert manager.is_online("user-1")

    @pytest.mark.asyncio
    async def test_disconnect_removes_user(self, manager, mock_ws):
        """断开后应移除用户"""
        await manager.connect("user-1", mock_ws)
        manager.disconnect("user-1")
        assert manager.active_count == 0
        assert not manager.is_online("user-1")

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_user_no_error(self, manager):
        """断开不存在的用户不应报错"""
        manager.disconnect("nonexistent")
        assert manager.active_count == 0

    @pytest.mark.asyncio
    async def test_connect_replaces_existing(self, manager):
        """同一用户重新连接应替换旧连接"""
        old_ws = AsyncMock()
        old_ws.close = AsyncMock()
        new_ws = AsyncMock()

        await manager.connect("user-1", old_ws)
        await manager.connect("user-1", new_ws)

        assert manager.active_count == 1
        old_ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_personal_success(self, manager, mock_ws):
        """向在线用户发送消息应成功"""
        await manager.connect("user-1", mock_ws)
        result = await manager.send_personal("user-1", "test:event", {"key": "value"})
        assert result is True
        mock_ws.send_text.assert_awaited_once()

        # 验证消息格式
        sent = json.loads(mock_ws.send_text.call_args[0][0])
        assert sent["event"] == "test:event"
        assert sent["data"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_send_personal_offline_user(self, manager):
        """向离线用户发送消息应返回 False"""
        result = await manager.send_personal("offline-user", "test:event", {})
        assert result is False

    @pytest.mark.asyncio
    async def test_send_personal_broken_connection(self, manager):
        """发送失败时应清理断开的连接"""
        ws = AsyncMock()
        ws.send_text = AsyncMock(side_effect=Exception("connection lost"))

        await manager.connect("user-1", ws)
        result = await manager.send_personal("user-1", "test:event", {})
        assert result is False
        assert not manager.is_online("user-1")

    @pytest.mark.asyncio
    async def test_broadcast_to_all(self, manager):
        """广播应向所有在线用户发送"""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws3 = AsyncMock()

        await manager.connect("user-1", ws1)
        await manager.connect("user-2", ws2)
        await manager.connect("user-3", ws3)

        count = await manager.broadcast("system:announce", {"msg": "hello"})
        assert count == 3
        ws1.send_text.assert_awaited_once()
        ws2.send_text.assert_awaited_once()
        ws3.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_broadcast_cleans_dead_connections(self, manager):
        """广播时应清理已断开的连接"""
        ws_alive = AsyncMock()
        ws_dead = AsyncMock()
        ws_dead.send_text = AsyncMock(side_effect=Exception("dead"))

        await manager.connect("alive", ws_alive)
        await manager.connect("dead", ws_dead)

        count = await manager.broadcast("test", {})
        assert count == 1
        assert manager.is_online("alive")
        assert not manager.is_online("dead")

    @pytest.mark.asyncio
    async def test_is_online(self, manager, mock_ws):
        """is_online 应正确反映连接状态"""
        assert not manager.is_online("user-1")
        await manager.connect("user-1", mock_ws)
        assert manager.is_online("user-1")
        manager.disconnect("user-1")
        assert not manager.is_online("user-1")
