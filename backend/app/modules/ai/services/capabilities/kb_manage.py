"""
kb_manage 能力：知识库管理（查状态 / 重建）

输入：query
处理：调 KBSyncService 拿三类 KB 状态；返回结构化状态供 LLM 节点回答
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities.types import (CapabilityContext,
                                                        CapabilityResult)
from app.modules.ai.services.kb_sync_service import KBSyncService


async def run(
    *, db: AsyncSession, ctx: CapabilityContext, query: str
) -> CapabilityResult:
    svc = KBSyncService(db)
    stats = await svc.get_stats(ctx.tenant_id)

    lines = ["【SAMS 知识库当前状态】", ""]
    for s in stats:
        kb_label = {
            "meta": "L1 元数据",
            "rules": "L4 业务规则",
            "ocr": "L2 OCR 全文",
        }.get(s.kb_type, s.kb_type)
        es_show = "ES 不可达" if s.es_count is None else f"{s.es_count} 条"
        synced = "✓ 已同步" if s.synced else "⚠ 待同步"
        lines.append(
            f"- {kb_label}（{s.kb_type}）：DB {s.db_count} 条 / 索引 {es_show} · {synced}"
        )
        if s.note:
            lines.append(f"    备注：{s.note}")
    lines.append("")
    lines.append(
        "如需重建 L1 元数据索引，可在 /ai/knowledge 页面点击『立即同步』或调用 POST /v1/ai/kb/rebuild。"
    )

    detail = {
        "stats": [
            {
                "kb_type": s.kb_type,
                "db_count": s.db_count,
                "es_count": s.es_count,
                "synced": s.synced,
                "last_synced_at": s.last_synced_at,
                "note": s.note,
            }
            for s in stats
        ]
    }
    return CapabilityResult(status="ok", answer="\n".join(lines), detail=detail)
