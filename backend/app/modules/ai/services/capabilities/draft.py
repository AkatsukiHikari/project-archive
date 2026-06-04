"""
draft 能力：拟稿助手

输入：query（草稿类型 + 上下文）
处理：识别草稿类型，准备模板素材 + 检索相关档案给 LLM 节点
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities.types import CapabilityContext, CapabilityResult
from app.modules.ai.services.retrieval_service import RetrievalService, RetrieveFilter


DRAFT_TEMPLATES = {
    "鉴定": "档案鉴定意见",
    "销毁": "档案销毁建议书",
    "利用": "档案利用工作报告",
    "汇报": "工作汇报",
    "通知": "通知",
}


def _detect_type(query: str) -> str:
    for kw, label in DRAFT_TEMPLATES.items():
        if kw in query:
            return label
    return "档案业务公文"


async def run(*, db: AsyncSession, ctx: CapabilityContext, query: str) -> CapabilityResult:
    draft_type = _detect_type(query)
    svc = RetrievalService(db)
    filt = RetrieveFilter(tenant_id=ctx.tenant_id, secret_level=ctx.secret_level, user_id=ctx.user_id)

    refs = await svc.retrieve(query=query, kb_type="rules", top_k=2, filt=filt)
    archives = await svc.retrieve(query=query, kb_type="meta", top_k=3, filt=filt)

    lines = [
        f"【拟稿任务】{draft_type}",
        f"【用户需求】{query}",
        "",
        "【可引用的业务规则】",
    ]
    for r in refs:
        lines.append(f"- 《{r.title}》：{r.snippet[:80]}")
    lines.append("")
    lines.append("【相关档案素材】")
    for a in archives:
        lines.append(f"- {a.title}")
    lines.append("")
    lines.append(f"请按【{draft_type}】的公文规范生成：标题 / 正文（分条款，引用要准确）/ 落款建议。")
    lines.append("⚠ 草稿不替代正式签发，请落到草稿夹后人工修改、走审批。")

    citations = [
        {
            "chunk_id": c.chunk_id, "source_type": c.source_type, "source_id": c.source_id,
            "title": c.title, "snippet": c.snippet, "score": c.score,
            "secret_level": c.secret_level, "tenant_id": c.tenant_id, "extra": c.extra,
        }
        for c in (refs + archives)
    ]
    return CapabilityResult(
        status="ok",
        answer="\n".join(lines),
        citations=citations,
        detail={"draft_type": draft_type, "refs_count": len(refs), "archives_count": len(archives)},
    )
