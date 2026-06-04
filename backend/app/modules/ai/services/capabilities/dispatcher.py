"""
能力分发器：scenario_code → capability service

Dify 主 Chatflow 的 HTTP 节点 / 子 Workflow 的 HTTP 节点都打到后端的
/v1/ai/internal/tool/dispatch + /v1/ai/internal/capability/{code}，最终都进入这里。
"""
from __future__ import annotations

from typing import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.services.capabilities import (
    attach,
    catalog,
    draft,
    fournat,
    kb_manage,
    qa,
    relate,
    search,
    summary,
)
from app.modules.ai.services.capabilities.types import CapabilityContext, CapabilityResult


CapabilityRunner = Callable[..., Awaitable[CapabilityResult]]


_REGISTRY: dict[str, CapabilityRunner] = {
    "qa": qa.run,
    "search": search.run,
    "summary": summary.run,
    "kb_manage": kb_manage.run,
    "relate": relate.run,
    "catalog": catalog.run,
    "attach": attach.run,
    "draft": draft.run,
    "fournat": fournat.run,
}


def get_capability(code: str) -> CapabilityRunner | None:
    return _REGISTRY.get(code)


async def dispatch(
    *, db: AsyncSession, ctx: CapabilityContext, code: str, query: str
) -> CapabilityResult:
    runner = _REGISTRY.get(code)
    if runner is None:
        return CapabilityResult(
            status="not_implemented",
            answer=f"能力 '{code}' 尚未实装。",
            reason=f"unknown capability code: {code}",
        )
    return await runner(db=db, ctx=ctx, query=query)


def all_capability_codes() -> list[str]:
    return list(_REGISTRY.keys())
