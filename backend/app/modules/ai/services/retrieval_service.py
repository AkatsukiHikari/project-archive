"""
检索代理：Dify 永远不直连 ES / 向量库

设计稿 §3.2 第 3 条不可破坏约束：检索强制由后端代理，无视 Dify 传入的 tenant/密级/类目
过滤参数，只信 JWT 恢复出来的用户身份。

知识库类型：
- ``meta``  L1 档案元数据全量
- ``rules`` L4 业务规则静态（保管期限表 / 编号规则等）
- ``ocr``   L2 原文 OCR（P3 接入）

P1 阶段先打通"调用 → 注入 filter → 写审计 → 返回"通路，
实际数据源对接（ES / pgvector）留到 P2 在 ``_retrieve_*`` 方法里替换。
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.search.es_client import (
    AI_RULES_INDEX,
    ARCHIVE_INDEX,
    SHARED_TENANT_ID,
    get_es_client,
)

logger = logging.getLogger(__name__)


# 用户 secret_level（int）→ 可见 MJ 字符串集合（DA/T 18 密级）
# 0=公开 / 1=内部 / 2=秘密 / 3=机密 / 4=绝密；按"低看不到高"原则下游降级
_MJ_BY_LEVEL: dict[int, tuple[str, ...]] = {
    0: ("public", "公开"),
    1: ("public", "公开", "internal", "内部"),
    2: ("public", "公开", "internal", "内部", "secret", "秘密"),
    3: ("public", "公开", "internal", "内部", "secret", "秘密", "confidential", "机密"),
    4: ("public", "公开", "internal", "内部", "secret", "秘密", "confidential", "机密", "top_secret", "绝密"),
}


def _allowed_mj(secret_level: int) -> tuple[str, ...]:
    return _MJ_BY_LEVEL.get(max(0, min(secret_level, 4)), _MJ_BY_LEVEL[0])


# MJ 字符串 → 数值密级（用于回传 chunk.secret_level，供 citation_validator 校验）
_MJ_TO_LEVEL: dict[str, int] = {
    "public": 0, "公开": 0,
    "internal": 1, "内部": 1,
    "secret": 2, "秘密": 2,
    "confidential": 3, "机密": 3,
    "top_secret": 4, "绝密": 4,
}


KBType = Literal["meta", "rules", "ocr"]


@dataclass(frozen=True)
class RetrieveFilter:
    """检索强制注入的过滤器（user 视角，Dify 改不了）。"""

    tenant_id: uuid.UUID
    secret_level: int
    user_id: uuid.UUID
    category_ids: tuple[str, ...] = ()
    fonds_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RetrievedChunk:
    """单条检索结果（统一形态）。"""

    chunk_id: str
    source_type: str  # "meta" / "rule" / "ocr"
    source_id: str    # archive_id / rule_id / ...
    title: str
    snippet: str
    score: float
    secret_level: int
    tenant_id: str
    category_id: str | None = None
    extra: dict[str, Any] | None = None


class RetrievalService:
    """检索代理服务。

    用法（在 Tool 回调里）::

        svc = RetrievalService(db)
        filt = RetrieveFilter(tenant_id=..., secret_level=..., user_id=...)
        chunks = await svc.retrieve(query, kb_type="meta", top_k=5, filt=filt)
    """

    def __init__(self, db: AsyncSession):
        self._db = db

    async def retrieve(
        self,
        *,
        query: str,
        kb_type: KBType,
        top_k: int,
        filt: RetrieveFilter,
    ) -> list[RetrievedChunk]:
        if top_k <= 0 or top_k > 50:
            top_k = 5

        if kb_type == "meta":
            raw = await self._retrieve_meta(query=query, top_k=top_k, filt=filt)
        elif kb_type == "rules":
            raw = await self._retrieve_rules(query=query, top_k=top_k, filt=filt)
        elif kb_type == "ocr":
            raw = await self._retrieve_ocr(query=query, top_k=top_k, filt=filt)
        else:
            return []

        # 二次防御：即使 _retrieve_* 实装时漏注 filter，这里也强行兜底
        allowed_tenants = {str(filt.tenant_id), SHARED_TENANT_ID}
        return [
            chunk
            for chunk in raw
            if chunk.tenant_id in allowed_tenants
            and chunk.secret_level <= filt.secret_level
        ][:top_k]

    # ── 各 KB 类型的实装（P1 mock，P2 接 ES/pgvector） ─────────────────

    async def _retrieve_meta(
        self, *, query: str, top_k: int, filt: RetrieveFilter
    ) -> list[RetrievedChunk]:
        """查 ES ``sams_archives`` 索引，强制注入 tenant_id + MJ 允许列表。"""
        client = get_es_client()
        allowed = list(_allowed_mj(filt.secret_level))
        es_query: dict[str, Any] = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["TM^3", "RZZ^2"],
                                "type": "best_fields",
                                "fuzziness": "AUTO",
                            }
                        }
                    ],
                    "filter": [
                        {"term": {"tenant_id": str(filt.tenant_id)}},
                        {"terms": {"MJ": allowed}},
                    ],
                }
            },
            "size": top_k,
            "_source": [
                "id", "DH", "QZH", "TM", "RZZ", "ND", "MJ",
                "catalog_id", "tenant_id",
            ],
        }

        try:
            resp = await client.search(index=ARCHIVE_INDEX, body=es_query)
        except Exception as exc:
            logger.warning("retrieval.meta ES 查询失败 query=%r: %s", query, exc)
            return []

        hits = resp.get("hits", {}).get("hits", []) or []
        out: list[RetrievedChunk] = []
        for hit in hits:
            src = hit.get("_source", {}) or {}
            mj = src.get("MJ") or "public"
            level = _MJ_TO_LEVEL.get(mj, 0)
            archive_id = str(src.get("id") or hit.get("_id") or "")
            out.append(
                RetrievedChunk(
                    chunk_id=f"meta:{archive_id}",
                    source_type="meta",
                    source_id=archive_id,
                    title=str(src.get("TM") or "(无题名)"),
                    snippet=" / ".join(
                        str(x) for x in (src.get("DH"), src.get("QZH"), src.get("ND")) if x
                    ),
                    score=float(hit.get("_score") or 0.0),
                    secret_level=level,
                    tenant_id=str(src.get("tenant_id") or filt.tenant_id),
                    category_id=str(src.get("catalog_id")) if src.get("catalog_id") else None,
                    extra={"DH": src.get("DH"), "ND": src.get("ND"), "MJ": mj},
                )
            )
        return out

    async def _retrieve_rules(
        self, *, query: str, top_k: int, filt: RetrieveFilter
    ) -> list[RetrievedChunk]:
        """查 ES ``sams_ai_rules`` 索引：全租户共享 + 当前租户私有，按密级过滤。"""
        client = get_es_client()
        es_query: dict[str, Any] = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "multi_match": {
                                "query": query,
                                "fields": ["title^3", "content^2", "tags"],
                                "type": "best_fields",
                                "fuzziness": "AUTO",
                            }
                        }
                    ],
                    "filter": [
                        {
                            "terms": {
                                "tenant_id": [SHARED_TENANT_ID, str(filt.tenant_id)]
                            }
                        },
                        {"range": {"secret_level": {"lte": filt.secret_level}}},
                    ],
                }
            },
            "size": top_k,
            "_source": [
                "rule_id", "category", "title", "content", "tags",
                "source", "version", "tenant_id", "secret_level",
            ],
        }
        try:
            resp = await client.search(index=AI_RULES_INDEX, body=es_query)
        except Exception as exc:
            logger.warning("retrieval.rules ES 查询失败 query=%r: %s", query, exc)
            return []

        hits = resp.get("hits", {}).get("hits", []) or []
        out: list[RetrievedChunk] = []
        for hit in hits:
            src = hit.get("_source", {}) or {}
            rule_id = str(src.get("rule_id") or hit.get("_id") or "")
            content = str(src.get("content") or "")
            snippet = content[:160] + ("…" if len(content) > 160 else "")
            out.append(
                RetrievedChunk(
                    chunk_id=f"rule:{rule_id}",
                    source_type="rule",
                    source_id=rule_id,
                    title=str(src.get("title") or rule_id),
                    snippet=snippet,
                    score=float(hit.get("_score") or 0.0),
                    secret_level=int(src.get("secret_level") or 0),
                    tenant_id=str(src.get("tenant_id") or SHARED_TENANT_ID),
                    category_id=str(src.get("category")) if src.get("category") else None,
                    extra={
                        "source": src.get("source"),
                        "version": src.get("version"),
                        "tags": src.get("tags") or [],
                    },
                )
            )
        return out

    async def _retrieve_ocr(
        self, *, query: str, top_k: int, filt: RetrieveFilter
    ) -> list[RetrievedChunk]:
        # OCR 索引管线 P3 才接入，P1/P2 都是空
        return []
