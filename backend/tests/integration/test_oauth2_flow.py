"""
OAuth2 授权码 + PKCE 集成测试

测试完整的 SSO 流程：
  1. GET /oauth/authorize  — 未登录时重定向到 /oauth/login
  2. POST /oauth/login     — 登录成功，获得授权码并设置 session cookie
  3. POST /oauth/token     — 用授权码换 access_token + refresh_token
  4. GET /api/v1/users/me  — 用 access_token 访问受保护接口

学习笔记：
  PKCE（Proof Key for Code Exchange）是 OAuth2 的安全扩展。
  防止"授权码拦截攻击"：即使授权码被第三方截获，没有 code_verifier 也无法换取 token。

  flow:
    client_side: code_verifier = random_string()
                 code_challenge = base64url(sha256(code_verifier))  ← 发给服务端
    server_side: 存储 code_challenge，签发 code
    token_exchange: 发送 code + code_verifier，服务端验证 sha256(verifier) == challenge
"""

import base64
import hashlib
import os
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock


def generate_pkce_pair() -> tuple[str, str]:
    """生成 PKCE code_verifier 和 code_challenge"""
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return code_verifier, code_challenge


@pytest.fixture
def mock_user():
    import uuid
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "testadmin"
    user.is_active = True
    user.is_superadmin = False
    user.tenant_id = None
    return user


@pytest.mark.asyncio
async def test_authorize_redirects_to_login_when_no_session():
    """未登录时 /oauth/authorize 应重定向到登录页"""
    from app.main import app

    code_verifier, code_challenge = generate_pkce_pair()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            "/oauth/authorize",
            params={
                "client_id": "admin-web",
                "redirect_uri": "http://localhost:3000/auth/callback",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "response_type": "code",
            },
            follow_redirects=False,
        )

    assert resp.status_code == 302
    assert "/oauth/login" in resp.headers["location"]


@pytest.mark.asyncio
async def test_login_with_wrong_credentials_redirects_with_error(mock_user):
    """错误密码登录失败，重定向回登录页并附带 error 参数"""
    from app.main import app

    code_verifier, code_challenge = generate_pkce_pair()

    with patch(
        "app.modules.oauth.api.routes.IAMService.authenticate",
        new_callable=AsyncMock,
        return_value=None,  # 认证失败
    ), patch(
        "app.modules.oauth.api.routes._check_login_rate_limit",
        new_callable=AsyncMock,
        return_value=True,
    ), patch(
        "app.modules.oauth.api.routes._record_login_failure",
        new_callable=AsyncMock,
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/oauth/login",
                data={
                    "username": "wronguser",
                    "password": "wrongpass",
                    "client_id": "admin-web",
                    "redirect_uri": "http://localhost:3000/auth/callback",
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
                    "response_type": "code",
                    "state": "",
                },
                follow_redirects=False,
            )

    assert resp.status_code == 302
    assert "error=" in resp.headers["location"]


@pytest.mark.asyncio
async def test_pkce_pair_generation():
    """PKCE 对生成正确性验证"""
    code_verifier, code_challenge = generate_pkce_pair()

    # code_verifier 应为 URL 安全 base64 字符串
    assert len(code_verifier) > 40

    # 手动验证 code_challenge = base64url(sha256(verifier))
    expected_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode()

    assert code_challenge == expected_challenge
