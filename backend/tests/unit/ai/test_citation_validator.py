"""引用校验器单测。"""
from __future__ import annotations

import uuid

import pytest

from app.modules.ai.services.citation_validator import CitationValidator


TENANT_A = uuid.uuid4()
TENANT_B = uuid.uuid4()


def _chunk(
    chunk_id: str = "c1",
    *,
    tenant: uuid.UUID | str = TENANT_A,
    level: int = 0,
    source: str = "meta",
) -> dict:
    return {
        "chunk_id": chunk_id,
        "source_type": source,
        "source_id": "a-1",
        "tenant_id": str(tenant),
        "secret_level": level,
    }


@pytest.mark.unit
def test_empty_citations_pass_when_not_required() -> None:
    v = CitationValidator(tenant_id=TENANT_A, user_secret_level=3, require_citation=False)
    outcome = v.validate([])
    assert outcome.valid
    assert outcome.accepted == ()
    assert outcome.rejected == ()


@pytest.mark.unit
def test_empty_citations_fail_when_required() -> None:
    v = CitationValidator(tenant_id=TENANT_A, user_secret_level=3, require_citation=True)
    outcome = v.validate([])
    assert not outcome.valid
    assert outcome.reason is not None and "未携带引用" in outcome.reason


@pytest.mark.unit
def test_all_chunks_valid_passes() -> None:
    v = CitationValidator(tenant_id=TENANT_A, user_secret_level=3, require_citation=True)
    outcome = v.validate([_chunk("c1"), _chunk("c2", level=2)])
    assert outcome.valid
    assert len(outcome.accepted) == 2
    assert outcome.rejected == ()


@pytest.mark.unit
def test_cross_tenant_chunk_rejected_one_vote_kills_all() -> None:
    v = CitationValidator(tenant_id=TENANT_A, user_secret_level=3, require_citation=True)
    outcome = v.validate([_chunk("c1"), _chunk("c2", tenant=TENANT_B)])
    assert not outcome.valid
    assert "c2" in outcome.rejected
    # 一票否决：即使 c1 合规，整体也不放行
    assert outcome.reason is not None and "越权" in outcome.reason


@pytest.mark.unit
def test_higher_secret_level_chunk_rejected() -> None:
    v = CitationValidator(tenant_id=TENANT_A, user_secret_level=1, require_citation=True)
    outcome = v.validate([_chunk("c1", level=2)])
    assert not outcome.valid
    assert outcome.rejected == ("c1",)


@pytest.mark.unit
def test_missing_required_keys_rejected() -> None:
    v = CitationValidator(tenant_id=TENANT_A, user_secret_level=3, require_citation=True)
    outcome = v.validate([{"chunk_id": "c1"}])  # 缺 source_type
    assert not outcome.valid
    assert "c1" in outcome.rejected


@pytest.mark.unit
def test_equal_level_chunk_passes() -> None:
    v = CitationValidator(tenant_id=TENANT_A, user_secret_level=2, require_citation=True)
    outcome = v.validate([_chunk("c1", level=2)])
    assert outcome.valid
