import uuid

import pytest

from app.modules.repository.models.archive import ArchiveStaging, Catalog
from app.modules.repository.models.category import ArchiveCategory


def test_archive_category_instantiate():
    cat = ArchiveCategory(code="WS", name="文书档案", is_builtin=True, requires_privacy_guard=False)
    assert cat.code == "WS"
    assert cat.is_builtin is True
    assert cat.requires_privacy_guard is False


def test_catalog_instantiate():
    cat = Catalog(
        fonds_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        catalog_no="1",
        name="2024年度文书目录",
        year=2024,
        catalog_type="一文一件",
    )
    assert cat.catalog_type == "一文一件"
    assert cat.catalog_no == "1"


def test_catalog_case_volume():
    cat = Catalog(
        fonds_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        catalog_no="2",
        name="2024年案卷目录",
        year=2024,
        catalog_type="案卷目录",
    )
    assert cat.catalog_type == "案卷目录"
    assert cat.volume_archive_id is None


def test_archive_staging_instantiate():
    arch = ArchiveStaging(
        fonds_id=uuid.uuid4(),
        catalog_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        QZH="J001",
        TM="关于XXX的通知",
        ND=2024,
        status="draft",
    )
    assert arch.status == "draft"
    assert arch.TM == "关于XXX的通知"
    assert arch.QZH == "J001"


def test_archive_staging_default_status():
    arch = ArchiveStaging(
        fonds_id=uuid.uuid4(),
        catalog_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        QZH="J001",
        TM="test",
    )
    assert arch.MJ == "public"
    assert arch.BGQX == "permanent"
