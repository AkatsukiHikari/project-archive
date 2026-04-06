"""
Elasticsearch 异步客户端单例

用途：
  - 档案全文检索索引
  - 支持中文分词（需安装 IK 分词器插件）
  - 与 pgvector 语义检索形成互补：
      ES = 关键词全文检索（精确匹配、多字段、高亮）
      pgvector = 语义相似度检索（RAG 场景）

学习笔记：
  Elasticsearch 是文档型搜索引擎，数据以 JSON 文档存储。
  索引（Index）≈ 数据库表；文档（Document）≈ 行；字段（Field）≈ 列。
  倒排索引是其核心：把"词 → 文档列表"存起来，查词时秒找到所有包含该词的文档。
"""

import logging
from typing import Optional

from elasticsearch import AsyncElasticsearch

from app.core.config import settings

logger = logging.getLogger(__name__)

# 模块级单例
_client: Optional[AsyncElasticsearch] = None


def get_es_client() -> AsyncElasticsearch:
    global _client
    if _client is None:
        _client = AsyncElasticsearch(
            hosts=[settings.ELASTICSEARCH_URL],
            # 生产环境需配置认证：
            # basic_auth=("elastic", settings.ES_PASSWORD),
            # verify_certs=True,
        )
    return _client


async def close_es_client() -> None:
    global _client
    if _client is not None:
        await _client.close()
        _client = None


# ─── 档案索引名称 ──────────────────────────────────────────────────��───────────

ARCHIVE_ITEM_INDEX = "sams_archive_items"

# ─── 索引 Mapping ──────────────────────��───────────────────────���───────────────

ARCHIVE_ITEM_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            # 如已安装 IK 分词器，可用 ik_max_word 替代 standard
            "analyzer": {
                "chinese_analyzer": {
                    "type": "standard"  # 生产环境换为 "ik_max_word"
                }
            }
        },
    },
    "mappings": {
        "properties": {
            "id": {"type": "keyword"},
            "title": {
                "type": "text",
                "analyzer": "chinese_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "author": {"type": "text", "analyzer": "chinese_analyzer"},
            "document_date": {"type": "keyword"},
            "item_type": {"type": "keyword"},
            "security_level": {"type": "keyword"},
            "fonds_id": {"type": "keyword"},
            "fonds_code": {"type": "keyword"},
            "archive_file_id": {"type": "keyword"},
            "file_number": {"type": "keyword"},
            "year": {"type": "integer"},
            "tenant_id": {"type": "keyword"},
            "metadata_json": {"type": "object", "enabled": False},  # 不索引元数据内部字段
            "create_time": {"type": "date"},
        }
    },
}


async def ensure_index() -> None:
    """确保档案条目索引存在（应用启动时调用）"""
    client = get_es_client()
    try:
        exists = await client.indices.exists(index=ARCHIVE_ITEM_INDEX)
        if not exists:
            await client.indices.create(
                index=ARCHIVE_ITEM_INDEX,
                body=ARCHIVE_ITEM_MAPPING,
            )
            logger.info("Elasticsearch 索引 '%s' 创建成功", ARCHIVE_ITEM_INDEX)
        else:
            logger.debug("Elasticsearch 索引 '%s' 已存在", ARCHIVE_ITEM_INDEX)
    except Exception as e:
        # ES 不可用时不阻断启动，降级为仅 pgvector 搜索
        logger.warning("Elasticsearch 索引初始化失败（将降级为数据库搜索）: %s", e)
