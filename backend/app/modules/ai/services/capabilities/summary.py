"""
summary 能力：档案专题综述

输入：query（主题）
处理：先按主题做较大范围检索（top_k=10），按年度聚类，给 LLM 节点结构化素材
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities.types import CapabilityContext, CapabilityResult
from app.modules.ai.services.retrieval_service import RetrievalService, RetrieveFilter


async def run(*, db: AsyncSession, ctx: CapabilityContext, query: str) -> CapabilityResult:
    svc = RetrievalService(db)
    filt = RetrieveFilter(tenant_id=ctx.tenant_id, secret_level=ctx.secret_level, user_id=ctx.user_id)
    rules = await svc.retrieve(query=query, kb_type="rules", top_k=3, filt=filt)
    metas = await svc.retrieve(query=query, kb_type="meta", top_k=12, filt=filt)
    hits = rules + metas

    if not metas:
        return CapabilityResult(
            status="ok",
            answer=f"未找到与「{query}」相关的档案，无法生成综述。建议放宽主题或时间范围。",
            detail={"hits_count": 0},
        )

    # 按年度聚类
    by_year: dict[str, list[str]] = defaultdict(list)
    for m in metas:
        nd = (m.extra or {}).get("ND") or "—"
        by_year[str(nd)].append(m.title)

    lines = [f"【综述主题】{query}", "", "【相关业务规则】"]
    for r in rules:
        lines.append(f"- 《{r.title}》：{r.snippet}")
    lines.append("")
    lines.append(f"【档案分布概览】共检索到 {len(metas)} 件档案，按年度分布如下：")
    for year in sorted(by_year.keys(), reverse=True):
        titles = by_year[year]
        lines.append(f"  · {year} 年（{len(titles)} 件）: {' / '.join(titles[:3])}{' 等' if len(titles) > 3 else ''}")
    lines.append("")
    lines.append("【典型档案明细】")
    for m in metas[:6]:
        nd = (m.extra or {}).get("ND")
        dh = (m.extra or {}).get("DH")
        lines.append(f"- {m.title}（档号 {dh or '—'} · {nd or '—'} 年）")

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
        detail={"metas_count": len(metas), "years_count": len(by_year)},
    )
