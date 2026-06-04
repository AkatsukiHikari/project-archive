"""
catalog 能力：AI 自动编目

输入：query（档案原文）
处理：用启发式 + 检索辅助提取核心字段；产出编目 patch 进入审核队列（Q2 ii：通过后可写入档案表）
"""
from __future__ import annotations

import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities.types import CapabilityContext, CapabilityResult
from app.modules.ai.services.retrieval_service import RetrievalService, RetrieveFilter
from app.modules.ai_patch.services.patch_service import PatchService


_YEAR_RE = re.compile(r"(19|20)\d{2}")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_RZZ_RE = re.compile(r"(办公室|档案馆|党办|财务部|人事科|信息中心|宣传科|审计科|技术科|保密办)")


def _extract_fields(text: str) -> dict:
    """轻量启发式抽取（演示阶段；P3 替换为 LLM 抽取）。"""
    fields: dict = {}
    # 题名：取第一行 60 字内
    first_line = text.strip().split("\n")[0].strip()
    if first_line:
        fields["TM"] = first_line[:80]
    if m := _YEAR_RE.search(text):
        fields["ND"] = int(m.group())
    if m := _DATE_RE.search(text):
        fields["WJRQ"] = m.group()
    if m := _RZZ_RE.search(text):
        fields["RZZ"] = m.group()
    # 默认值
    fields.setdefault("MJ", "internal")
    fields.setdefault("BGQX", "long")
    return fields


async def run(*, db: AsyncSession, ctx: CapabilityContext, query: str) -> CapabilityResult:
    fields = _extract_fields(query)
    confidence = sum(1 for k in ("TM", "ND", "RZZ", "WJRQ") if k in fields) / 4.0

    # 检索相似档案给用户参考
    svc = RetrievalService(db)
    filt = RetrieveFilter(tenant_id=ctx.tenant_id, secret_level=ctx.secret_level, user_id=ctx.user_id)
    similar = await svc.retrieve(query=fields.get("TM", query)[:60], kb_type="meta", top_k=3, filt=filt)
    citations = [
        {
            "chunk_id": c.chunk_id, "source_type": c.source_type, "source_id": c.source_id,
            "title": c.title, "snippet": c.snippet, "score": c.score,
            "secret_level": c.secret_level, "tenant_id": c.tenant_id, "extra": c.extra,
        }
        for c in similar
    ]

    # 写一份 staging patch（target_type=archive_staging，让审核员通过后由 patch_service.apply 写入）
    patch_svc = PatchService(db)
    patch = await patch_svc.create(
        tenant_id=ctx.tenant_id,
        user_id=ctx.user_id,
        scenario_code="catalog",
        target_type="archive_staging",
        operation="create",
        payload={"create": {"fields": fields, "raw_text": query[:2000]}},
        citations=citations,
        confidence=confidence,
        gate="review",
    )
    await db.commit()

    lines = [
        "【AI 自动编目结果】",
        "",
        f"识别置信度：{confidence:.0%}",
        "",
        "【抽取字段】",
    ]
    for k, v in fields.items():
        lines.append(f"  · {k}: {v}")
    if similar:
        lines.append("")
        lines.append("【相似档案参考】")
        for s in similar[:3]:
            lines.append(f"  - {s.title}")
    lines.append("")
    lines.append(f"已生成编目 Patch #{str(patch.id)[:8]}（pending），等待人工审核通过后归档。")

    return CapabilityResult(
        status="ok",
        answer="\n".join(lines),
        citations=citations,
        patch_id=patch.id,
        detail={"fields": fields, "confidence": confidence},
    )
