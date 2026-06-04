"""短 Token 签发 / 验签单测。"""
from __future__ import annotations

import time
import uuid

import jwt
import pytest

from app.core.config import settings
from app.core.security.token import ALGORITHM
from app.modules.ai.services.user_token import (
    InvalidUserTokenError,
    sign_user_token,
    verify_service_token,
    verify_user_token,
)


@pytest.mark.unit
def test_sign_and_verify_round_trip() -> None:
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    token = sign_user_token(
        user_id=user_id,
        tenant_id=tenant_id,
        secret_level=2,
        scenario_code="qa",
    )
    claims = verify_user_token(token)

    assert claims.user_id == user_id
    assert claims.tenant_id == tenant_id
    assert claims.secret_level == 2
    assert claims.scenario_code == "qa"
    assert claims.expires_at > claims.issued_at


@pytest.mark.unit
def test_verify_missing_token_raises() -> None:
    with pytest.raises(InvalidUserTokenError, match="缺失"):
        verify_user_token("")


@pytest.mark.unit
def test_verify_tampered_token_raises() -> None:
    token = sign_user_token(
        user_id="u1", tenant_id="t1", secret_level=0, scenario_code="qa"
    )
    bad = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
    with pytest.raises(InvalidUserTokenError, match="校验失败"):
        verify_user_token(bad)


@pytest.mark.unit
def test_verify_expired_token_raises() -> None:
    token = sign_user_token(
        user_id="u1", tenant_id="t1", secret_level=0, scenario_code="qa", ttl_seconds=1
    )
    time.sleep(1.2)
    with pytest.raises(InvalidUserTokenError, match="过期"):
        verify_user_token(token)


@pytest.mark.unit
def test_verify_wrong_type_rejects() -> None:
    payload = {
        "sub": "u1",
        "tenant_id": "t1",
        "secret_level": 0,
        "scenario_code": "qa",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        "typ": "access_token",  # 错误类型
    }
    fake = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(InvalidUserTokenError, match="类型"):
        verify_user_token(fake)


@pytest.mark.unit
def test_verify_missing_claims_rejects() -> None:
    payload = {
        # 故意缺 sub
        "tenant_id": "t1",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
        "typ": "ai_user_token",
    }
    fake = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(InvalidUserTokenError, match="字段"):
        verify_user_token(fake)


@pytest.mark.unit
def test_service_token_passthrough_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_SERVICE_TOKEN", "")
    # 没配置就放行（本地 demo 友好）
    verify_service_token(None)
    verify_service_token("anything")


@pytest.mark.unit
def test_service_token_enforced_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_SERVICE_TOKEN", "secret-svc")
    with pytest.raises(Exception):
        verify_service_token(None)
    with pytest.raises(Exception):
        verify_service_token("wrong")
    # 正确放行
    verify_service_token("secret-svc")
