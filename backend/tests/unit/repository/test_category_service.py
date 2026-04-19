import uuid
import pytest
from app.modules.repository.schemas.category import CategoryCreate, CategoryRead


def test_category_create_schema_valid():
    data = CategoryCreate(code="TEST", name="测试门类")
    assert data.code == "TEST"
    assert data.is_builtin is False


def test_category_create_schema_requires_code():
    with pytest.raises(Exception):
        CategoryCreate(name="无代码门类")  # code 必填


def test_category_read_schema():
    data = CategoryRead(
        id=uuid.uuid4(),
        code="WS",
        name="文书档案",
        is_builtin=True,
        requires_privacy_guard=False,
        field_schema=None,
    )
    assert data.code == "WS"
