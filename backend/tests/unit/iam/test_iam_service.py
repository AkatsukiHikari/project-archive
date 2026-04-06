"""
IAM Service 单元测试

策略：Mock Repository 层，只测试 Service 层的业务逻辑。
这样测试不依赖数据库，运行极快（毫秒级）。
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.iam.services.iam_service import IAMService
from app.modules.iam.schemas.user import UserCreate, UserUpdate
from app.common.exceptions.base import ValidationException


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_iam_repo():
    repo = AsyncMock()
    repo.db = AsyncMock()
    return repo

@pytest.fixture
def mock_role_repo():
    return AsyncMock()

@pytest.fixture
def iam_service(mock_iam_repo, mock_role_repo):
    return IAMService(mock_iam_repo, mock_role_repo)

@pytest.fixture
def sample_user():
    user = MagicMock()
    user.id = uuid.uuid4()
    user.username = "testuser"
    user.email = "test@example.com"
    user.hashed_password = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewuLRsxbz5pREzGO"
    user.is_active = True
    user.is_superadmin = False
    user.roles = []
    return user


# ─── authenticate() ────────────────────────────────────────────────────────

class TestAuthenticate:
    """验证用户名密码认证逻辑"""

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_when_user_not_found(
        self, iam_service, mock_iam_repo
    ):
        """用户不存在时返回 None（不抛异常，防止用户枚举攻击）"""
        mock_iam_repo.get_by_username.return_value = None

        result = await iam_service.authenticate("nobody", "password")

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_returns_none_on_wrong_password(
        self, iam_service, mock_iam_repo, sample_user
    ):
        """密码错误时返回 None"""
        mock_iam_repo.get_by_username.return_value = sample_user

        with patch("app.modules.iam.services.iam_service.verify_password", return_value=False):
            result = await iam_service.authenticate("testuser", "wrongpassword")

        assert result is None

    @pytest.mark.asyncio
    async def test_authenticate_returns_user_on_success(
        self, iam_service, mock_iam_repo, sample_user
    ):
        """正确用户名密码返回 User 对象"""
        mock_iam_repo.get_by_username.return_value = sample_user

        with patch("app.modules.iam.services.iam_service.verify_password", return_value=True):
            result = await iam_service.authenticate("testuser", "correctpassword")

        assert result is sample_user


# ─── register_user() ───────────────────────────────────────────────────────

class TestRegisterUser:
    """用户注册业务规则"""

    @pytest.mark.asyncio
    async def test_register_raises_when_username_exists(
        self, iam_service, mock_iam_repo, sample_user
    ):
        """用户名已存在时抛 ValidationException"""
        mock_iam_repo.get_by_username.return_value = sample_user

        user_in = UserCreate(
            username="testuser",
            email="new@example.com",
            password="Password123!",
        )

        with pytest.raises(ValidationException) as exc_info:
            await iam_service.register_user(user_in)

        assert "用户名已存在" in str(exc_info.value.message)

    @pytest.mark.asyncio
    async def test_register_creates_user_successfully(
        self, iam_service, mock_iam_repo, sample_user
    ):
        """正常注册流程"""
        mock_iam_repo.get_by_username.return_value = None  # 用户不存在
        mock_iam_repo.create.return_value = sample_user

        user_in = UserCreate(
            username="newuser",
            email="new@example.com",
            password="Password123!",
        )

        with patch("app.modules.iam.services.iam_service.get_password_hash", return_value="hashed"):
            result = await iam_service.register_user(user_in)

        assert result is sample_user
        mock_iam_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_hashes_password(
        self, iam_service, mock_iam_repo, sample_user
    ):
        """注册时密码必须经过哈希，不能明文存储"""
        mock_iam_repo.get_by_username.return_value = None
        mock_iam_repo.create.return_value = sample_user

        user_in = UserCreate(
            username="newuser",
            email="new@example.com",
            password="PlainTextPassword",
        )

        with patch("app.modules.iam.services.iam_service.get_password_hash") as mock_hash:
            mock_hash.return_value = "bcrypt_hashed_value"
            await iam_service.register_user(user_in)

            # 验证 hash 函数被调用（密码不应明文传给 repository）
            mock_hash.assert_called_once_with("PlainTextPassword")
            # 验证传给 repository 的是哈希值
            create_call_kwargs = mock_iam_repo.create.call_args
            assert create_call_kwargs[0][1] == "bcrypt_hashed_value"


# ─── delete_user() ─────────────────────────────────────────────────────────

class TestDeleteUser:
    """软删除逻辑"""

    @pytest.mark.asyncio
    async def test_delete_sets_is_deleted_flag(
        self, iam_service, mock_iam_repo, sample_user
    ):
        """删除用户应设置 is_deleted=True，而非真正删除数据库记录"""
        mock_iam_repo.get_by_id.return_value = sample_user
        mock_iam_repo.save.return_value = sample_user

        result = await iam_service.delete_user(sample_user.id)

        assert result is True
        assert sample_user.is_deleted is True

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, iam_service, mock_iam_repo
    ):
        """用户不存在时返回 False"""
        mock_iam_repo.get_by_id.return_value = None

        result = await iam_service.delete_user(uuid.uuid4())

        assert result is False
