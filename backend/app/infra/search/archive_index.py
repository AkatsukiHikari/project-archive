"""
档案条目 ES 索引操作封装（v2，使用 DA/T 拼音缩写字段名）

提供：
  - index_item()   — 新增/更新单个档案条目到 ES
  - delete_item()  — 从 ES 删除条目
  - search_items() — 全文检索

设计原则：ES 是 PostgreSQL 的搜索副本，PostgreSQL 是主数据源。
写入失败不阻断业务流程。
"""

import logging
import re
import uuid
from typing import Any

from app.infra.search.es_client import ARCHIVE_INDEX, get_es_client
from app.modules.repository.models.archive import ArchiveStaging

logger = logging.getLogger(__name__)


async def index_item(item: ArchiveStaging) -> None:
    """将暂存档案条目索引到 Elasticsearch（新增或覆盖）。"""
    client = get_es_client()
    doc = {
        "id": str(item.id),
        "doc_source": "staging",
        "DH": item.DH,
        "QZH": item.QZH,
        "TM": item.TM,
        "RZZ": item.RZZ,
        "ND": item.ND,
        "WJRQ": item.WJRQ,
        "MJ": item.MJ,
        "BGQX": item.BGQX,
        "catalog_id": str(item.catalog_id),
        "category_id": str(item.category_id) if item.category_id else None,
        "status": item.status,
        "tenant_id": str(item.tenant_id) if item.tenant_id else None,
        "ext_fields": item.ext_fields,
        "full_text": getattr(item, "full_text", None),
        "create_time": item.create_time.isoformat() if item.create_time else None,
    }
    try:
        await client.index(index=ARCHIVE_INDEX, id=str(item.id), document=doc)
    except Exception as exc:
        logger.warning("ES 索引写入失败 id=%s: %s", item.id, exc)


async def delete_item(item_id: uuid.UUID) -> None:
    """从 ES 删除档案条目。"""
    client = get_es_client()
    try:
        await client.delete(index=ARCHIVE_INDEX, id=str(item_id), ignore=[404])
    except Exception as exc:
        logger.warning("ES 删除失败 id=%s: %s", item_id, exc)


async def search_items(
    query: str,
    tenant_id: str | None = None,
    ND: int | None = None,
    QZH: str | None = None,
    public_only: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """
    档案全文检索：题名 TM、责任者 RZZ、原文 OCR 全文 full_text 多字段匹配。

    用于老档案题名著录不准、按字段查不到时，命中原文内容。
    public_only=True 仅返回无密级（MJ=无）档案，供社会公众查档。

    返回：{"total": N, "hits": [{...source, "score", "highlight"}]}
    """
    client = get_es_client()

    # 标准分词器对中文按单字切分，单字重叠会污染结果；
    # 用 should + match_phrase 让"精确短语"命中排到最前，单字匹配作为兜底召回。
    should_clauses: list[dict] = [
        {"match_phrase": {"full_text": {"query": query, "boost": 8, "slop": 1}}},
        {"match_phrase": {"TM": {"query": query, "boost": 10}}},
        {"match_phrase": {"RZZ": {"query": query, "boost": 6}}},
        {
            "multi_match": {
                "query": query,
                "fields": ["TM^3", "RZZ^2", "full_text"],
                "type": "best_fields",
                "fuzziness": "AUTO",
            }
        },
    ]
    must_clauses: list[dict] = [
        {"bool": {"should": should_clauses, "minimum_should_match": 1}}
    ]

    filter_clauses: list[dict] = []
    if tenant_id:
        filter_clauses.append({"term": {"tenant_id": tenant_id}})
    if public_only:
        filter_clauses.append({"term": {"MJ": "无"}})
    if ND:
        filter_clauses.append({"term": {"ND": ND}})
    if QZH:
        filter_clauses.append({"term": {"QZH": QZH}})

    es_query = {
        "query": {"bool": {"must": must_clauses, "filter": filter_clauses}},
        "highlight": {
            "fields": {
                "TM": {},
                "RZZ": {},
                "full_text": {"fragment_size": 120, "number_of_fragments": 2},
            },
            "pre_tags": ["<em>"],
            "post_tags": ["</em>"],
        },
        "from": skip,
        "size": limit,
        "_source": [
            "id",
            "DH",
            "QZH",
            "TM",
            "RZZ",
            "ND",
            "WJRQ",
            "MJ",
            "BGQX",
            "catalog_id",
            "create_time",
        ],
    }

    try:
        resp = await client.search(index=ARCHIVE_INDEX, body=es_query)
        hits = resp["hits"]["hits"]
        return {
            "total": resp["hits"]["total"]["value"],
            "hits": [
                {
                    **hit["_source"],
                    "score": hit["_score"],
                    "highlight": hit.get("highlight", {}),
                }
                for hit in hits
            ],
        }
    except Exception as exc:
        logger.error("ES 搜索失败 query='%s': %s", query, exc)
        return {"total": 0, "hits": [], "error": "搜索服务暂时不可用"}


# ── 超级查询：字段/全文 + 分面聚合（NDL 风格）────────────────────────────────────

# 分面字段 → ES 聚合字段（结构化字段用 .keyword 子字段，年度为数值）
FACET_FIELDS: dict[str, str] = {
    "QZH": "QZH.keyword",
    "ND": "ND",
    "RZZ": "RZZ.keyword",
    "MJ": "MJ.keyword",
    "BGQX": "BGQX.keyword",
    "category_id": "category_id.keyword",
}

_SUPER_SOURCE = [
    "id",
    "DH",
    "QZH",
    "TM",
    "RZZ",
    "ND",
    "WJRQ",
    "MJ",
    "BGQX",
    "category_id",
    "create_time",
    "doc_source",
]


def _keyword_clause(keyword: str, mode: str) -> dict:
    """字段检索：题名/责任者/档号（精确，不做 token-OR 否则档号会命中全部）；
    全文检索：OCR 原文 full_text（可模糊召回）；
    综合检索(qa)：AI 问答用，档号/题名/全文/责任者(姓名)/全宗号/年度/密级/保管期限 全覆盖。
    均走 ES。"""
    if mode == "qa":
        # AI 问答综合召回：覆盖用户列的全部重要条件（KFZT 开放状态未入 ES，走 DB 统计）
        should = [
            {
                "wildcard": {
                    "DH.keyword": {
                        "value": f"*{keyword}*",
                        "case_insensitive": True,
                        "boost": 12,
                    }
                }
            },
            {"match_phrase": {"TM": {"query": keyword, "boost": 10}}},
            {"match_phrase": {"full_text": {"query": keyword, "boost": 8, "slop": 1}}},
            {
                "multi_match": {
                    "query": keyword,
                    "fields": ["TM^4", "RZZ^3", "full_text^2", "QZH^2", "MJ", "BGQX"],
                    "type": "best_fields",
                }
            },
        ]
        # 年度：从问句抽取 4 位年份，精确匹配 ND
        for y in re.findall(r"(?:19|20)\d{2}", keyword):
            should.append({"term": {"ND": int(y)}})
        return {"bool": {"should": should, "minimum_should_match": 1}}
    if mode == "fulltext":
        # 短语命中排最前；match 分词 OR 召回，保证自然语言提问（如"2024财务"）
        # 也能命中题名"2024年度财务凭证"这类非连续匹配；DH 通配兜底档号查询。
        should = [
            {
                "wildcard": {
                    "DH.keyword": {
                        "value": f"*{keyword}*",
                        "case_insensitive": True,
                        "boost": 12,
                    }
                }
            },
            {"match_phrase": {"full_text": {"query": keyword, "boost": 8, "slop": 1}}},
            {"match": {"full_text": {"query": keyword}}},
            {"match_phrase": {"TM": {"query": keyword, "boost": 4}}},
            {"match": {"TM": {"query": keyword, "boost": 2}}},
        ]
    else:
        # 题名/责任者用短语精确匹配；档号用子串通配（大小写不敏感）。
        should = [
            {"match_phrase": {"TM": {"query": keyword, "boost": 10}}},
            {"match_phrase": {"RZZ": {"query": keyword, "boost": 6}}},
            {
                "wildcard": {
                    "DH.keyword": {
                        "value": f"*{keyword}*",
                        "case_insensitive": True,
                    }
                }
            },
        ]
    return {"bool": {"should": should, "minimum_should_match": 1}}


async def super_search(
    keyword: str | None = None,
    mode: str = "field",
    filters: dict[str, list] | None = None,
    tenant_id: str | None = None,
    public_only: bool = False,
    include_staging: bool = False,
    skip: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """超级查询：关键字(字段/全文) + 分面聚合 + 高亮 + 分页，全部走 ES。

    返回 {"total", "hits": [...highlight], "facets": {field: [{value, count}]}}
    分面在当前过滤(关键字 + 已选分面)下重算，实现逐层下钻。
    """
    client = get_es_client()
    filters = filters or {}

    must: list[dict] = []
    if keyword:
        must.append(_keyword_clause(keyword, mode))

    # 默认仅检索正式库馆藏（排除暂存库草稿）；include_staging 时正式+暂存都检索
    filter_clauses: list[dict] = []
    if not include_staging:
        filter_clauses.append({"term": {"doc_source.keyword": "formal"}})
    if tenant_id:
        filter_clauses.append({"term": {"tenant_id": tenant_id}})
    if public_only:
        filter_clauses.append({"term": {"MJ.keyword": "无"}})
    for name, values in filters.items():
        field = FACET_FIELDS.get(name)
        if field and values:
            filter_clauses.append({"terms": {field: values}})

    # 全文模式：把整段 OCR 原文(full_text)带回，前端整段展示 + 命中标红
    source_fields = _SUPER_SOURCE + (
        ["full_text"] if mode in ("fulltext", "qa") else []
    )

    es_query = {
        "query": {
            "bool": {"must": must or [{"match_all": {}}], "filter": filter_clauses}
        },
        "aggs": {
            f"facet_{name}": {"terms": {"field": field, "size": 30}}
            for name, field in FACET_FIELDS.items()
        },
        "highlight": {
            "fields": {"TM": {}, "RZZ": {}},
            "pre_tags": ["<em>"],
            "post_tags": ["</em>"],
        },
        "from": skip,
        "size": limit,
        "_source": source_fields,
    }

    try:
        resp = await client.search(index=ARCHIVE_INDEX, body=es_query)
    except Exception as exc:
        logger.error("ES 超级查询失败 keyword='%s': %s", keyword, exc)
        return {"total": 0, "hits": [], "facets": {}, "error": "搜索服务暂时不可用"}

    facets: dict[str, list] = {}
    aggs = resp.get("aggregations", {})
    for name in FACET_FIELDS:
        buckets = aggs.get(f"facet_{name}", {}).get("buckets", [])
        facets[name] = [{"value": b["key"], "count": b["doc_count"]} for b in buckets]

    return {
        "total": resp["hits"]["total"]["value"],
        "hits": [
            {
                **hit["_source"],
                "score": hit["_score"],
                "highlight": hit.get("highlight", {}),
            }
            for hit in resp["hits"]["hits"]
        ],
        "facets": facets,
    }
