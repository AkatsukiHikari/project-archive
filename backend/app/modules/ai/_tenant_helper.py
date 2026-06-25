"""
AI 模块统一的租户兜底：用户 tenant_id=None 时回退到 system 租户。

AI 模块所有表的 tenant_id 都是 NOT NULL，但 superadmin / 平台级用户的
``current_user.tenant_id`` 可能是 None，本 helper 统一处理。
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import BaseAPIException
from app.modules.iam.models.tenant import Tenant
from app.modules.iam.models.user import User


async def ensure_tenant_id(db: AsyncSession, user: User) -> uuid.UUID:
    if user.tenant_id is not None:
        return user.tenant_id
    row = (
        await db.execute(
            select(Tenant).where(Tenant.code == "system", Tenant.is_deleted.is_(False))
        )
    ).scalar_one_or_none()
    if row is None:
        raise BaseAPIException(
            code=ErrorCode.AI_CAPABILITY_DISABLED,
            message="当前用户未绑定租户，且系统未配置默认租户",
            status_code=400,
        )
    return row.id
