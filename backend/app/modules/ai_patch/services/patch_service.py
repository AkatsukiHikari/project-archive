"""
AI Patch 写入服务

设计稿 §5.2 第 3 条：``ai_patch`` 是唯一的 AI 写库通道。
任何 AI 写操作（自动挂接 / 自动编目 / KB 变更）经此服务落 staging 表，
等审核队列处理；不允许 AI 代码直接 INSERT/UPDATE 业务表。

P1 实现 ``create`` + ``compute_payload_hash``：让 tool_dispatch 在 P3 写类
能力接进来时有现成钩子。``approve`` / ``reject`` 落库逻辑留 P3 实装。
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.constants import (
    AUDIT_AI_PATCH_CREATE,
    GATE_REVIEW,
    PATCH_STATUS_PENDING,
    VALID_GATES,
    VALID_PATCH_STATUSES,
)
from app.modules.ai_patch.models.ai_patch import AIPatch
from app.modules.audit.repositories.audit_repository import SQLAlchemyAuditRepository
from app.modules.audit.schemas.audit_log import AuditLogCreate
from app.modules.audit.services.audit_service import AuditService

logger = logging.getLogger(__name__)


VALID_OPERATIONS: frozenset[str] = frozenset({"create", "update", "delete"})


def compute_payload_hash(payload: dict[str, Any]) -> str:
    """对 payload 做稳定 hash：sort_keys + ensure_ascii=False，避免顺序敏感。"""
    blob = json.dumps(payload or {}, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class PatchValidationError(ValueError):
    """patch 入参不合法（早于 DB 校验）。"""


class PatchService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID | None,
        scenario_code: str,
        target_type: str,
        operation: str,
        payload: dict[str, Any],
        citations: list[dict[str, Any]] | None = None,
        confidence: float | None = None,
        gate: str = GATE_REVIEW,
        target_id: uuid.UUID | None = None,
        session_id: uuid.UUID | None = None,
        workflow_version: str | None = None,
        dify_message_id: str | None = None,
    ) -> AIPatch:
        if operation not in VALID_OPERATIONS:
            raise PatchValidationError(f"非法 operation: {operation!r}")
        if gate not in VALID_GATES:
            raise PatchValidationError(f"非法 gate: {gate!r}")
        if not isinstance(payload, dict) or not payload:
            raise PatchValidationError("payload 不能为空")
        if operation in {"update", "delete"} and target_id is None:
            raise PatchValidationError(f"{operation} 操作必须提供 target_id")

        row = AIPatch(
            tenant_id=tenant_id,
            session_id=session_id,
            scenario_code=scenario_code,
            target_type=target_type,
            target_id=target_id,
            operation=operation,
            payload=payload,
            payload_hash=compute_payload_hash(payload),
            citations=list(citations or []),
            confidence=confidence,
            gate=gate,
            status=PATCH_STATUS_PENDING,
            workflow_version=workflow_version,
            dify_message_id=dify_message_id,
            create_by=user_id,
        )
        self._db.add(row)
        await self._db.flush()

        # 审计：patch 提交本身就是一次事件
        try:
            await AuditService(SQLAlchemyAuditRepository(self._db)).create_audit_log(
                AuditLogCreate(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    action=AUDIT_AI_PATCH_CREATE,
                    module="ai",
                    status="SUCCESS",
                    details={
                        "patch_id": str(row.id),
                        "scenario_code": scenario_code,
                        "target_type": target_type,
                        "operation": operation,
                        "gate": gate,
                        "confidence": confidence,
                        "workflow_version": workflow_version,
                    },
                )
            )
        except Exception:
            logger.warning("ai_patch_create 审计写入失败", exc_info=True)

        return row

    @staticmethod
    def verify_payload_unchanged(row: AIPatch) -> bool:
        """approve 时调；payload 被人在后台手改 → False（设计稿 §7.5）。"""
        return compute_payload_hash(row.payload) == row.payload_hash

    @staticmethod
    def is_terminal(status: str) -> bool:
        return status in {"approved", "rejected", "applied", "failed"}

    @staticmethod
    def is_valid_status(status: str) -> bool:
        return status in VALID_PATCH_STATUSES
