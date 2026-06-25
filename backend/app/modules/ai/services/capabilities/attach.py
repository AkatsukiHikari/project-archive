"""
attach 能力：档案自动挂接

输入：query（新材料描述）
处理：检索候选档案 / 目录 → 取最佳 → 产出挂接 patch
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities.types import (CapabilityContext,
                                                        CapabilityResult)
from app.modules.ai.services.retrieval_service import (RetrievalService,
                                                       RetrieveFilter)
from app.modules.ai_patch.services.patch_service import PatchService


async def run(
    *, db: AsyncSession, ctx: CapabilityContext, query: str
) -> CapabilityResult:
    svc = RetrievalService(db)
    filt = RetrieveFilter(
        tenant_id=ctx.tenant_id, secret_level=ctx.secret_level, user_id=ctx.user_id
    )

    candidates = await svc.retrieve(query=query, kb_type="meta", top_k=5, filt=filt)
    if not candidates:
        return CapabilityResult(
            status="ok",
            answer="未找到合适的归属档案 / 目录，建议人工指定。",
            detail={"candidates_count": 0},
        )

    best = candidates[0]
    confidence = min(1.0, best.score / 30.0)  # ES score → 0-1 标准化
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
        for c in candidates
    ]

    patch_svc = PatchService(db)
    patch = await patch_svc.create(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        scenario_code="attach",
        target_type="archive_attach_link",
        operation="create",
        payload={
            "create": {
                "attach_to_archive_id": best.source_id,
                "attach_to_title": best.title,
                "source_material": query[:500],
                "confidence": confidence,
            }
        },
        citations=citations,
        confidence=confidence,
        gate="review",
    )
    await db.commit()

    lines = [
        "【档案挂接建议】",
        "",
        f"推荐挂接目标：{best.title}",
        f"  档号：{(best.extra or {}).get('DH', '—')}",
        f"  匹配相关度：{best.score:.2f}（标准化置信度 {confidence:.0%}）",
        "",
        "【其他候选】",
    ]
    for c in candidates[1:4]:
        lines.append(f"  · {c.title}（相关度 {c.score:.2f}）")
    lines.append("")
    lines.append(
        f"已生成挂接 Patch #{str(patch.id)[:8]}（pending），等待人工审核确认。"
    )

    return CapabilityResult(
        status="ok",
        answer="\n".join(lines),
        citations=citations,
        patch_id=patch.id,
        detail={
            "best_match": best.title,
            "confidence": confidence,
            "candidates_count": len(candidates),
        },
    )
