"""Dify 知识库(Dataset) API 客户端：把档案全文+元数据推进知识库。

走 DIFY_DATASET_API_KEY + DIFY_ARCHIVE_DATASET_ID（知识库 API，与 App API 不同）。
未配置时所有方法静默 no-op（不阻断业务）。
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_PROCESS_RULE = {"mode": "automatic"}


def _enabled() -> bool:
    return bool(settings.DIFY_DATASET_API_KEY and settings.DIFY_ARCHIVE_DATASET_ID)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.DIFY_DATASET_API_KEY}",
        "Content-Type": "application/json",
    }


def _base() -> str:
    return f"{settings.DIFY_BASE_URL}/datasets/{settings.DIFY_ARCHIVE_DATASET_ID}"


async def upsert_text(doc_id: Optional[str], name: str, text: str) -> Optional[str]:
    """创建/更新一篇文本文档，返回 document_id。未配置返回 None。"""
    if not _enabled():
        return None
    async with httpx.AsyncClient(timeout=60.0) as c:
        if doc_id:
            url = f"{_base()}/documents/{doc_id}/update-by-text"
            payload = {"name": name, "text": text}
        else:
            url = f"{_base()}/document/create-by-text"
            payload = {
                "name": name,
                "text": text,
                "indexing_technique": "high_quality",
                "process_rule": _PROCESS_RULE,
            }
        r = await c.post(url, headers=_headers(), json=payload)
        if r.status_code not in (200, 201):
            # doc_id 失效（被手动删了）→ 退回创建
            if doc_id and r.status_code in (404, 400):
                return await upsert_text(None, name, text)
            logger.warning("KB upsert 失败 %d: %s", r.status_code, r.text[:200])
            return doc_id
        return (r.json().get("document") or {}).get("id") or doc_id


async def delete_doc(doc_id: str) -> None:
    if not _enabled() or not doc_id:
        return
    async with httpx.AsyncClient(timeout=30.0) as c:
        try:
            await c.delete(f"{_base()}/documents/{doc_id}", headers=_headers())
        except Exception as exc:  # noqa: BLE001
            logger.warning("KB 删除失败 %s: %s", doc_id, exc)


async def list_documents(page: int = 1, limit: int = 20, keyword: str = "") -> dict:
    """知识库文档列表：名称/字数/索引状态/更新时间。"""
    if not _enabled():
        return {"total": 0, "items": []}
    params: dict = {"page": page, "limit": limit}
    if keyword:
        params["keyword"] = keyword
    async with httpx.AsyncClient(timeout=30.0) as c:
        r = await c.get(f"{_base()}/documents", headers=_headers(), params=params)
        if r.status_code != 200:
            logger.warning("KB 文档列表失败 %d: %s", r.status_code, r.text[:200])
            return {"total": 0, "items": [], "error": r.text[:200]}
        d = r.json()
        return {
            "total": d.get("total", 0),
            "items": [
                {
                    "id": x.get("id"),
                    "name": x.get("name"),
                    "word_count": x.get("word_count"),
                    "indexing_status": x.get("indexing_status"),
                    "enabled": x.get("enabled"),
                    "created_at": x.get("created_at"),
                }
                for x in d.get("data", [])
            ],
        }


async def hit_testing(query: str, top_k: int = 6) -> list[dict]:
    """命中测试：查询知识库召回了哪些片段、相关度多少。"""
    if not _enabled():
        return []
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.post(
            f"{_base()}/hit-testing",
            headers=_headers(),
            json={
                "query": query,
                "retrieval_model": {
                    "search_method": "hybrid_search",
                    "reranking_enable": False,
                    "top_k": top_k,
                    "score_threshold_enabled": False,
                },
            },
        )
        if r.status_code != 200:
            logger.warning("KB 命中测试失败 %d: %s", r.status_code, r.text[:200])
            raise RuntimeError(f"命中测试失败：{r.text[:160]}")
        out = []
        for rec in r.json().get("records", []):
            seg = rec.get("segment") or {}
            doc = seg.get("document") or {}
            out.append(
                {
                    "score": rec.get("score"),
                    "content": (seg.get("content") or "")[:600],
                    "document_id": doc.get("id"),
                    "document_name": doc.get("name"),
                }
            )
        return out


async def upload_document_file(filename: str, content: bytes) -> dict:
    """按文件上传文档（规章制度等，PDF/DOCX/TXT/MD，由 Dify 解析入库）。"""
    import json as _json

    if not _enabled():
        raise RuntimeError("未配置知识库 API")
    data = {
        "indexing_technique": "high_quality",
        "process_rule": _PROCESS_RULE,
    }
    async with httpx.AsyncClient(timeout=120.0) as c:
        r = await c.post(
            f"{_base()}/document/create-by-file",
            headers={"Authorization": f"Bearer {settings.DIFY_DATASET_API_KEY}"},
            files={"file": (filename, content)},
            data={"data": _json.dumps(data)},
        )
        if r.status_code not in (200, 201):
            logger.warning("KB 文件上传失败 %d: %s", r.status_code, r.text[:200])
            raise RuntimeError(f"上传失败：{r.text[:160]}")
        doc = r.json().get("document") or {}
        return {"id": doc.get("id"), "name": doc.get("name")}


async def stats() -> dict:
    """知识库名称/ID/文档数等状态（让前端明确显示在用哪个 dataset）。"""
    if not _enabled():
        return {"enabled": False}
    out: dict = {"enabled": True, "dataset_id": settings.DIFY_ARCHIVE_DATASET_ID}
    async with httpx.AsyncClient(timeout=30.0) as c:
        meta = await c.get(_base(), headers=_headers())
        if meta.status_code == 200:
            out["name"] = meta.json().get("name")
        docs = await c.get(
            f"{_base()}/documents", headers=_headers(), params={"page": 1, "limit": 1}
        )
        if docs.status_code == 200:
            out["doc_count"] = docs.json().get("total", 0)
        else:
            out["error"] = docs.text[:120]
    return out
