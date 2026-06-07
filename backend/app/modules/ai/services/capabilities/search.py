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
# 检索口语里的停用词：剔除后剩下的才是真正的主题关键词
_STOPWORDS = (
    "查询", "查找", "检索", "查", "找", "看看", "给我", "帮我", "一下", "所有", "全部",
    "的", "档案", "文件", "材料", "资料", "年度", "年", "相关", "关于", "有哪些", "有",
)


def _extract_dsl(query: str) -> dict:
    """NL → 结构化检索意图（主题关键词 + 年度 + 全宗号）。

    关键：把"2022年""查/的/档案"等剥掉，避免它们污染全文匹配；
    年度/全宗号转成精确过滤，否则"查2022年的档案"会变成对题名的模糊匹配而错配。
    """
    nd = int(m.group()) if (m := _YEAR_RE.search(query)) else None
    qzh = m.group() if (m := _QZH_RE.search(query)) else None

    kw = _YEAR_RE.sub("", query)
    if qzh:
        kw = kw.replace(qzh, "")
    for w in _STOPWORDS:
        kw = kw.replace(w, "")
    kw = kw.strip()

    return {"keywords": kw, "filters": {"ND": nd, "QZH": qzh}}


async def run(*, db: AsyncSession, ctx: CapabilityContext, query: str) -> CapabilityResult:
    dsl = _extract_dsl(query)
    svc = RetrievalService(db)
    filt = RetrieveFilter(
        tenant_id=ctx.tenant_id,
        secret_level=ctx.secret_level,
        user_id=ctx.user_id,
        nd=dsl["filters"]["ND"],
        qzh=dsl["filters"]["QZH"],
    )

    # 主题关键词走全文匹配；年度/全宗号走精确过滤（在 retrieve 内注入 ES filter）
    hits = await svc.retrieve(query=dsl["keywords"], kb_type="meta", top_k=10, filt=filt)
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
            answer="检索结果：未命中任何档案。",
            detail={"dsl": dsl, "hits_count": 0},
        )

    # 返回"原始事实块"而非成品散文：格式交给 Dify 的 LLM 节点控制，
    # 但带上 archive_id 让模型能生成 [题名](/archive/reader?id=...) 的可点击原文链接。
    lines = [f"检索到 {len(hits)} 条档案，字段顺序：archive_id | 档号 | 题名 | 年度 | 责任者 | 全宗号"]
    for h in hits:
        ex = h.extra or {}
        qzh = ex.get("QZH") or (h.snippet.split(" / ")[1] if " / " in h.snippet else "")
        lines.append(
            f"- {h.source_id} | {ex.get('DH') or '—'} | {h.title} | "
            f"{ex.get('ND') or '—'} | {ex.get('RZZ') or '—'} | {qzh or '—'}"
        )
    return CapabilityResult(
        status="ok",
        answer="\n".join(lines),
        citations=citations,
        detail={"dsl": dsl, "hits_count": len(hits)},
    )
