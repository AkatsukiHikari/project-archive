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
        "DH": item.DH,
        "QZH": item.QZH,
        "TM": item.TM,
        "RZZ": item.RZZ,
        "ND": item.ND,
        "WJRQ": item.WJRQ,
        "MJ": item.MJ,
        "BGQX": item.BGQX,
        "catalog_id": str(item.catalog_id),
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
