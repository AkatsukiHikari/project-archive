import uuid
import pytest
from app.modules.repository.schemas.archive import (
    CatalogCreate, CatalogRead, ArchiveCreate, ArchiveRead
)


def test_catalog_create_valid():
    cat = CatalogCreate(
        fonds_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        catalog_no="1",
        name="2024文书目录",
        year=2024,
        org_mode="by_item",
    )
    assert cat.org_mode == "by_item"


def test_catalog_create_invalid_org_mode():
    with pytest.raises(Exception):
        CatalogCreate(
            fonds_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            catalog_no="1",
            name="X",
            org_mode="invalid_mode",
        )


def test_archive_create_requires_title():
    with pytest.raises(Exception):
        ArchiveCreate(
            fonds_id=uuid.uuid4(),
            catalog_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            level="item",
            fonds_code="J001",
            # title 缺失
        )


def test_archive_create_valid():
    arch = ArchiveCreate(
        fonds_id=uuid.uuid4(),
        catalog_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        level="item",
        title="关于XXX的通知",
        fonds_code="J001",
        year=2024,
        creator="国务院",
    )
    assert arch.level == "item"
    assert arch.security_level == "public"
    assert arch.retention_period == "permanent"
