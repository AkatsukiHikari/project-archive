"""场景路由单测。"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.config import settings
from app.modules.ai.services import scenario_router as sr_module
from app.modules.ai.services.scenario_router import (
    ScenarioDisabledError,
    ScenarioNotFoundError,
    ScenarioRouter,
)


TENANT = uuid.uuid4()


class _StubDB:
    """最小 fake DB；可分别让 fetch 返回 None 或 fake row。"""

    def __init__(self, row: Any | None = None):
        self._row = row

    async def execute(self, _stmt) -> Any:
        row = self._row
        return SimpleNamespace(scalar_one_or_none=lambda: row)


def _row(**overrides):
    base = dict(
        id=uuid.uuid4(),
        tenant_id=TENANT,
        scenario_code="qa",
        name="智能问答",
        description=None,
        enabled=True,
        dify_app_id="app-qa",
        dify_workflow_id=None,
        workflow_version="v1",
        default_model_tier="准",
        model_mapping={"准": {"provider": "qwen", "model": "qwen-max"}},
        gate="review",
        citation_required=True,
        extra_config={},
        is_deleted=False,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.unit
def test_unknown_scenario_raises_not_found() -> None:
    router = ScenarioRouter(_StubDB(None))
    with pytest.raises(ScenarioNotFoundError):
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            router.resolve(tenant_id=TENANT, scenario_code="not_a_real_code")
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_capability_disabled_by_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_ENABLED_CAPABILITIES", "qa")
    router = ScenarioRouter(_StubDB(_row(scenario_code="search")))
    with pytest.raises(ScenarioDisabledError):
        await router.resolve(tenant_id=TENANT, scenario_code="search")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_db_row_disabled_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_ENABLED_CAPABILITIES", "qa")
    router = ScenarioRouter(_StubDB(_row(enabled=False)))
    with pytest.raises(ScenarioDisabledError):
        await router.resolve(tenant_id=TENANT, scenario_code="qa")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_no_row_falls_back_to_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_ENABLED_CAPABILITIES", "qa")
    monkeypatch.setattr(settings, "AI_DEFAULT_MODEL_TIER", "准")
    monkeypatch.setattr(settings, "AI_PATCH_DEFAULT_GATE", "review")
    monkeypatch.setattr(settings, "AI_CITATION_REQUIRED", True)

    router = ScenarioRouter(_StubDB(None))
    resolved = await router.resolve(tenant_id=TENANT, scenario_code="qa")

    assert resolved.scenario_code == "qa"
    assert resolved.model_tier == "准"
    assert resolved.gate == "review"
    assert resolved.citation_required is True
    assert resolved.dify_app_id is None  # 未配置


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_with_row_uses_db_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_ENABLED_CAPABILITIES", "qa")
    router = ScenarioRouter(_StubDB(_row()))
    resolved = await router.resolve(tenant_id=TENANT, scenario_code="qa")

    assert resolved.dify_app_id == "app-qa"
    assert resolved.workflow_version == "v1"
    assert resolved.model_provider == "qwen"
    assert resolved.model_name == "qwen-max"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_invalid_model_tier_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_ENABLED_CAPABILITIES", "qa")
    router = ScenarioRouter(_StubDB(_row(default_model_tier="思考")))
    resolved = await router.resolve(
        tenant_id=TENANT, scenario_code="qa", model_tier="garbage"
    )
    assert resolved.model_tier == "思考"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_extra_config_api_key_overrides_global(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_ENABLED_CAPABILITIES", "qa")
    monkeypatch.setattr(settings, "DIFY_API_KEY", "global-key")
    router = ScenarioRouter(_StubDB(_row(extra_config={"dify_api_key": "scenario-key"})))
    resolved = await router.resolve(tenant_id=TENANT, scenario_code="qa")
    assert resolved.dify_api_key == "scenario-key"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_key_falls_back_to_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_ENABLED_CAPABILITIES", "qa")
    monkeypatch.setattr(settings, "DIFY_API_KEY", "global-key")
    router = ScenarioRouter(_StubDB(_row(extra_config={})))
    resolved = await router.resolve(tenant_id=TENANT, scenario_code="qa")
    assert resolved.dify_api_key == "global-key"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_api_key_none_when_settings_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_ENABLED_CAPABILITIES", "qa")
    monkeypatch.setattr(settings, "DIFY_API_KEY", "")
    router = ScenarioRouter(_StubDB(_row(extra_config={})))
    resolved = await router.resolve(tenant_id=TENANT, scenario_code="qa")
    assert resolved.dify_api_key is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_valid_model_tier_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "AI_ENABLED_CAPABILITIES", "qa")
    router = ScenarioRouter(_StubDB(_row(
        default_model_tier="准",
        model_mapping={
            "快":   {"provider": "qwen", "model": "qwen-turbo"},
            "准":   {"provider": "qwen", "model": "qwen-max"},
            "思考": {"provider": "deepseek", "model": "ds-r1"},
        },
    )))
    resolved = await router.resolve(
        tenant_id=TENANT, scenario_code="qa", model_tier="思考"
    )
    assert resolved.model_tier == "思考"
    assert resolved.model_provider == "deepseek"
    assert resolved.model_name == "ds-r1"
