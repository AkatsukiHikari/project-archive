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
    """preview=False 时序号从 SeqRepository 取，并返回带补零的字符串"""
    db = AsyncMock()
    # 模拟 get_and_lock 返回 None（首次），create_seq 返回 seq=1
    from app.modules.repository.models.no_rule_seq import ArchiveNoSeq
    seq_row = _sa_new(ArchiveNoSeq)
    seq_row.current_seq = 1

    engine = ArchiveNoEngine(db)
    # 注入 mock SeqRepository
    mock_seq_repo = AsyncMock()
    mock_seq_repo.get_and_lock = AsyncMock(return_value=None)
    mock_seq_repo.create_seq = AsyncMock(return_value=seq_row)
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
    mock_seq_repo.create_seq.assert_called_once()


@pytest.mark.asyncio
async def test_engine_sequence_existing_row_increments():
    """已有序号行时递增后返回新值"""
    db = AsyncMock()
    from app.modules.repository.models.no_rule_seq import ArchiveNoSeq
    seq_row = _sa_new(ArchiveNoSeq)
    seq_row.current_seq = 22   # 已有 22，下一个应为 23

    engine = ArchiveNoEngine(db)
    mock_seq_repo = AsyncMock()
    mock_seq_repo.get_and_lock = AsyncMock(return_value=seq_row)
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
    assert seq_row.current_seq == 23
