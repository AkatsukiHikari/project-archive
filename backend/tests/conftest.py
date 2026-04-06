"""
测试配置 (pytest fixtures)

学习笔记：
  conftest.py 是 pytest 的特殊文件，其中定义的 fixture 自动对同目录和子目录的所有测试可用。
  fixture 是测试前置/后置逻辑的声明方式，用 @pytest.fixture 装饰。
  scope 参数控制 fixture 的生命周期：function（每个测试）/ module（每个文件）/ session（整个测试会话）。
"""

import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.common.entity.base import Base


# ─── 事件循环（异步测试必需）─────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """为整个测试会话共用同一个事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ─── 内存数据库（单元测试用，不依赖真实 PostgreSQL）─────────────────────────

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    每个测试函数使用独立的内存 SQLite 数据库。
    测试结束后自动回滚，不污染其他测试。

    注意：SQLite 不支持所有 PostgreSQL 特性（如 UUID、JSON 类型）。
    集成测试（需要真实 PG 特性）应使用真实 PostgreSQL。
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ─── Mock 用户对象 ────────────────────────────────────────────────────────────

@pytest.fixture
def mock_superadmin():
    """超级管理员用户 mock"""
    import uuid
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "admin"
    user.is_active = True
    user.is_superadmin = True
    user.tenant_id = None
    user.hashed_password = "$2b$12$fake_hash"
    return user


@pytest.fixture
def mock_tenant_user():
    """普通租户用户 mock"""
    import uuid
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "testuser"
    user.is_active = True
    user.is_superadmin = False
    user.tenant_id = uuid.uuid4()
    user.hashed_password = "$2b$12$fake_hash"
    return user
