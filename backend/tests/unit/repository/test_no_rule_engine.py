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
