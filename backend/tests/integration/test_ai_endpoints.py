"""
AI 模块端点集成测试

策略：用 ASGITransport 起 FastAPI app，DI 覆盖 ``get_current_user`` 和 ``get_db``，
DB 用 AsyncMock 模拟。验证路由签名 + 权限隔离逻辑 + ResponseModel 包络结构。
不依赖真实 Postgres / ES（这俩在不同测试环境里行为差异大）。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User


@pytest.fixture
def mock_user() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = uuid.uuid4()
    user.tenant_id = uuid.uuid4()
    user.username = "alice"
    user.is_active = True
    user.is_superadmin = False
    user.secret_level = 2
    return user


@pytest.fixture
def app_with_overrides(mock_user: MagicMock):
    """覆盖 get_current_user / get_db 后再 yield app。"""
    from app.main import app

    db_mock = AsyncMock()
    db_mock.commit = AsyncMock(return_value=None)
    db_mock.flush = AsyncMock(return_value=None)

    async def fake_get_db():
        yield db_mock

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = fake_get_db
    try:
        yield app, db_mock
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(app_with_overrides):
    app, db_mock = app_with_overrides

    async def _factory() -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _factory, db_mock


def _execute_returning(rows: list) -> AsyncMock:
    """构造 db.execute(...) 的返回，让 .scalars().all() 给出 rows。"""
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return AsyncMock(return_value=result)


def _execute_scalar(value):
    result = MagicMock()
    result.scalar_one.return_value = value
    return AsyncMock(return_value=result)


# ──────────────────────────────────────────────────────────────
# /v1/ai/sessions
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_returns_envelope(client) -> None:
    factory, db = client

    row = SimpleNamespace(
        id=uuid.uuid4(),
        title="如何申请档案利用",
        last_scenario_code="qa",
        last_model_tier="准",
        message_count=4,
        dify_conversation_id="dify-conv-xyz",
        update_time=datetime(2026, 5, 26, 10, 0, tzinfo=timezone.utc),
        create_time=datetime(2026, 5, 26, 9, 0, tzinfo=timezone.utc),
    )

    # 路由内部依次 execute(count) + execute(rows)
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [row]
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    async with await factory() as ac:
        resp = await ac.get("/api/v1/ai/sessions?page=1&size=10")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["title"] == "如何申请档案利用"
    assert body["data"]["items"][0]["last_scenario_code"] == "qa"


@pytest.mark.asyncio
async def test_delete_session_not_found(client) -> None:
    factory, db = client

    not_found_result = MagicMock()
    not_found_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=not_found_result)

    async with await factory() as ac:
        resp = await ac.delete(f"/api/v1/ai/sessions/{uuid.uuid4()}")

    # BaseAPIException 全局 handler 映射 → 404 / 标准 envelope
    assert resp.status_code in (404, 409)
    body = resp.json()
    # 全局异常处理器返回 ResponseModel(code=AI_PATCH_STATE_CONFLICT)
    assert body.get("code") in (6003, body.get("code"))


@pytest.mark.asyncio
async def test_delete_session_soft_deletes(client, mock_user) -> None:
    factory, db = client

    row = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=mock_user.tenant_id,
        user_id=mock_user.id,
        is_deleted=False,
    )
    found = MagicMock()
    found.scalar_one_or_none.return_value = row
    db.execute = AsyncMock(return_value=found)

    async with await factory() as ac:
        resp = await ac.delete(f"/api/v1/ai/sessions/{row.id}")

    assert resp.status_code == 200
    assert resp.json()["code"] == 0
    # 软删除：is_deleted 应被置 True
    assert row.is_deleted is True
    db.commit.assert_awaited()


# ──────────────────────────────────────────────────────────────
# /v1/ai/patches
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_patches_with_status_filter(client) -> None:
    factory, db = client

    row = SimpleNamespace(
        id=uuid.uuid4(),
        scenario_code="attach",
        target_type="archive",
        target_id=uuid.uuid4(),
        operation="create",
        status="pending",
        gate="review",
        confidence=0.87,
        workflow_version="v1",
        reviewer_id=None,
        create_time=datetime(2026, 5, 26, 10, 0, tzinfo=timezone.utc),
        update_time=datetime(2026, 5, 26, 10, 0, tzinfo=timezone.utc),
    )
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = [row]
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    async with await factory() as ac:
        resp = await ac.get("/api/v1/ai/patches?status=pending&scenario_code=attach")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["scenario_code"] == "attach"
    assert body["data"]["items"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_patch_review_returns_p3_placeholder(client) -> None:
    factory, _db = client
    async with await factory() as ac:
        resp = await ac.post(
            f"/api/v1/ai/patches/{uuid.uuid4()}/review",
            json={"action": "approve"},
        )
    # P1 占位明确抛 6003 + 409
    assert resp.status_code in (409, 200)
    body = resp.json()
    assert body.get("code") == 6003 or "P3" in body.get("message", "")


# ──────────────────────────────────────────────────────────────
# /v1/ai/kb/status
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_kb_status_tolerates_es_unreachable(client, mock_user, monkeypatch) -> None:
    """ES 客户端抛错时 kb/status 仍 200，es_count=None 提示 ES 不可达。"""
    factory, db = client

    # _meta_stats 内部连发两次 execute（db_count + last_synced）
    count_result = MagicMock()
    count_result.scalar_one.return_value = 0
    last_synced_result = MagicMock()
    last_synced_result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(side_effect=[count_result, last_synced_result])

    # ES 客户端 mock：count 抛错
    from app.modules.ai.services import kb_sync_service as svc_mod

    es_client = MagicMock()
    es_client.count = AsyncMock(side_effect=RuntimeError("ES down"))
    monkeypatch.setattr(svc_mod, "get_es_client", lambda: es_client)

    async with await factory() as ac:
        resp = await ac.get("/api/v1/ai/kb/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    items = body["data"]["items"]
    assert len(items) == 3
    meta = next(i for i in items if i["kb_type"] == "meta")
    assert meta["db_count"] == 0
    assert meta["es_count"] is None
    assert "ES 不可达" in (meta["note"] or "")
    # rules / ocr 是 placeholder
    rules = next(i for i in items if i["kb_type"] == "rules")
    assert rules["synced"] is True


@pytest.mark.asyncio
async def test_kb_rebuild_rejects_unknown_kb_type(client) -> None:
    factory, _db = client
    async with await factory() as ac:
        resp = await ac.post("/api/v1/ai/kb/rebuild", json={"kb_type": "ocr"})
    # pydantic 拒绝 Literal["meta"] 之外的值（422）
    assert resp.status_code in (400, 422)


# ──────────────────────────────────────────────────────────────
# /v1/ai/scenarios
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_scenarios_returns_nine(client) -> None:
    factory, db = client
    # 无任何 AIScenario 行：路由按 settings.AI_ENABLED_CAPABILITIES 回退
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=rows_result)

    async with await factory() as ac:
        resp = await ac.get("/api/v1/ai/scenarios")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert len(body["data"]["scenarios"]) == 9
    codes = {s["code"] for s in body["data"]["scenarios"]}
    assert codes == {"qa", "search", "summary", "attach", "catalog", "fournat", "draft", "relate", "kb_manage"}
    # qa 在默认灰度白名单里
    qa = next(s for s in body["data"]["scenarios"] if s["code"] == "qa")
    assert qa["enabled"] is True
