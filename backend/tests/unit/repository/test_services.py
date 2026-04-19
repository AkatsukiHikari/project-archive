import uuid
import pytest
from unittest.mock import AsyncMock
from app.modules.repository.services.category_service import CategoryService
from app.modules.repository.schemas.category import CategoryCreate
from app.modules.repository.models.category import ArchiveCategory
from app.common.exceptions.base import NotFoundException, ValidationException


@pytest.fixture
def mock_category_repo():
    repo = AsyncMock()
    repo.get_by_code = AsyncMock(return_value=None)
    repo.get_by_id = AsyncMock(return_value=None)
    repo.create = AsyncMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def category_service(mock_category_repo):
    service = CategoryService.__new__(CategoryService)
    service._repo = mock_category_repo
    return service


@pytest.mark.asyncio
async def test_create_category_success(category_service, mock_category_repo):
    mock_category_repo.create.return_value = ArchiveCategory(
        id=uuid.uuid4(), code="CUSTOM", name="自定义门类",
        is_builtin=False, requires_privacy_guard=False
    )
    result = await category_service.create(
        CategoryCreate(code="CUSTOM", name="自定义门类"), tenant_id=uuid.uuid4()
    )
    mock_category_repo.create.assert_called_once()
    assert result.code == "CUSTOM"


@pytest.mark.asyncio
async def test_create_category_duplicate_code_raises(category_service, mock_category_repo):
    mock_category_repo.get_by_code.return_value = ArchiveCategory(
        id=uuid.uuid4(), code="WS", name="文书档案",
        is_builtin=True, requires_privacy_guard=False
    )
    with pytest.raises(ValidationException):
        await category_service.create(
            CategoryCreate(code="WS", name="重复"), tenant_id=uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_delete_builtin_category_raises(category_service, mock_category_repo):
    builtin = ArchiveCategory(
        id=uuid.uuid4(), code="WS", name="文书档案",
        is_builtin=True, requires_privacy_guard=False
    )
    mock_category_repo.get_by_id.return_value = builtin
    with pytest.raises(ValidationException):
        await category_service.delete(builtin.id)


@pytest.mark.asyncio
async def test_delete_nonexistent_raises(category_service, mock_category_repo):
    mock_category_repo.get_by_id.return_value = None
    with pytest.raises(NotFoundException):
        await category_service.delete(uuid.uuid4())
