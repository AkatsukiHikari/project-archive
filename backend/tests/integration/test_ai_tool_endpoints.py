"""
AI Tool 回调端点集成测试

策略：内部端点不走 get_current_user 鉴权，只验 X-Service-Token + X-User-Token。
覆盖：
- 缺 X-User-Token → 401 / 6007
- 错误 token（篡改/过期）→ 401 / 6007
- 类型不匹配（非 ai_user_token）→ 401 / 6007
- 合法 token + service token 未配置 → 200 + 走 retrieve 流程
- service token 配置后强校验
- tool/dispatch 当前返 not_implemented
"""
from __future__ import annotations

import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.security.token import ALGORITHM
from app.infra.db.session import get_db
from app.modules.ai.services.user_token import sign_user_token


@pytest.fixture
def app_with_db_override():
    from app.main import app

    db_mock = AsyncMock()

    async def fake_get_db():
        yield db_mock

    app.dependency_overrides[get_db] = fake_get_db
    try:
        yield app, db_mock
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client(app_with_db_override):
    app, db_mock = app_with_db_override

    async def _factory() -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    return _factory, db_mock


@pytest.fixture
def valid_token() -> str:
    return sign_user_token(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        secret_level=2,
        scenario_code="qa",
    )


# ──────────────────────────────────────────────────────────────
# /v1/ai/internal/retrieve
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retrieve_rejects_without_user_token(client) -> None:
    factory, _db = client
    async with await factory() as ac:
        resp = await ac.post(
            "/api/v1/ai/internal/retrieve",
            json={"query": "x", "kb_type": "meta", "top_k": 3},
        )
    assert resp.status_code == 401
    body = resp.json()
    assert body["code"] == 6007  # AI_TOOL_AUTH_FAILED


@pytest.mark.asyncio
async def test_retrieve_rejects_tampered_token(client) -> None:
    factory, _db = client
    good = sign_user_token(
        user_id="u1", tenant_id="t1", secret_level=0, scenario_code="qa"
    )
    bad = good[:-2] + ("AA" if not good.endswith("AA") else "BB")
    async with await factory() as ac:
        resp = await ac.post(
            "/api/v1/ai/internal/retrieve",
            json={"query": "x", "kb_type": "meta", "top_k": 3},
            headers={"X-User-Token": bad},
        )
    assert resp.status_code == 401
    assert resp.json()["code"] == 6007


@pytest.mark.asyncio
async def test_retrieve_rejects_wrong_token_type(client) -> None:
    factory, _db = client
    # 用 access_token 风格 payload 签发（typ 错误）
    payload = {
        "sub": "u1",
        "tenant_id": "t1",
        "secret_level": 0,
        "scenario_code": "qa",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        "typ": "access_token",
    }
    fake = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    async with await factory() as ac:
        resp = await ac.post(
            "/api/v1/ai/internal/retrieve",
            json={"query": "x", "kb_type": "meta", "top_k": 3},
            headers={"X-User-Token": fake},
        )
    assert resp.status_code == 401
    assert resp.json()["code"] == 6007


@pytest.mark.asyncio
async def test_retrieve_passes_with_valid_token(client, valid_token, monkeypatch) -> None:
    factory, _db = client
    # 让底层 retrieval_service 返空（避免依赖 ES）—— audit 也吞 quiet
    async def _empty_search(*_a, **_kw):
        return {"hits": {"hits": []}}

    from app.modules.ai.services import retrieval_service as rsvc

    es_mock = MagicMock()
    es_mock.search = AsyncMock(side_effect=_empty_search)
    monkeypatch.setattr(rsvc, "get_es_client", lambda: es_mock)

    async with await factory() as ac:
        resp = await ac.post(
            "/api/v1/ai/internal/retrieve",
            json={"query": "永久保管", "kb_type": "meta", "top_k": 3},
            headers={"X-User-Token": valid_token},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["chunks"] == []


@pytest.mark.asyncio
async def test_retrieve_rejects_when_service_token_required(client, valid_token, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_SERVICE_TOKEN", "secret-svc")
    factory, _db = client
    async with await factory() as ac:
        # 提供 user-token 但不带 service-token
        resp = await ac.post(
            "/api/v1/ai/internal/retrieve",
            json={"query": "q", "kb_type": "meta", "top_k": 3},
            headers={"X-User-Token": valid_token},
        )
    assert resp.status_code == 401
    assert resp.json()["code"] == 6007


@pytest.mark.asyncio
async def test_retrieve_passes_with_both_tokens(client, valid_token, monkeypatch) -> None:
    monkeypatch.setattr(settings, "AI_SERVICE_TOKEN", "svc-key-7")

    from app.modules.ai.services import retrieval_service as rsvc

    es_mock = MagicMock()
    es_mock.search = AsyncMock(return_value={"hits": {"hits": []}})
    monkeypatch.setattr(rsvc, "get_es_client", lambda: es_mock)

    factory, _db = client
    async with await factory() as ac:
        resp = await ac.post(
            "/api/v1/ai/internal/retrieve",
            json={"query": "q", "kb_type": "meta", "top_k": 3},
            headers={
                "X-User-Token": valid_token,
                "X-Service-Token": "svc-key-7",
            },
        )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


# ──────────────────────────────────────────────────────────────
# /v1/ai/internal/tool/dispatch
# ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_rejects_without_token(client) -> None:
    factory, _db = client
    async with await factory() as ac:
        resp = await ac.post(
            "/api/v1/ai/internal/tool/dispatch",
            json={"tool_name": "attach_archive", "arguments": {}},
        )
    assert resp.status_code == 401
    assert resp.json()["code"] == 6007


@pytest.mark.asyncio
async def test_dispatch_returns_not_implemented_p1(client, valid_token) -> None:
    factory, _db = client
    async with await factory() as ac:
        resp = await ac.post(
            "/api/v1/ai/internal/tool/dispatch",
            json={"tool_name": "attach_archive", "arguments": {"x": 1}},
            headers={"X-User-Token": valid_token},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "not_implemented"
    assert body["data"]["tool_name"] == "attach_archive"
