import uuid
import pytest
from app.modules.repository.models.no_rule_seq import ArchiveNoSeq
from app.modules.repository.models.category import ArchiveCategory


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
