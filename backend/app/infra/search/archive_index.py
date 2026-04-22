"""
档案条目 ES 索引操作封装

提供：
  - index_item()     — 新增/更新单个档案条目到 ES
  - delete_item()    — 从 ES 删除条目
  - search_items()   — 全文检索

设计原则：ES 是 PostgreSQL 的搜索副本，PostgreSQL 是主数据源。
数据以 PG 为准，ES 仅用于加速检索。写入失败不应阻断业务流程。
"""

import logging
from typing import Any
import uuid

from app.infra.search.es_client import get_es_client, ARCHIVE_INDEX
from app.modules.repository.models.archive import Archive

logger = logging.getLogger(__name__)


async def index_item(item: Archive, fonds_code: str = "", file_number: str = "") -> None:
    """将档案条目索引到 Elasticsearch（新增或覆盖）"""
    client = get_es_client()
    doc = {
        "id": str(item.id),
        "title": item.title,
        "creator": item.creator,
        "doc_date": item.doc_date,
        "level": item.level,
        "security_level": item.security_level,
        "catalog_id": str(item.catalog_id),
        "archive_no": item.archive_no,
        "fonds_code": item.fonds_code or fonds_code,
        "year": item.year,
        "retention_period": item.retention_period,
        "status": item.status,
        "tenant_id": str(item.tenant_id) if item.tenant_id else None,
        "ext_fields": item.ext_fields,
        "create_time": item.create_time.isoformat() if item.create_time else None,
    }
    try:
        await client.index(
            index=ARCHIVE_INDEX,
            id=str(item.id),
            document=doc,
        )
    except Exception as e:
        logger.warning("ES 索引写入失败 item_id=%s: %s", item.id, e)


async def delete_item(item_id: uuid.UUID) -> None:
    """从 ES 删除档案条目"""
    client = get_es_client()
    try:
        await client.delete(
            index=ARCHIVE_INDEX,
            id=str(item_id),
            ignore=[404],  # 不存在时静默忽略
        )
    except Exception as e:
        logger.warning("ES 删除失败 item_id=%s: %s", item_id, e)


async def search_items(
    query: str,
    tenant_id: str | None = None,
    security_level: str | None = None,
    year: int | None = None,
    fonds_code: str | None = None,
    skip: int = 0,
    limit: int = 20,
) -> dict[str, Any]:
    """
    档案全文检索。

    返回格式：
    {
        "total": 100,
        "hits": [
            {
                "id": "uuid",
                "title": "...",
                "score": 1.23,
                "highlight": {"title": ["<em>关键词</em>在这里"]},
                ...
            }
        ]
    }
    """
    client = get_es_client()

    # 构建查询（multi_match 多字段匹配）
    must_clauses: list[dict] = [
        {
            "multi_match": {
                "query": query,
                "fields": ["title^3", "creator^2"],  # ^N 是字段权重
                "type": "best_fields",
                "fuzziness": "AUTO",  # 容错模糊匹配
            }
        }
    ]

    # 过滤条件（filter 不影响相关性评分）
    filter_clauses: list[dict] = [
        {"term": {"security_level": "public"}}  # 默认只返回公开档案
    ]
    if tenant_id:
        filter_clauses.append({"term": {"tenant_id": tenant_id}})
    if security_level:
        filter_clauses[-1] = {"term": {"security_level": security_level}}  # 覆盖默认过滤
    if year:
        filter_clauses.append({"term": {"year": year}})
    if fonds_code:
        filter_clauses.append({"term": {"fonds_code": fonds_code}})

    es_query = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses,
            }
        },
        "highlight": {
            "fields": {"title": {}, "creator": {}},
            "pre_tags": ["<em>"],
            "post_tags": ["</em>"],
        },
        "from": skip,
        "size": limit,
        "_source": ["id", "title", "creator", "doc_date", "level",
                    "fonds_code", "archive_no", "catalog_id", "year", "create_time"],
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
    except Exception as e:
        logger.error("ES 搜索失败 query='%s': %s", query, e)
        return {"total": 0, "hits": [], "error": "搜索服务暂时不可用"}
