"""能力调用共用类型。"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CapabilityContext:
    """每次能力调用的上下文（从 dispatch 入口构造一次，传给所有能力）。"""

    tenant_id: uuid.UUID
    user_id: uuid.UUID
    secret_level: int
    scenario_code: str


@dataclass(frozen=True)
class CapabilityResult:
    """能力 service 统一返回结构。"""

    status: str                 # "ok" / "rejected" / "not_implemented"
    answer: str                  # 给 LLM 节点做最终格式化的"原始素材"或直接答案
    citations: list[dict[str, Any]] = field(default_factory=list)
    patch_id: uuid.UUID | None = None  # 写类能力产出的 staging patch id
    detail: dict[str, Any] = field(default_factory=dict)  # 能力特有的额外结构
    reason: str | None = None    # rejected / not_implemented 时的说明
