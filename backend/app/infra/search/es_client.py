"""
Elasticsearch 异步客户端单例

用途：
  - 档案全文检索索引
  - 支持中文分词（需安装 IK 分词器插件）
"""
import logging
from typing import Optional

from elasticsearch import AsyncElasticsearch

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncElasticsearch] = None


def get_es_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = AsyncElasticsearch(hosts=[settings.ELASTICSEARCH_URL])
    return _client


async def close_es_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


ARCHIVE_INDEX = "sams_archives"
AI_RULES_INDEX = "sams_ai_rules"

# 全租户共享的规则条目的 tenant_id 占位
SHARED_TENANT_ID = "__shared__"

AI_RULES_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "chinese_analyzer": {"type": "standard"}
            }
        },
    },
    "mappings": {
        "properties": {
            "rule_id":       {"type": "keyword"},
            "tenant_id":     {"type": "keyword"},
            "category":      {"type": "keyword"},
            "title":         {"type": "text", "analyzer": "chinese_analyzer",
                              "fields": {"keyword": {"type": "keyword"}}},
            "content":       {"type": "text", "analyzer": "chinese_analyzer"},
            "tags":          {"type": "keyword"},
            "version":       {"type": "keyword"},
            "secret_level":  {"type": "integer"},
            "source":        {"type": "keyword"},   # DA/T 编号 / 内部规章 / ...
            "create_time":   {"type": "date"},
        }
    },
}

ARCHIVE_INDEX_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "analyzer": {
                "chinese_analyzer": {
                    "type": "standard"  # 生产环境换为 ik_max_word
                }
            }
        },
    },
    "mappings": {
        "properties": {
            "id":               {"type": "keyword"},
            "archive_no":       {"type": "keyword"},
            "fonds_code":       {"type": "keyword"},
            "catalog_id":       {"type": "keyword"},
            "year":             {"type": "integer"},
            "title":            {"type": "text", "analyzer": "chinese_analyzer",
                                 "fields": {"keyword": {"type": "keyword"}}},
            "creator":          {"type": "text", "analyzer": "chinese_analyzer"},
            "security_level":   {"type": "keyword"},
            "retention_period": {"type": "keyword"},
            "doc_date":         {"type": "date"},
            "level":            {"type": "keyword"},
            "status":           {"type": "keyword"},
            "ext_fields":       {"type": "object", "dynamic": True},
            "tenant_id":        {"type": "keyword"},
            "create_time":      {"type": "date"},
        }
    },
}


async def ensure_index() -> None:
    """确保档案索引存在（应用启动时调用）。ES 不可用时不阻断启动。"""
    client = get_es_client()
    for index_name, mapping in (
        (ARCHIVE_INDEX, ARCHIVE_INDEX_MAPPING),
        (AI_RULES_INDEX, AI_RULES_INDEX_MAPPING),
    ):
        try:
            exists = await client.indices.exists(index=index_name)
            if not exists:
                await client.indices.create(index=index_name, body=mapping)
                logger.info("Elasticsearch 索引 '%s' 创建成功", index_name)
            else:
                logger.debug("Elasticsearch 索引 '%s' 已存在", index_name)
        except Exception as exc:
            logger.warning(
                "Elasticsearch 索引 '%s' 初始化失败（降级处理）: %s", index_name, exc
            )
