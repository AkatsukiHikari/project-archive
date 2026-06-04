"""
search 能力：自然语言检索

输入：query
处理：解析关键词 / 年度 / 全宗号 → 调 ES 检索 meta → 返回命中列表
"""
from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities.types import CapabilityContext, CapabilityResult
from app.modules.ai.services.retrieval_service import RetrievalService, RetrieveFilter


_YEAR_RE = re.compile(r"(19|20)\d{2}")
_QZH_RE = re.compile(r"[JQ]\d{3}")


def _extract_dsl(query: str) -> dict:
    """简单的 NL → 结构化检索意图（关键词 + 年度 + 全宗号）。"""
    dsl: dict = {"keywords": query, "filters": {}}
    if m := _YEAR_RE.search(query):
        dsl["filters"]["ND"] = int(m.group())
    if m := _QZH_RE.search(query):
        dsl["filters"]["QZH"] = m.group()
    return dsl


async def run(*, db: AsyncSession, ctx: CapabilityContext, query: str) -> CapabilityResult:
    dsl = _extract_dsl(query)
    svc = RetrievalService(db)
    filt = RetrieveFilter(tenant_id=ctx.tenant_id, secret_level=ctx.secret_level, user_id=ctx.user_id)

    # P1：ES 已能按 query 多字段匹配；filters 暂时存到 detail 给 LLM 节点解释意图
    hits = await svc.retrieve(query=query, kb_type="meta", top_k=8, filt=filt)
    citations = [
        {
            "chunk_id": c.chunk_id,
            "source_type": c.source_type,
            "source_id": c.source_id,
            "title": c.title,
            "snippet": c.snippet,
            "score": c.score,
            "secret_level": c.secret_level,
            "tenant_id": c.tenant_id,
            "extra": c.extra,
        }
        for c in hits
    ]

    if not hits:
        return CapabilityResult(
            status="ok",
            answer=f"未找到匹配「{query}」的档案。建议补充时间范围、关键词或全宗号。",
            detail={"dsl": dsl, "hits_count": 0},
        )

    lines = [f"基于查询「{query}」检索到 {len(hits)} 条命中（按相关度排序）：", ""]
    for i, h in enumerate(hits, start=1):
        nd = (h.extra or {}).get("ND")
        dh = (h.extra or {}).get("DH")
        qzh = h.snippet.split(' / ')[1] if ' / ' in h.snippet else '—'
        # 在题名上加 markdown 链接 → 档案查阅页定位到该档案
        # 前端 RagChatPanel 会拦截 a[href] 点击转 window.open（新浏览器 tab）
        url = f"/archive/utilization/reading?id={h.source_id}"
        lines.append(f"{i}. [{h.title}]({url})（档号 `{dh or '—'}` · {nd or '—'} 年 · 全宗 {qzh}）")
    return CapabilityResult(
        status="ok",
        answer="\n".join(lines),
        citations=citations,
        detail={"dsl": dsl, "hits_count": len(hits)},
    )
