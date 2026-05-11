import uuid
import pytest
from pydantic import ValidationError
from app.modules.repository.schemas.archive import (
    CatalogCreate, CatalogRead, ArchiveCreate, ArchiveRead,
)


def test_catalog_create_valid():
    cat = CatalogCreate(
        fonds_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        catalog_no="1",
        name="2024文书目录",
        year=2024,
        catalog_type="一文一件",
    )
    assert cat.catalog_type == "一文一件"


def test_catalog_create_invalid_catalog_type():
    with pytest.raises(ValidationError):
        CatalogCreate(
            fonds_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            catalog_no="1",
            name="X",
            catalog_type="invalid_type",  # type: ignore[arg-type]
        )


def test_catalog_create_volume_type():
    cid = uuid.uuid4()
    cat = CatalogCreate(
        fonds_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        catalog_no="2",
        name="2024案卷目录",
        year=2024,
        catalog_type="案卷目录",
        volume_archive_id=cid,
    )
    assert cat.catalog_type == "案卷目录"
    assert cat.volume_archive_id == cid


def test_archive_create_requires_title():
    with pytest.raises(ValidationError):
        ArchiveCreate(
            fonds_id=uuid.uuid4(),
            catalog_id=uuid.uuid4(),
            category_id=uuid.uuid4(),
            QZH="J001",
            # TM 缺失 → ValidationError
        )


def test_archive_create_valid():
    arch = ArchiveCreate(
        fonds_id=uuid.uuid4(),
        catalog_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        TM="关于XXX的通知",
        QZH="J001",
        ND=2024,
        RZZ="国务院",
    )
    assert arch.TM == "关于XXX的通知"
    assert arch.MJ == "public"
    assert arch.BGQX == "permanent"
