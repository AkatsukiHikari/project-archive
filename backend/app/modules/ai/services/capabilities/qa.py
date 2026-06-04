"""
qa 能力：RAG 问答

输入：query
处理：检索 rules + meta → 拼成证据 → 直接返回（LLM 节点用 prompt 把证据转成答案）
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities.types import CapabilityContext, CapabilityResult
from app.modules.ai.services.retrieval_service import RetrievalService, RetrieveFilter


async def run(*, db: AsyncSession, ctx: CapabilityContext, query: str) -> CapabilityResult:
    svc = RetrievalService(db)
    filt = RetrieveFilter(tenant_id=ctx.tenant_id, secret_level=ctx.secret_level, user_id=ctx.user_id)
    rules = await svc.retrieve(query=query, kb_type="rules", top_k=4, filt=filt)
    metas = await svc.retrieve(query=query, kb_type="meta", top_k=3, filt=filt)
    hits = rules + metas

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
            answer="未在知识库中找到与此问题相关的档案或业务规则。",
            citations=[],
            detail={"hint": "尝试补充关键词、时间或全宗号条件后重新提问。"},
        )

    # 把证据按"规则 + 档案"分类拼好，留给 LLM 节点格式化
    lines = ["以下是检索到的相关证据，请基于此回答问题：", ""]
    rule_hits = [c for c in hits if c.source_type == "rule"]
    meta_hits = [c for c in hits if c.source_type == "meta"]
    if rule_hits:
        lines.append("【相关业务规则】")
        for r in rule_hits:
            lines.append(f"- 《{r.title}》：{r.snippet}")
    if meta_hits:
        lines.append("")
        lines.append("【相关档案】")
        for m in meta_hits:
            lines.append(f"- {m.title}（{m.snippet}）")

    return CapabilityResult(
        status="ok",
        answer="\n".join(lines),
        citations=citations,
        detail={"rules_count": len(rule_hits), "metas_count": len(meta_hits)},
    )
