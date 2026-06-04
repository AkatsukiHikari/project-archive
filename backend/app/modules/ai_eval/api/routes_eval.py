"""
AI Eval 评测中心 API（P1 占位 + P2/P3 实装）。

P1 阶段只暴露：
- GET /v1/ai/eval/runs    — 评测历史列表（含趋势所需指标快照）
- GET /v1/ai/eval/golden  — 黄金集列表
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel
from app.infra.db.session import get_db
from app.modules.ai.constants import AUDIT_AI_EVAL_RUN
from app.modules.ai_eval.models.eval_run import EvalRun
from app.modules.ai_eval.models.golden_set import GoldenSetItem
from app.modules.ai_eval.schemas.eval import (
    EvalRunListItem,
    EvalRunListResponse,
    GoldenItem,
    GoldenListResponse,
)
from app.modules.ai._tenant_helper import ensure_tenant_id
from app.modules.ai_eval.services.runner import EvalRunner
from app.modules.audit.repositories.audit_repository import SQLAlchemyAuditRepository
from app.modules.audit.schemas.audit_log import AuditLogCreate
from app.modules.audit.services.audit_service import AuditService
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User

router = APIRouter()


@router.get(
    "/runs",
    summary="AI 评测历史列表",
    response_model=ResponseModel[EvalRunListResponse],
)
async def list_runs(
    scenario_code: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[EvalRunListResponse]:
    tenant_id = await ensure_tenant_id(db, current_user)
    base = select(EvalRun).where(
        EvalRun.tenant_id == tenant_id,
        EvalRun.is_deleted.is_(False),
    )
    if scenario_code:
        base = base.where(EvalRun.scenario_code == scenario_code)
    if status:
        base = base.where(EvalRun.status == status)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    stmt = base.order_by(EvalRun.create_time.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).scalars().all()
    items = [
        EvalRunListItem(
            id=row.id,
            scenario_code=row.scenario_code,
            workflow_version=row.workflow_version,
            model_tier=row.model_tier,
            status=row.status,
            total=row.total,
            passed=row.passed,
            metrics=row.metrics or {},
            threshold=row.threshold or {},
            blocked_upgrade=row.blocked_upgrade,
            create_time=row.create_time,
            update_time=row.update_time,
        )
        for row in rows
    ]
    return ResponseModel(data=EvalRunListResponse(total=total, items=items))


class EvalRunTrigger(BaseModel):
    scenario_code: str = Field(..., max_length=32)
    workflow_version: str | None = Field(default=None, max_length=32)
    model_tier: str | None = Field(default=None, max_length=8)
    threshold: dict[str, float] | None = None


@router.post(
    "/runs",
    summary="手动触发评测运行",
    response_model=ResponseModel[EvalRunListItem],
)
async def trigger_run(
    body: EvalRunTrigger,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[EvalRunListItem]:
    tenant_id = await ensure_tenant_id(db, current_user)
    runner = EvalRunner(db)
    run = await runner.run(
        tenant_id=tenant_id,
        scenario_code=body.scenario_code,
        workflow_version=body.workflow_version,
        model_tier=body.model_tier,
        threshold=body.threshold,
    )
    try:
        await AuditService(SQLAlchemyAuditRepository(db)).create_audit_log(
            AuditLogCreate(
                user_id=current_user.id,
                tenant_id=tenant_id,
                action=AUDIT_AI_EVAL_RUN,
                module="ai",
                status="SUCCESS",
                details={
                    "scenario_code": body.scenario_code,
                    "workflow_version": body.workflow_version,
                    "model_tier": body.model_tier,
                    "accuracy": run.metrics.get("accuracy"),
                    "total": run.total,
                    "passed": run.passed,
                    "blocked": run.blocked_upgrade,
                },
            )
        )
    except Exception:
        pass

    await db.commit()
    await db.refresh(run)
    return ResponseModel(
        data=EvalRunListItem(
            id=run.id,
            scenario_code=run.scenario_code,
            workflow_version=run.workflow_version,
            model_tier=run.model_tier,
            status=run.status,
            total=run.total,
            passed=run.passed,
            metrics=run.metrics or {},
            threshold=run.threshold or {},
            blocked_upgrade=run.blocked_upgrade,
            create_time=run.create_time,
            update_time=run.update_time,
        )
    )


@router.get(
    "/golden",
    summary="AI 评测黄金集列表",
    response_model=ResponseModel[GoldenListResponse],
)
async def list_golden(
    scenario_code: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResponseModel[GoldenListResponse]:
    tenant_id = await ensure_tenant_id(db, current_user)
    base = select(GoldenSetItem).where(
        GoldenSetItem.tenant_id == tenant_id,
        GoldenSetItem.is_deleted.is_(False),
    )
    if scenario_code:
        base = base.where(GoldenSetItem.scenario_code == scenario_code)
    if source:
        base = base.where(GoldenSetItem.source == source)

    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    stmt = base.order_by(GoldenSetItem.create_time.desc()).offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).scalars().all()
    items = [
        GoldenItem(
            id=row.id,
            scenario_code=row.scenario_code,
            input=row.input or {},
            expected=row.expected or {},
            tags=row.tags or [],
            source=row.source,
            note=row.note,
            create_time=row.create_time,
        )
        for row in rows
    ]
    return ResponseModel(data=GoldenListResponse(total=total, items=items))
