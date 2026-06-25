"""
fournat 能力：四性检测建议（建议态，最低优先级）

P1 仅做骨架：对给定档案 / 主题给出四性维度的"可能风险"提示。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities.types import (CapabilityContext,
                                                        CapabilityResult)
from app.modules.ai.services.retrieval_service import (RetrievalService,
                                                       RetrieveFilter)

_DIMENSIONS = [
    ("真实性", "来源 / 责任者 / 时间链"),
    ("完整性", "文件哈希 / 子文件清单"),
    ("可用性", "文件格式 / 编码 / 可读性"),
    ("安全性", "密级标记 / 加密 / 备份"),
]


async def run(
    *, db: AsyncSession, ctx: CapabilityContext, query: str
) -> CapabilityResult:
    svc = RetrievalService(db)
    filt = RetrieveFilter(
        tenant_id=ctx.tenant_id, secret_level=ctx.secret_level, user_id=ctx.user_id
    )
    rules = await svc.retrieve(
        query=query + " 四性 检测", kb_type="rules", top_k=4, filt=filt
    )

    lines = ["【四性检测风险提示（建议态，仅供参考）】", "", f"对象：{query}", ""]
    for name, hint in _DIMENSIONS:
        lines.append(f"◆ {name}（{hint}）")
        lines.append(
            f"  · 可能风险：请人工核对【责任者签章 / 文件元数据 / 来源系统】是否齐备。"
        )
        lines.append("")
    if rules:
        lines.append("【可参照的业务规则】")
        for r in rules:
            lines.append(f"- 《{r.title}》：{r.snippet[:80]}")
    lines.append("")
    lines.append("⚠ 本能力仅提示风险点，不下检测结论；请档案管理员人工复核。")

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
        for c in rules
    ]
    return CapabilityResult(
        status="ok",
        answer="\n".join(lines),
        citations=citations,
        detail={"target": query, "dimensions": [d[0] for d in _DIMENSIONS]},
    )
