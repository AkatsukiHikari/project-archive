"""
场景路由：能力码 → Dify App / 模型档位映射

把 (tenant_id, scenario_code) 解析成一份 ``ResolvedScenario``，包含：
- Dify App ID / Workflow ID / 版本（按场景独立）
- 用户选的模型档位 → 实际 provider+model（按租户配置）
- HITL 闸门档位（写类场景生效）
- 是否强制引用

校验链：
1. 灰度：场景码必须在 ``settings.AI_ENABLED_CAPABILITIES`` 白名单里（6008）
2. 启用：DB 里对应行 ``enabled=true``（6008）
3. 档位：用户传入的 ``model_tier`` 必须在 ``model_mapping`` keys 里（默认回退到 ``default_model_tier``）
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import BaseAPIException
from app.core.config import settings
from app.modules.ai.models.ai_scenario import AIScenario

# 全部 9 个 AI 能力码（见设计稿 §2）
ALL_SCENARIO_CODES: frozenset[str] = frozenset(
    {
        "qa",  # ① RAG 智能问答
        "search",  # ④ 自然语言检索
        "summary",  # ⑤ 档案摘要/综述
        "attach",  # ② 档案自动挂接
        "catalog",  # ③ AI 自动编目
        "fournat",  # ⑥ 四性检测辅助
        "draft",  # ⑦ 审稿/拟稿
        "relate",  # ⑨ 跨档案关联分析
        "kb_manage",  # ⑧ 知识库交互管理
    }
)

# 模型档位字面量
VALID_MODEL_TIERS: frozenset[str] = frozenset({"快", "准", "思考"})


@dataclass(frozen=True)
class ResolvedScenario:
    """场景路由结果（不可变）。"""

    scenario_code: str
    scenario_id: uuid.UUID
    dify_app_id: str | None
    dify_workflow_id: str | None
    dify_api_key: str | None
    workflow_version: str | None
    model_tier: str
    model_provider: str | None
    model_name: str | None
    gate: str
    citation_required: bool
    extra_config: dict[str, Any] = field(default_factory=dict)


class ScenarioDisabledError(BaseAPIException):
    """场景未启用 / 灰度未放开（6008）。"""

    def __init__(self, scenario_code: str):
        super().__init__(
            code=ErrorCode.AI_CAPABILITY_DISABLED,
            message=f"AI 能力 '{scenario_code}' 未启用",
            status_code=403,
        )


class ScenarioNotFoundError(BaseAPIException):
    """租户未配置该场景（6008）。"""

    def __init__(self, scenario_code: str):
        super().__init__(
            code=ErrorCode.AI_CAPABILITY_DISABLED,
            message=f"AI 能力 '{scenario_code}' 未为当前租户配置",
            status_code=403,
        )


def _enabled_capabilities() -> frozenset[str]:
    raw = settings.AI_ENABLED_CAPABILITIES or ""
    return frozenset(code.strip() for code in raw.split(",") if code.strip())


class ScenarioRouter:
    """场景路由服务（无状态，可在请求间复用）。"""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def resolve(
        self,
        tenant_id: uuid.UUID,
        scenario_code: str,
        model_tier: str | None = None,
    ) -> ResolvedScenario:
        if scenario_code not in ALL_SCENARIO_CODES:
            raise ScenarioNotFoundError(scenario_code)

        if scenario_code not in _enabled_capabilities():
            raise ScenarioDisabledError(scenario_code)

        row = await self._fetch_row(tenant_id, scenario_code)

        # 租户未单独配置：按 settings 兜底（P1 阶段不强求每个租户 seed）
        if row is None:
            tier = (
                model_tier
                if model_tier in VALID_MODEL_TIERS
                else settings.AI_DEFAULT_MODEL_TIER
            )
            return ResolvedScenario(
                scenario_code=scenario_code,
                scenario_id=uuid.UUID(int=0),
                dify_app_id=None,
                dify_workflow_id=None,
                dify_api_key=settings.dify_api_key_for(scenario_code) or None,
                workflow_version=None,
                model_tier=tier,
                model_provider=None,
                model_name=None,
                gate=settings.AI_PATCH_DEFAULT_GATE,
                citation_required=settings.AI_CITATION_REQUIRED,
                extra_config={},
            )

        if not row.enabled:
            raise ScenarioDisabledError(scenario_code)

        tier = self._resolve_tier(row, model_tier)
        provider, model_name = self._resolve_model(row, tier)
        api_key = self._resolve_api_key(row)

        return ResolvedScenario(
            scenario_code=row.scenario_code,
            scenario_id=row.id,
            dify_app_id=row.dify_app_id,
            dify_workflow_id=row.dify_workflow_id,
            dify_api_key=api_key,
            workflow_version=row.workflow_version,
            model_tier=tier,
            model_provider=provider,
            model_name=model_name,
            gate=row.gate,
            citation_required=row.citation_required,
            extra_config=dict(row.extra_config or {}),
        )

    async def _fetch_row(
        self, tenant_id: uuid.UUID, scenario_code: str
    ) -> AIScenario | None:
        stmt = (
            select(AIScenario)
            .where(
                AIScenario.tenant_id == tenant_id,
                AIScenario.scenario_code == scenario_code,
                AIScenario.is_deleted.is_(False),
            )
            .limit(1)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _resolve_tier(row: AIScenario, requested: str | None) -> str:
        candidate = (
            requested or row.default_model_tier or settings.AI_DEFAULT_MODEL_TIER
        )
        if candidate not in VALID_MODEL_TIERS:
            return row.default_model_tier or settings.AI_DEFAULT_MODEL_TIER
        return candidate

    @staticmethod
    def _resolve_model(row: AIScenario, tier: str) -> tuple[str | None, str | None]:
        mapping = row.model_mapping or {}
        entry = mapping.get(tier) or mapping.get(row.default_model_tier) or {}
        if not isinstance(entry, dict):
            return None, None
        return entry.get("provider"), entry.get("model")

    @staticmethod
    def _resolve_api_key(row: AIScenario) -> str | None:
        """优先取 extra_config.dify_api_key（按场景独立 App），缺失则按 scenario_code 查 settings。"""
        extra = row.extra_config or {}
        key = extra.get("dify_api_key") if isinstance(extra, dict) else None
        if isinstance(key, str) and key:
            return key
        # 按场景从 settings 拿对应的 DIFY_API_KEY_<CODE>
        scenario_key = settings.dify_api_key_for(row.scenario_code)
        return scenario_key or None
