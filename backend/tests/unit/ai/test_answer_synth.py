"""答案合成器单测（无 Dify 兜底分支）。"""
from __future__ import annotations

import uuid

import pytest

from app.modules.ai.services.answer_synth import synthesize_answer
from app.modules.ai.services.retrieval_service import RetrievedChunk


def _chunk(
    src_type: str = "rule",
    title: str = "永久保管期限定义",
    snippet: str = "永久保管的档案是指对国家、社会、本机关具有长远利用价值的档案。",
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=f"{src_type}:t",
        source_type=src_type,
        source_id="x",
        title=title,
        snippet=snippet,
        score=10.0,
        secret_level=0,
        tenant_id="__shared__",
    )


@pytest.mark.unit
def test_no_chunks_refuses() -> None:
    out = synthesize_answer(query="档案保管期限", chunks=[])
    assert "未在知识库" in out
    assert "请尝试换" in out


@pytest.mark.unit
def test_single_rule_renders_quote_form() -> None:
    out = synthesize_answer(query="永久保管", chunks=[_chunk()])
    assert "《永久保管期限定义》" in out
    assert "长远利用价值" in out


@pytest.mark.unit
def test_multiple_rules_numbered() -> None:
    chunks = [
        _chunk(title="规则一", snippet="aaa"),
        _chunk(title="规则二", snippet="bbb"),
        _chunk(title="规则三", snippet="ccc"),
    ]
    out = synthesize_answer(query="保管期限", chunks=chunks)
    assert "1. **规则一**" in out
    assert "2. **规则二**" in out
    assert "3. **规则三**" in out


@pytest.mark.unit
def test_rules_capped_at_three() -> None:
    chunks = [_chunk(title=f"规则{i}") for i in range(5)]
    out = synthesize_answer(query="q", chunks=chunks)
    assert "**规则3**" not in out  # 0-indexed → 第 4 条
    assert "**规则2**" in out      # 第 3 条还在


@pytest.mark.unit
def test_meta_only_renders_archive_list() -> None:
    chunks = [_chunk(src_type="meta", title="X-001 财务凭证", snippet="A001 / 2024")]
    out = synthesize_answer(query="财务", chunks=chunks)
    assert "找到以下相关档案" in out
    assert "X-001 财务凭证" in out


@pytest.mark.unit
def test_rules_and_metas_both_rendered() -> None:
    chunks = [
        _chunk(src_type="rule"),
        _chunk(src_type="meta", title="档案1", snippet=""),
    ]
    out = synthesize_answer(query="q", chunks=chunks)
    assert "《永久保管期限定义》" in out
    assert "相关档案" in out
    assert "档案1" in out


@pytest.mark.unit
def test_footer_disclaimer_always_present_when_hits() -> None:
    out = synthesize_answer(query="q", chunks=[_chunk()])
    assert "未经大模型重述" in out
