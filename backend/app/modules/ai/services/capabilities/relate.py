"""
relate 能力：跨档案关联

输入：query（档号或主题）
处理：检索相关 meta；按 score 排序；按全宗 / 年度分组，返回关联建议
"""
from __future__ import annotations

import re
from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities.types import CapabilityContext, CapabilityResult
from app.modules.ai.services.retrieval_service import RetrievalService, RetrieveFilter


_DH_RE = re.compile(r"[JQ]\d{3}-[A-Z_]+-\d{4}-[YCD]-\d+")


async def run(*, db: AsyncSession, ctx: CapabilityContext, query: str) -> CapabilityResult:
    svc = RetrievalService(db)
    filt = RetrieveFilter(tenant_id=ctx.tenant_id, secret_level=ctx.secret_level, user_id=ctx.user_id)

    # 如果用户提到具体档号，剥离档号后用其语义部分检索
    dh_match = _DH_RE.search(query)
    target_dh = dh_match.group() if dh_match else None

    hits = await svc.retrieve(query=query, kb_type="meta", top_k=10, filt=filt)
    # 排除自身
    if target_dh:
        hits = [h for h in hits if (h.extra or {}).get("DH") != target_dh]

    if not hits:
        return CapabilityResult(
            status="ok",
            answer="未找到与之相关的其他档案，建议扩大检索关键词。",
            detail={"target_dh": target_dh, "hits_count": 0},
        )

    # 按"全宗号 / 年度"维度分组，体现关联依据
    by_qzh: dict[str, list[str]] = defaultdict(list)
    by_year: dict[str, list[str]] = defaultdict(list)
    for h in hits:
        ex = h.extra or {}
        # snippet 是 "DH / QZH / ND"
        parts = h.snippet.split(" / ")
        qzh = parts[1] if len(parts) > 1 else "—"
        nd = ex.get("ND") or "—"
        by_qzh[qzh].append(h.title)
        by_year[str(nd)].append(h.title)

    lines = [f"【关联分析对象】{query}", ""]
    if target_dh:
        lines.append(f"识别到具体档号：{target_dh}")
        lines.append("")
    lines.append(f"【可能相关的 {len(hits)} 件档案（按相关度排序）】")
    for i, h in enumerate(hits, start=1):
        nd = (h.extra or {}).get("ND")
        dh = (h.extra or {}).get("DH")
        lines.append(f"{i}. {h.title}（{dh or '—'} · {nd or '—'} 年 · 相关度 {h.score:.2f}）")
    lines.append("")
    lines.append("【关联维度统计】")
    lines.append(f"  · 涉及全宗：{len(by_qzh)} 个")
    lines.append(f"  · 涉及年度：{len(by_year)} 个")
    lines.append("")
    lines.append("⚠ 关联仅为建议，实体消歧可能存在歧义，最终请人工核对。")

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
    return CapabilityResult(
        status="ok",
        answer="\n".join(lines),
        citations=citations,
        detail={"target_dh": target_dh, "by_qzh": list(by_qzh.keys()), "by_year": list(by_year.keys())},
    )
