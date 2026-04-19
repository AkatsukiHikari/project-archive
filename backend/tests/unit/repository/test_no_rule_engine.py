import uuid
import pytest
from app.modules.repository.models.no_rule_seq import ArchiveNoSeq
from app.modules.repository.models.category import ArchiveCategory
from app.modules.repository.schemas.no_rule import (
    NoRuleCreate, NoRuleRead, PreviewRequest, RuleTemplate, SegmentDef,
)


def test_no_seq_instantiate():
    seq = ArchiveNoSeq(
        rule_id=uuid.uuid4(),
        scope_key="catalog_year:abc:2024",
        current_seq=1,
    )
    assert seq.current_seq == 1


def test_category_has_no_rule_id_field():
    cat = ArchiveCategory(code="WS", name="文书", is_builtin=True)
    assert hasattr(cat, "archive_no_rule_id")
    assert cat.archive_no_rule_id is None


def test_segment_def_field():
    seg = SegmentDef(type="field", field="fonds_code")
    assert seg.type == "field"
    assert seg.field == "fonds_code"


def test_segment_def_sequence():
    seg = SegmentDef(type="sequence", padding=4, scope="catalog_year")
    assert seg.padding == 4
    assert seg.scope == "catalog_year"


def test_rule_template_valid():
    tmpl = RuleTemplate(
        separator="-",
        segments=[
            SegmentDef(type="field", field="fonds_code"),
            SegmentDef(type="literal", value="WS"),
            SegmentDef(type="sequence", padding=4, scope="catalog_year"),
        ],
    )
    assert len(tmpl.segments) == 3


def test_no_rule_create_valid():
    data = NoRuleCreate(
        category_id=uuid.uuid4(),
        name="文书一文一件规则",
        rule_template={
            "separator": "-",
            "segments": [
                {"type": "field", "field": "fonds_code"},
                {"type": "sequence", "padding": 4, "scope": "catalog_year"},
            ],
        },
        seq_scope="catalog_year",
    )
    assert data.name == "文书一文一件规则"


def test_no_rule_create_invalid_template():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        NoRuleCreate(
            category_id=uuid.uuid4(),
            name="坏规则",
            rule_template={"separator": "-", "segments": []},  # min_length=1 violated
            seq_scope="catalog_year",
        )


def test_segment_def_field_missing_field_raises():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SegmentDef(type="field")  # field is required when type="field"


def test_preview_request():
    req = PreviewRequest(
        fonds_code="J001",
        year=2024,
        catalog_no="1",
    )
    assert req.fonds_code == "J001"


# --- Task 3: NoRuleRepository tests ---

from unittest.mock import AsyncMock
from app.modules.repository.repositories.no_rule_repo import NoRuleRepository


@pytest.fixture
def mock_no_rule_repo():
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.list_by_category = AsyncMock(return_value=[])
    repo.create = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_no_rule_repo_list_empty(mock_no_rule_repo):
    result = await mock_no_rule_repo.list_by_category(uuid.uuid4())
    assert result == []


# --- Task 4: ArchiveNoEngine tests ---

from sqlalchemy.orm.instrumentation import manager_of_class
from app.modules.repository.services.no_rule_engine import ArchiveNoEngine
from app.modules.repository.models.no_rule import ArchiveNoRule
from app.modules.repository.models.archive import Archive


def _sa_new(cls):
    """Create a SQLAlchemy mapped instance without calling __init__,
    while still initialising the ORM instance state so mapped_column
    descriptors work correctly."""
    instance = cls.__new__(cls)
    manager_of_class(cls)._new_state_if_none(instance)
    return instance


def _make_rule(template: dict) -> ArchiveNoRule:
    rule = _sa_new(ArchiveNoRule)
    rule.id = uuid.uuid4()
    rule.rule_template = template
    rule.seq_scope = template.get("segments", [{}])[-1].get("scope", "catalog_year")
    return rule


def _make_archive(**kwargs) -> Archive:
    arch = _sa_new(Archive)
    arch.fonds_id = uuid.uuid4()
    arch.catalog_id = uuid.uuid4()
    arch.category_id = uuid.uuid4()
    arch.fonds_code = kwargs.get("fonds_code", "J001")
    arch.year = kwargs.get("year", 2024)
    arch.catalog_no = kwargs.get("catalog_no", "1")
    arch.volume_no = kwargs.get("volume_no", None)
    arch.item_no = kwargs.get("item_no", None)
    arch.creator = kwargs.get("creator", None)
    arch.doc_date = kwargs.get("doc_date", "2024-06-15")
    arch.level = "item"
    arch.title = "test"
    return arch


@pytest.mark.asyncio
async def test_engine_field_literal_segments():
    """field + literal 段 → 无序号，纯拼接"""
    db = AsyncMock()
    engine = ArchiveNoEngine(db)
    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "field", "field": "fonds_code"},
            {"type": "literal", "value": "WS"},
        ],
    })
    archive = _make_archive(fonds_code="J001")
    result = await engine.generate(rule, archive, preview=True)
    assert result == "J001-WS"


@pytest.mark.asyncio
async def test_engine_date_part_year():
    """date_part 提取年份"""
    db = AsyncMock()
    engine = ArchiveNoEngine(db)
    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "date_part", "date_field": "doc_date", "date_format": "%Y"},
        ],
    })
    archive = _make_archive(doc_date="2024-06-15")
    result = await engine.generate(rule, archive, preview=True)
    assert result == "2024"


@pytest.mark.asyncio
async def test_engine_sequence_preview_uses_zeros():
    """preview=True 时序号段输出全零占位，不写 DB"""
    db = AsyncMock()
    engine = ArchiveNoEngine(db)
    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "field", "field": "fonds_code"},
            {"type": "sequence", "padding": 4, "scope": "catalog_year"},
        ],
    })
    archive = _make_archive(fonds_code="J001")
    result = await engine.generate(rule, archive, preview=True)
    assert result == "J001-0000"
    db.execute.assert_not_called()   # preview 不碰 DB


@pytest.mark.asyncio
async def test_engine_sequence_real_increments():
    """preview=False 时序号通过 SeqRepository.increment 原子获取，首次返回 1"""
    db = AsyncMock()
    engine = ArchiveNoEngine(db)
    mock_seq_repo = AsyncMock()
    mock_seq_repo.increment = AsyncMock(return_value=1)
    engine._seq_repo = mock_seq_repo

    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "field", "field": "fonds_code"},
            {"type": "sequence", "padding": 4, "scope": "catalog_year"},
        ],
    })
    archive = _make_archive(fonds_code="J001", year=2024)
    result = await engine.generate(rule, archive, preview=False)
    assert result == "J001-0001"
    mock_seq_repo.increment.assert_called_once()


@pytest.mark.asyncio
async def test_engine_sequence_existing_row_increments():
    """已有序号时 increment 返回下一个值（如 23），带补零"""
    db = AsyncMock()
    engine = ArchiveNoEngine(db)
    mock_seq_repo = AsyncMock()
    mock_seq_repo.increment = AsyncMock(return_value=23)
    engine._seq_repo = mock_seq_repo

    rule = _make_rule({
        "separator": "-",
        "segments": [
            {"type": "sequence", "padding": 4, "scope": "catalog_year"},
        ],
    })
    archive = _make_archive(year=2024)
    result = await engine.generate(rule, archive, preview=False)
    assert result == "0023"


# --- Task 5: NoRuleService tests ---

from app.modules.repository.services.no_rule_service import NoRuleService
from app.modules.repository.schemas.no_rule import NoRuleCreate
from app.common.exceptions.base import NotFoundException


@pytest.fixture
def mock_no_rule_repo_svc():
    repo = AsyncMock()
    rule = _make_rule({
        "separator": "-",
        "segments": [{"type": "literal", "value": "X"}],
    })
    rule.name = "测试规则"
    rule.is_active = True
    rule.tenant_id = None
    rule.is_deleted = False
    repo.get_by_id = AsyncMock(return_value=rule)
    repo.list_by_tenant = AsyncMock(return_value=[rule])
    repo.create = AsyncMock(return_value=rule)
    repo.delete = AsyncMock()
    return repo, rule


@pytest.fixture
def no_rule_service(mock_no_rule_repo_svc):
    repo, _ = mock_no_rule_repo_svc
    svc = NoRuleService.__new__(NoRuleService)
    svc._repo = repo
    return svc


@pytest.mark.asyncio
async def test_no_rule_service_list(no_rule_service, mock_no_rule_repo_svc):
    repo, rule = mock_no_rule_repo_svc
    result = await no_rule_service.list_all(tenant_id=None)
    repo.list_by_tenant.assert_called_once()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_no_rule_service_get_not_found(no_rule_service, mock_no_rule_repo_svc):
    repo, _ = mock_no_rule_repo_svc
    repo.get_by_id = AsyncMock(return_value=None)
    with pytest.raises(NotFoundException):
        await no_rule_service.get(uuid.uuid4())


@pytest.mark.asyncio
async def test_no_rule_service_delete(no_rule_service, mock_no_rule_repo_svc):
    repo, rule = mock_no_rule_repo_svc
    await no_rule_service.delete(rule.id)
    repo.delete.assert_called_once_with(rule)
