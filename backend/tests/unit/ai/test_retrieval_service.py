"""retrieval_service ES 实装单测（mock ES 客户端）。"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.ai.services.retrieval_service import (
    RetrievalService,
    RetrieveFilter,
    _allowed_mj,
)


@pytest.mark.unit
def test_allowed_mj_low_level_only_public() -> None:
    allowed = _allowed_mj(0)
    assert "public" in allowed
    assert "秘密" not in allowed
    assert "绝密" not in allowed


@pytest.mark.unit
def test_allowed_mj_top_level_sees_all() -> None:
    allowed = _allowed_mj(4)
    for v in ("public", "秘密", "机密", "绝密"):
        assert v in allowed


@pytest.mark.unit
def test_allowed_mj_clamped() -> None:
    # 超出 [0,4] 不应抛错
    assert "public" in _allowed_mj(-1)
    assert "绝密" in _allowed_mj(99)


def _filt(tenant: uuid.UUID, level: int = 2) -> RetrieveFilter:
    return RetrieveFilter(
        tenant_id=tenant, secret_level=level, user_id=uuid.uuid4()
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_meta_query_injects_tenant_and_mj_filter() -> None:
    tenant = uuid.uuid4()
    fake_client = AsyncMock()
    fake_client.search.return_value = {"hits": {"hits": []}}

    captured_body: dict = {}

    async def _capture(*, index, body, **_kw):
        nonlocal captured_body
        captured_body = body
        return {"hits": {"hits": []}}

    fake_client.search = _capture  # type: ignore[assignment]

    with patch(
        "app.modules.ai.services.retrieval_service.get_es_client",
        return_value=fake_client,
    ):
        svc = RetrievalService(db=None)  # type: ignore[arg-type]
        out = await svc.retrieve(
            query="财务凭证", kb_type="meta", top_k=5, filt=_filt(tenant, level=2)
        )

    assert out == []
    filters = captured_body["query"]["bool"]["filter"]
    # 必须有 tenant_id 过滤
    assert {"term": {"tenant_id": str(tenant)}} in filters
    # MJ 列表必须按 level 限制（不应包含机密 / 绝密）
    mj_clause = next(f for f in filters if "terms" in f and "MJ" in f["terms"])
    mj_values = set(mj_clause["terms"]["MJ"])
    assert "公开" in mj_values and "秘密" in mj_values
    assert "机密" not in mj_values and "绝密" not in mj_values


@pytest.mark.unit
@pytest.mark.asyncio
async def test_meta_query_es_failure_returns_empty() -> None:
    tenant = uuid.uuid4()
    fake_client = AsyncMock()
    fake_client.search.side_effect = RuntimeError("ES down")

    with patch(
        "app.modules.ai.services.retrieval_service.get_es_client",
        return_value=fake_client,
    ):
        svc = RetrievalService(db=None)  # type: ignore[arg-type]
        out = await svc.retrieve(
            query="q", kb_type="meta", top_k=5, filt=_filt(tenant)
        )
    assert out == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_meta_hits_mapped_to_retrieved_chunks() -> None:
    tenant = uuid.uuid4()
    fake_client = AsyncMock()
    fake_client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "a-1",
                    "_score": 7.5,
                    "_source": {
                        "id": "a-1",
                        "DH": "X-001",
                        "QZH": "Q1",
                        "TM": "测试题名",
                        "ND": 2024,
                        "MJ": "公开",
                        "catalog_id": "c-1",
                        "tenant_id": str(tenant),
                    },
                }
            ]
        }
    }
    with patch(
        "app.modules.ai.services.retrieval_service.get_es_client",
        return_value=fake_client,
    ):
        svc = RetrievalService(db=None)  # type: ignore[arg-type]
        out = await svc.retrieve(
            query="q", kb_type="meta", top_k=5, filt=_filt(tenant)
        )

    assert len(out) == 1
    chunk = out[0]
    assert chunk.chunk_id == "meta:a-1"
    assert chunk.source_type == "meta"
    assert chunk.source_id == "a-1"
    assert chunk.title == "测试题名"
    assert chunk.score == 7.5
    assert chunk.tenant_id == str(tenant)
    assert chunk.secret_level == 0  # 公开
    assert chunk.category_id == "c-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_post_filter_drops_cross_tenant_or_higher_level_results() -> None:
    """即使 ES 异常返回了越权数据，二次防御也应拦截。"""
    tenant = uuid.uuid4()
    other = uuid.uuid4()
    fake_client = AsyncMock()
    fake_client.search.return_value = {
        "hits": {
            "hits": [
                {  # 跨租户
                    "_id": "x",
                    "_score": 1.0,
                    "_source": {"id": "x", "TM": "x", "MJ": "public", "tenant_id": str(other)},
                },
                {  # 越级密级
                    "_id": "y",
                    "_score": 1.0,
                    "_source": {"id": "y", "TM": "y", "MJ": "绝密", "tenant_id": str(tenant)},
                },
                {  # 合规
                    "_id": "z",
                    "_score": 1.0,
                    "_source": {"id": "z", "TM": "z", "MJ": "公开", "tenant_id": str(tenant)},
                },
            ]
        }
    }
    with patch(
        "app.modules.ai.services.retrieval_service.get_es_client",
        return_value=fake_client,
    ):
        svc = RetrievalService(db=None)  # type: ignore[arg-type]
        out = await svc.retrieve(
            query="q", kb_type="meta", top_k=5, filt=_filt(tenant, level=1)
        )
    ids = {c.source_id for c in out}
    assert ids == {"z"}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ocr_returns_empty() -> None:
    svc = RetrievalService(db=None)  # type: ignore[arg-type]
    out_ocr = await svc.retrieve(
        query="q", kb_type="ocr", top_k=5, filt=_filt(uuid.uuid4())
    )
    assert out_ocr == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rules_query_allows_shared_tenant() -> None:
    tenant = uuid.uuid4()
    fake_client = AsyncMock()
    captured: dict = {}

    async def _capture(*, index, body, **_kw):
        captured.update({"index": index, "body": body})
        return {"hits": {"hits": []}}

    fake_client.search = _capture  # type: ignore[assignment]
    with patch(
        "app.modules.ai.services.retrieval_service.get_es_client",
        return_value=fake_client,
    ):
        svc = RetrievalService(db=None)  # type: ignore[arg-type]
        await svc.retrieve(
            query="永久保管", kb_type="rules", top_k=3, filt=_filt(tenant, level=2)
        )
    assert captured["index"] == "sams_ai_rules"
    filters = captured["body"]["query"]["bool"]["filter"]
    tenant_clause = next(f for f in filters if "terms" in f and "tenant_id" in f["terms"])
    assert "__shared__" in tenant_clause["terms"]["tenant_id"]
    assert str(tenant) in tenant_clause["terms"]["tenant_id"]
    # secret_level 范围过滤
    range_clause = next(f for f in filters if "range" in f and "secret_level" in f["range"])
    assert range_clause["range"]["secret_level"]["lte"] == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rules_hits_map_to_rule_chunks() -> None:
    tenant = uuid.uuid4()
    fake_client = AsyncMock()
    fake_client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "retention.permanent",
                    "_score": 28.9,
                    "_source": {
                        "rule_id": "retention.permanent",
                        "tenant_id": "__shared__",
                        "category": "retention",
                        "title": "永久保管期限定义",
                        "content": "x" * 200,
                        "tags": ["BGQX", "永久"],
                        "source": "DA/T 15-2023",
                        "version": "v2024.01",
                        "secret_level": 0,
                    },
                }
            ]
        }
    }
    with patch(
        "app.modules.ai.services.retrieval_service.get_es_client",
        return_value=fake_client,
    ):
        svc = RetrievalService(db=None)  # type: ignore[arg-type]
        out = await svc.retrieve(
            query="永久", kb_type="rules", top_k=3, filt=_filt(tenant, level=2)
        )
    assert len(out) == 1
    chunk = out[0]
    assert chunk.chunk_id == "rule:retention.permanent"
    assert chunk.source_type == "rule"
    assert chunk.tenant_id == "__shared__"
    assert chunk.snippet.endswith("…")
    assert chunk.extra["source"] == "DA/T 15-2023"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shared_tenant_chunk_survives_post_filter() -> None:
    """二次防御应放行 __shared__ 租户的规则。"""
    tenant = uuid.uuid4()
    fake_client = AsyncMock()
    fake_client.search.return_value = {
        "hits": {
            "hits": [
                {
                    "_id": "r1",
                    "_score": 1.0,
                    "_source": {
                        "rule_id": "r1",
                        "tenant_id": "__shared__",
                        "title": "t",
                        "content": "c",
                        "secret_level": 0,
                    },
                }
            ]
        }
    }
    with patch(
        "app.modules.ai.services.retrieval_service.get_es_client",
        return_value=fake_client,
    ):
        svc = RetrievalService(db=None)  # type: ignore[arg-type]
        out = await svc.retrieve(
            query="q", kb_type="rules", top_k=3, filt=_filt(tenant)
        )
    assert len(out) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rules_es_failure_returns_empty() -> None:
    fake_client = AsyncMock()
    fake_client.search.side_effect = RuntimeError("nope")
    with patch(
        "app.modules.ai.services.retrieval_service.get_es_client",
        return_value=fake_client,
    ):
        svc = RetrievalService(db=None)  # type: ignore[arg-type]
        out = await svc.retrieve(
            query="q", kb_type="rules", top_k=3, filt=_filt(uuid.uuid4())
        )
    assert out == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_unknown_kb_type_returns_empty() -> None:
    svc = RetrievalService(db=None)  # type: ignore[arg-type]
    out = await svc.retrieve(
        query="q", kb_type="nope", top_k=5, filt=_filt(uuid.uuid4())  # type: ignore[arg-type]
    )
    assert out == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_top_k_clamped_when_out_of_range() -> None:
    fake_client = AsyncMock()
    fake_client.search.return_value = {"hits": {"hits": []}}
    captured = {}

    async def _capture(*, index, body, **_kw):
        captured["size"] = body.get("size")
        return {"hits": {"hits": []}}

    fake_client.search = _capture  # type: ignore[assignment]
    with patch(
        "app.modules.ai.services.retrieval_service.get_es_client",
        return_value=fake_client,
    ):
        svc = RetrievalService(db=None)  # type: ignore[arg-type]
        await svc.retrieve(
            query="q", kb_type="meta", top_k=0, filt=_filt(uuid.uuid4())
        )
    # top_k=0 → 内部 clamp 到 5
    assert captured["size"] == 5
