"""
OAuth2 授权服务核心逻辑

职责：
- 验证 client_id + redirect_uri
- 生成/校验授权码（含 PKCE）
- 签发 access_token + refresh_token
- 刷新 token
"""

import hashlib
import base64
import secrets
from datetime import timedelta

from app.core.config import settings
from app.core.security.token import create_access_token
from app.modules.oauth import session as session_mgr
from app.common.error_code import ErrorCode
from app.common.exceptions.base import ValidationException, AuthenticationException


def _verify_pkce(code_verifier: str, code_challenge: str) -> bool:
    """
    PKCE 校验：
    code_challenge == BASE64URL(SHA256(code_verifier))
    """
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    computed = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return computed == code_challenge


def validate_client(client_id: str, redirect_uri: str) -> None:
    """校验 client_id 和 redirect_uri 是否合法"""
    clients = settings.OAUTH_CLIENTS
    if client_id not in clients:
        raise ValidationException(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"未注册的客户端: {client_id}",
        )
    allowed_uris = clients[client_id]["redirect_uris"]
    if redirect_uri not in allowed_uris:
        raise ValidationException(
            code=ErrorCode.VALIDATION_ERROR,
            message=f"不允许的回调地址: {redirect_uri}",
        )


async def create_authorization_code(
    user_id: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
) -> str:
    """生成授权码并存入 Redis（30秒过期）"""
    code = secrets.token_urlsafe(32)
    await session_mgr.store_auth_code(
        code=code,
        user_id=user_id,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
    )
    return code


async def exchange_code_for_tokens(
    code: str,
    code_verifier: str,
    client_id: str,
    redirect_uri: str,
) -> dict:
    """
    用授权码换取 tokens：
    1. 从 Redis 取出授权码数据（一次性）
    2. 校验 client_id, redirect_uri, PKCE
    3. 签发 access_token + refresh_token
    """
    code_data = await session_mgr.get_and_delete_auth_code(code)
    if not code_data:
        raise AuthenticationException(
            code=ErrorCode.INVALID_TOKEN,
            message="授权码无效或已过期",
        )

    # 校验参数一致性
    if code_data["client_id"] != client_id:
        raise AuthenticationException(code=ErrorCode.INVALID_TOKEN, message="client_id 不匹配")
    if code_data["redirect_uri"] != redirect_uri:
        raise AuthenticationException(code=ErrorCode.INVALID_TOKEN, message="redirect_uri 不匹配")

    # PKCE 校验
    if not _verify_pkce(code_verifier, code_data["code_challenge"]):
        raise AuthenticationException(code=ErrorCode.INVALID_TOKEN, message="PKCE 校验失败")

    user_id = code_data["user_id"]

    # 签发 tokens
    access_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = secrets.token_urlsafe(48)
    await session_mgr.store_refresh_token(refresh_token, user_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


async def refresh_access_token(refresh_token_value: str) -> dict:
    """
    用 refresh_token 刷新 access_token（Token Rotation）：
    旧 refresh_token 立即失效，签发新的。
    """
    user_id = await session_mgr.get_and_rotate_refresh_token(refresh_token_value)
    if not user_id:
        raise AuthenticationException(
            code=ErrorCode.TOKEN_EXPIRED,
            message="Refresh token 无效或已过期",
        )

    access_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    new_refresh_token = secrets.token_urlsafe(48)
    await session_mgr.store_refresh_token(new_refresh_token, user_id)

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
