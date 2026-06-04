"""ai_patch.PatchService 单测（payload_hash + 入参校验，不依赖 DB）。"""
from __future__ import annotations

import json

import pytest

from app.modules.ai.constants import GATE_AUTO, GATE_REVIEW, PATCH_STATUS_APPLIED
from app.modules.ai_patch.services.patch_service import (
    PatchService,
    PatchValidationError,
    VALID_OPERATIONS,
    compute_payload_hash,
)


@pytest.mark.unit
def test_payload_hash_is_stable_across_key_order() -> None:
    a = {"create": {"DH": "X-001", "TM": "标题"}}
    b = {"create": {"TM": "标题", "DH": "X-001"}}
    assert compute_payload_hash(a) == compute_payload_hash(b)


@pytest.mark.unit
def test_payload_hash_detects_change() -> None:
    base = {"create": {"DH": "X-001", "TM": "标题"}}
    mutated = {"create": {"DH": "X-002", "TM": "标题"}}
    assert compute_payload_hash(base) != compute_payload_hash(mutated)


@pytest.mark.unit
def test_payload_hash_handles_unicode() -> None:
    payload = {"create": {"title": "档案 / 永久"}}
    # 不应在 ascii encode 步骤崩溃
    h = compute_payload_hash(payload)
    assert isinstance(h, str)
    assert len(h) == 64  # sha256 hex


@pytest.mark.unit
def test_valid_operations_locked_down() -> None:
    assert VALID_OPERATIONS == frozenset({"create", "update", "delete"})


@pytest.mark.unit
def test_is_terminal() -> None:
    assert PatchService.is_terminal("approved")
    assert PatchService.is_terminal("applied")
    assert PatchService.is_terminal("rejected")
    assert PatchService.is_terminal("failed")
    assert not PatchService.is_terminal("pending")


@pytest.mark.unit
def test_is_valid_status() -> None:
    assert PatchService.is_valid_status(PATCH_STATUS_APPLIED)
    assert not PatchService.is_valid_status("nonsense")


@pytest.mark.unit
def test_verify_payload_unchanged_true_when_match() -> None:
    payload = {"update": {"BGQX": {"from": "短期", "to": "永久"}}}

    class FakeRow:
        pass

    row = FakeRow()
    row.payload = payload
    row.payload_hash = compute_payload_hash(payload)

    assert PatchService.verify_payload_unchanged(row) is True


@pytest.mark.unit
def test_verify_payload_unchanged_false_when_tampered() -> None:
    payload = {"update": {"BGQX": {"from": "短期", "to": "永久"}}}

    class FakeRow:
        pass

    row = FakeRow()
    row.payload = payload
    row.payload_hash = compute_payload_hash({"hack": True})

    assert PatchService.verify_payload_unchanged(row) is False


# 入参校验（不需要 DB；create 在 add 前先校验）
import uuid


class _StubDB:
    def __init__(self):
        self.added = []

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        pass


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_rejects_invalid_operation() -> None:
    svc = PatchService(_StubDB())
    with pytest.raises(PatchValidationError, match="operation"):
        await svc.create(
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            scenario_code="attach",
            target_type="archive",
            operation="vaporize",  # bad
            payload={"create": {"x": 1}},
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_rejects_invalid_gate() -> None:
    svc = PatchService(_StubDB())
    with pytest.raises(PatchValidationError, match="gate"):
        await svc.create(
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            scenario_code="attach",
            target_type="archive",
            operation="create",
            payload={"create": {"x": 1}},
            gate="loose",  # bad
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_rejects_empty_payload() -> None:
    svc = PatchService(_StubDB())
    with pytest.raises(PatchValidationError, match="payload"):
        await svc.create(
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            scenario_code="attach",
            target_type="archive",
            operation="create",
            payload={},
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_update_requires_target_id() -> None:
    svc = PatchService(_StubDB())
    with pytest.raises(PatchValidationError, match="target_id"):
        await svc.create(
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            scenario_code="catalog",
            target_type="archive",
            operation="update",
            payload={"update": {"BGQX": {"from": "短期", "to": "永久"}}},
            target_id=None,  # 缺
        )
