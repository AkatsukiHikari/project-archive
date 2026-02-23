"""
Redis Session 管理器

SSO 的核心：通过 HttpOnly Cookie 存储 session_id，
Redis 存储 session 数据（user_id），实现跨前端免登录。
"""

import json
import secrets
from typing import Optional

from app.core.config import settings
from app.infra.cache.redis import redis_service


# Key 前缀
SESSION_PREFIX = "sso:session:"
SESSION_TTL = settings.SESSION_EXPIRE_HOURS * 3600

AUTH_CODE_PREFIX = "sso:code:"
AUTH_CODE_TTL = 30  # 授权码 30 秒过期

REFRESH_TOKEN_PREFIX = "sso:refresh:"
REFRESH_TOKEN_TTL = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400


# ─── Session 管理 ───


async def create_session(user_id: str) -> str:
    """创建 SSO Session，返回 session_id"""
    session_id = secrets.token_urlsafe(32)
    await redis_service.set(f"{SESSION_PREFIX}{session_id}", user_id, expire=SESSION_TTL)
    return session_id


async def get_session(session_id: str) -> Optional[str]:
    """通过 session_id 获取 user_id，不存在返回 None"""
    return await redis_service.get(f"{SESSION_PREFIX}{session_id}")


async def delete_session(session_id: str) -> None:
    """删除 Session（注销时调用）"""
    await redis_service.delete(f"{SESSION_PREFIX}{session_id}")


# ─── 授权码管理 ───


async def store_auth_code(
    code: str,
    user_id: str,
    client_id: str,
    redirect_uri: str,
    code_challenge: str,
) -> None:
    """存储授权码及关联数据（30秒过期）"""
    data = {
        "user_id": user_id,
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
    }
    await redis_service.set(f"{AUTH_CODE_PREFIX}{code}", data, expire=AUTH_CODE_TTL)


async def get_and_delete_auth_code(code: str) -> Optional[dict]:
    """获取并删除授权码（一次性使用）"""
    return await redis_service.get_json_and_delete(f"{AUTH_CODE_PREFIX}{code}")


# ─── Refresh Token 管理 ───


async def store_refresh_token(token: str, user_id: str) -> None:
    """存储 refresh_token"""
    await redis_service.set(f"{REFRESH_TOKEN_PREFIX}{token}", user_id, expire=REFRESH_TOKEN_TTL)


async def get_and_rotate_refresh_token(token: str) -> Optional[str]:
    """
    获取 refresh_token 关联的 user_id 并删除旧 token（Token Rotation）。
    调用方需签发新的 refresh_token。
    """
    return await redis_service.get_and_delete(f"{REFRESH_TOKEN_PREFIX}{token}")
