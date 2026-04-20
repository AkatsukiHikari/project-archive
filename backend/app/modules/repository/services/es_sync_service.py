"""
档案 ES 同步服务。

策略：
  - ES 是查询加速层，PG 是主存储，同步失败不阻断业务写入
  - 单条写入：API 路由提交 PG 事务后异步触发
  - 批量导入：每 500 条批次写完 PG 后 bulk index
  - 全量重建：管理后台触发 Celery 任务扫全表

专业档案隐私字段（requires_privacy_guard=True 的门类）在 ES 中存脱敏版本。
"""
import logging
from typing import Sequence

from elasticsearch import AsyncElasticsearch, helpers

from app.infra.search.es_client import get_es_client, ARCHIVE_INDEX
from app.modules.repository.models.archive import Archive

logger = logging.getLogger(__name__)

# 需脱敏的字段名关键词（证件号 / 手机号等）
_SENSITIVE_KEYWORDS = ("id_no", "id_card", "phone", "mobile", "cert_no")


def _build_doc(archive: Archive) -> dict:
    """将 Archive ORM 对象转换为 ES 文档。隐私字段自动脱敏。"""
    ext = archive.ext_fields or {}
    # 隐私门类：ext_fields 中包含敏感关键词的字段脱敏
    sanitized_ext: dict = {}
    for k, v in ext.items():
        if any(kw in k.lower() for kw in _SENSITIVE_KEYWORDS):
            sanitized_ext[k] = str(v)[:3] + "***" if v else ""
        else:
            sanitized_ext[k] = v

    return {
        "id": str(archive.id),
        "archive_no": archive.archive_no,
        "fonds_code": archive.fonds_code,
        "catalog_id": str(archive.catalog_id) if archive.catalog_id else None,
        "year": archive.year,
        "title": archive.title,
        "creator": archive.creator,
        "security_level": archive.security_level,
        "retention_period": archive.retention_period,
        "doc_date": archive.doc_date.isoformat() if archive.doc_date else None,
        "level": archive.level,
        "status": archive.status,
        "ext_fields": sanitized_ext,
        "tenant_id": str(archive.tenant_id) if archive.tenant_id else None,
        "create_time": archive.create_time.isoformat() if archive.create_time else None,
    }


async def sync_one(archive: Archive) -> None:
    """索引单条档案（新增或覆盖）。失败只记日志，不抛异常。"""
    client: AsyncElasticsearch = get_es_client()
    try:
        await client.index(index=ARCHIVE_INDEX, id=str(archive.id), document=_build_doc(archive))
    except Exception as exc:
        logger.warning("ES sync_one 失败 id=%s: %s", archive.id, exc)


async def delete_one(archive_id: str) -> None:
    """从 ES 删除档案（软删除后调用）。"""
    client: AsyncElasticsearch = get_es_client()
    try:
        await client.delete(index=ARCHIVE_INDEX, id=archive_id, ignore=[404])
    except Exception as exc:
        logger.warning("ES delete_one 失败 id=%s: %s", archive_id, exc)


async def bulk_sync(archives: Sequence[Archive]) -> int:
    """
    批量索引，返回成功写入条数。
    用于批量导入每批完成后调用。
    """
    if not archives:
        return 0
    client: AsyncElasticsearch = get_es_client()
    actions = [
        {"_index": ARCHIVE_INDEX, "_id": str(a.id), "_source": _build_doc(a)}
        for a in archives
    ]
    try:
        success, _ = await helpers.async_bulk(client, actions, raise_on_error=False)
        return success
    except Exception as exc:
        logger.warning("ES bulk_sync 失败 count=%d: %s", len(archives), exc)
        return 0
