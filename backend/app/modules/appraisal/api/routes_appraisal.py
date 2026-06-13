"""开放鉴定 API。

挂载前缀： /appraisal

圈定预览  GET  /scope-preview
鉴定计划  POST/GET /plans, GET /plans/{id}
鉴定任务  GET /tasks, GET /tasks/{id}, GET /tasks/{id}/items,
          POST /tasks/{id}/ai-run | /adopt-ai | /submit | /approve | /reject
明细结论  PUT  /items/{id}/decide
鉴定台账  GET  /ledger
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.core.security.permissions import require_permissions
from app.infra.db.session import get_db
from app.modules.appraisal.schemas.plan import (ItemDecide, ItemOut, ItemPage,
                                                LedgerPage, PlanCreate,
                                                PlanDetail, PlanOut,
                                                ScopePreviewOut, TaskDetail,
                                                TaskOut, TaskReject)
from app.modules.appraisal.services.ai_engine import AiAppraisalEngine
from app.modules.appraisal.services.plan_service import PlanService
from app.modules.appraisal.services.task_service import TaskService
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User

router = APIRouter(prefix="/appraisal", tags=["档案鉴定"])


def _item_out(item) -> dict:
    return ItemOut.model_validate(item).model_dump(mode="json")


# ── 圈定预览 / 计划 ───────────────────────────────────────────────────────────


@router.get("/scope-preview", response_model=ResponseModel[ScopePreviewOut])
async def scope_preview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:plan")),
):
    svc = PlanService(db)
    data = await svc.scope_preview(current_user.tenant_id)
    return success(ScopePreviewOut.model_validate(data).model_dump(mode="json"))


@router.post("/plans", response_model=ResponseModel[PlanDetail])
async def create_plan(
    body: PlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:plan")),
):
    svc = PlanService(db)
    plan = await svc.create_plan(body, current_user.id, current_user.tenant_id)
    await db.commit()
    data = await svc.get_plan(plan.id, current_user.tenant_id)
    return success(PlanDetail.model_validate(data).model_dump(mode="json"))


@router.get("/plans", response_model=ResponseModel[dict])
async def list_plans(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = PlanService(db)
    total, plans = await svc.list_plans(
        current_user.tenant_id, status=status, skip=skip, limit=limit
    )
    items = [PlanOut.model_validate(p).model_dump(mode="json") for p in plans]
    return success({"total": total, "items": items})


@router.get("/plans/{plan_id}", response_model=ResponseModel[PlanDetail])
async def get_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = PlanService(db)
    data = await svc.get_plan(plan_id, current_user.tenant_id)
    return success(PlanDetail.model_validate(data).model_dump(mode="json"))


# ── 任务 ──────────────────────────────────────────────────────────────────────


@router.get("/tasks", response_model=ResponseModel[dict])
async def list_tasks(
    role: str = Query("assignee", pattern="^(assignee|reviewer)$"),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskService(db)
    total, tasks = await svc.list_my_tasks(
        current_user.id,
        current_user.tenant_id,
        role=role,
        status=status,
        skip=skip,
        limit=limit,
    )
    items = [TaskOut.model_validate(t).model_dump(mode="json") for t in tasks]
    return success({"total": total, "items": items})


@router.get("/tasks/{task_id}", response_model=ResponseModel[TaskDetail])
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskService(db)
    data = await svc.get_task(task_id, current_user.tenant_id)
    return success(TaskDetail.model_validate(data).model_dump(mode="json"))


@router.get("/tasks/{task_id}/items", response_model=ResponseModel[ItemPage])
async def list_task_items(
    task_id: uuid.UUID,
    status: Optional[str] = Query(None, pattern="^(pending|decided)$"),
    kfzt: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskService(db)
    total, items = await svc.list_items(
        task_id,
        current_user.tenant_id,
        status=status,
        kfzt=kfzt,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )
    return success({"total": total, "items": [_item_out(i) for i in items]})


@router.post("/tasks/{task_id}/ai-run", response_model=ResponseModel[TaskOut])
async def run_ai(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:evaluate")),
):
    """AI 预鉴定：规则阶段同步完成，LLM 语义复核转后台。"""
    svc = TaskService(db)
    task, _ = await svc._require_task(task_id, current_user.tenant_id)
    svc._assert_assignee(task, current_user)
    svc._assert_editable(task)

    engine = AiAppraisalEngine(db)
    await engine.start(task, current_user.id)
    await db.commit()
    AiAppraisalEngine.spawn_llm_stage(task_id, current_user.id)
    return success(
        TaskOut.model_validate(
            await svc.get_task(task_id, current_user.tenant_id)
        ).model_dump(mode="json")
    )


@router.post("/tasks/{task_id}/adopt-ai", response_model=ResponseModel[dict])
async def adopt_ai(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:evaluate")),
):
    svc = TaskService(db)
    adopted = await svc.adopt_ai(task_id, current_user, current_user.tenant_id)
    await db.commit()
    return success({"adopted": adopted})


@router.put("/items/{item_id}/decide", response_model=ResponseModel[ItemOut])
async def decide_item(
    item_id: uuid.UUID,
    body: ItemDecide,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:evaluate")),
):
    svc = TaskService(db)
    item = await svc.decide_item(item_id, body, current_user, current_user.tenant_id)
    await db.commit()
    return success(_item_out(item))


@router.post("/tasks/{task_id}/submit", response_model=ResponseModel[TaskOut])
async def submit_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:evaluate")),
):
    svc = TaskService(db)
    await svc.submit_task(task_id, current_user, current_user.tenant_id)
    await db.commit()
    return success(
        TaskOut.model_validate(
            await svc.get_task(task_id, current_user.tenant_id)
        ).model_dump(mode="json")
    )


@router.post("/tasks/{task_id}/approve", response_model=ResponseModel[TaskOut])
async def approve_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:review")),
):
    svc = TaskService(db)
    await svc.approve_task(task_id, current_user, current_user.tenant_id)
    await db.commit()
    return success(
        TaskOut.model_validate(
            await svc.get_task(task_id, current_user.tenant_id)
        ).model_dump(mode="json")
    )


@router.post("/tasks/{task_id}/reject", response_model=ResponseModel[TaskOut])
async def reject_task(
    task_id: uuid.UUID,
    body: TaskReject,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("appraisal:review")),
):
    svc = TaskService(db)
    await svc.reject_task(task_id, body.reason, current_user, current_user.tenant_id)
    await db.commit()
    return success(
        TaskOut.model_validate(
            await svc.get_task(task_id, current_user.tenant_id)
        ).model_dump(mode="json")
    )


# ── 台账 ──────────────────────────────────────────────────────────────────────


@router.get("/ledger", response_model=ResponseModel[LedgerPage])
async def list_ledger(
    qzh: Optional[str] = Query(None),
    kfzt: Optional[str] = Query(None),
    plan_id: Optional[uuid.UUID] = Query(None),
    keyword: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = TaskService(db)
    total, entries = await svc.list_ledger(
        current_user.tenant_id,
        qzh=qzh,
        kfzt=kfzt,
        plan_id=plan_id,
        keyword=keyword,
        skip=skip,
        limit=limit,
    )
    return success(
        LedgerPage.model_validate({"total": total, "items": entries}).model_dump(
            mode="json"
        )
    )
