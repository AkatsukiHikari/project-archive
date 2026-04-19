import uuid
import pytest
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.models.archive import Catalog, Archive


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
        org_mode="by_item",
    )
    assert cat.org_mode == "by_item"
    assert cat.catalog_no == "1"


def test_archive_instantiate():
    arch = Archive(
        fonds_id=uuid.uuid4(),
        catalog_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        level="item",
        title="关于XXX的通知",
        year=2024,
        fonds_code="J001",
        status="active",
    )
    assert arch.level == "item"
    assert arch.status == "active"
    assert arch.title == "关于XXX的通知"
    assert arch.fonds_code == "J001"


def test_archive_volume_level():
    vol = Archive(
        fonds_id=uuid.uuid4(),
        catalog_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        level="volume",
        title="2024年文书案卷001",
        fonds_code="J001",
        status="active",
    )
    assert vol.level == "volume"
    assert vol.parent_id is None
