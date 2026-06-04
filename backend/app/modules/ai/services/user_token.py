"""
AI 短 Token（X-User-Token）签发与验签

设计稿 §3.2 / §5.2：Dify 永远不直接持有用户身份，需要回调后端时，
后端在 chat 入口签一个 5 分钟有效期的 short token，作为 ``inputs.user_token``
传给 Dify；Dify 用此 token 调 ``/v1/ai/internal/*`` 系列回调，后端验签后
恢复用户身份（user_id / tenant_id / secret_level），再走 RBAC。

为什么不复用 access_token？
- access_token 通常 ≥ 30min，泄漏到 LLM 上下文风险更大
- 这里要带额外 claim（scenario_code / tenant_id / secret_level），与登录态分开
- 短 TTL（300s）天然防重放
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.common.error_code import ErrorCode
from app.common.exceptions.base import BaseAPIException
from app.core.config import settings
from app.core.security.token import ALGORITHM


_TOKEN_TYPE = "ai_user_token"


@dataclass(frozen=True)
class AIUserTokenClaims:
    user_id: str
    tenant_id: str
    secret_level: int
    scenario_code: str
    issued_at: int
    expires_at: int


class InvalidUserTokenError(BaseAPIException):
    """X-User-Token 缺失 / 过期 / 篡改（6007）。"""

    def __init__(self, detail: str = "X-User-Token 无效或已过期"):
        super().__init__(
            code=ErrorCode.AI_TOOL_AUTH_FAILED,
            message=detail,
            status_code=401,
        )


def sign_user_token(
    *,
    user_id: str,
    tenant_id: str,
    secret_level: int,
    scenario_code: str,
    ttl_seconds: int | None = None,
) -> str:
    ttl = ttl_seconds if ttl_seconds is not None else settings.AI_USER_TOKEN_TTL_SECONDS
    now = datetime.now(timezone.utc)
    expires = now + timedelta(seconds=ttl)
    payload: dict[str, Any] = {
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "typ": _TOKEN_TYPE,
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "secret_level": secret_level,
        "scenario_code": scenario_code,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_user_token(token: str) -> AIUserTokenClaims:
    if not token:
        raise InvalidUserTokenError("X-User-Token 缺失")
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise InvalidUserTokenError("X-User-Token 已过期") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidUserTokenError("X-User-Token 校验失败") from exc

    if payload.get("typ") != _TOKEN_TYPE:
        raise InvalidUserTokenError("X-User-Token 类型不匹配")

    try:
        return AIUserTokenClaims(
            user_id=str(payload["sub"]),
            tenant_id=str(payload["tenant_id"]),
            secret_level=int(payload.get("secret_level", 0)),
            scenario_code=str(payload.get("scenario_code", "")),
            issued_at=int(payload["iat"]),
            expires_at=int(payload["exp"]),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidUserTokenError("X-User-Token 字段缺失") from exc


def verify_service_token(token: str | None) -> None:
    """校验 Dify 调用后端时携带的服务令牌（双向认证）。

    P1：只要 ``settings.AI_SERVICE_TOKEN`` 配置了就强校验；为空则放行（便于本地 demo）。
    """
    expected = settings.AI_SERVICE_TOKEN
    if not expected:
        return
    if not token or token != expected:
        raise BaseAPIException(
            code=ErrorCode.AI_TOOL_AUTH_FAILED,
            message="AI 服务令牌校验失败",
            status_code=401,
        )
