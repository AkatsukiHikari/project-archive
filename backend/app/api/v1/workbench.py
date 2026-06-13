"""档案工作台聚合 API。

GET /workbench/overview — 一次返回 KPI 卡片 + 四个待办 Tab（每个 Tab 最多 10 条）：
  approval  待我审批：我是审核员的待审鉴定任务
  appraisal 待鉴定档案：我是鉴定员的进行中任务
  request   查档申请：办理中的利用申请
  alert     异常告警：近 30 天四性检测不合格批次
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.appraisal.models import AppraisalPlan, AppraisalTask
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.preservation.models.run import DetectionBatch
from app.modules.repository.models.archive import Archive
from app.modules.repository.models.fonds import Fonds
from app.modules.utilization.models.application import UtilizationApplication

router = APIRouter(prefix="/workbench", tags=["工作台"])

TAB_LIMIT = 10
APPRAISAL_ACTIVE = ("pending", "ai_running", "ai_done", "rejected")
USE_TYPE_LABELS = {
    "read": "查阅",
    "borrow": "借阅",
    "copy": "复制",
    "certificate": "出具证明",
}


class TodoItem(BaseModel):
    id: str
    title: str
    author: Optional[str] = None
    time: Optional[datetime] = None
    tag: Optional[str] = None
    tag_color: Optional[str] = None
    link: str


class TodoTab(BaseModel):
    key: str
    label: str
    count: int
    danger: bool = False
    items: list[TodoItem] = []


class WorkbenchKpi(BaseModel):
    fonds_count: int
    archive_total: int
    month_new: int
    todo_total: int


class WorkbenchOverview(BaseModel):
    kpi: WorkbenchKpi
    tabs: list[TodoTab]


@router.get("/overview", response_model=ResponseModel[WorkbenchOverview])
async def get_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id
    approval = await _approval_tab(db, current_user)
    appraisal = await _appraisal_tab(db, current_user)
    request_tab = await _request_tab(db, tenant_id)
    alert = await _alert_tab(db, tenant_id)
    kpi = await _kpi(
        db,
        tenant_id,
        approval.count + appraisal.count + request_tab.count + alert.count,
    )

    return success(
        WorkbenchOverview(
            kpi=kpi, tabs=[approval, appraisal, request_tab, alert]
        ).model_dump(mode="json")
    )


# ── KPI ───────────────────────────────────────────────────────────────────────


async def _kpi(db: AsyncSession, tenant_id, todo_total: int) -> WorkbenchKpi:
    fonds_stmt = (
        select(func.count()).select_from(Fonds).where(Fonds.is_deleted.is_(False))
    )
    archive_stmt = (
        select(func.count())
        .select_from(Archive)
        .where(Archive.is_deleted.is_(False), Archive.status != "destroyed")
    )
    month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    month_stmt = archive_stmt.where(Archive.create_time >= month_start)
    if tenant_id:
        fonds_stmt = fonds_stmt.where(Fonds.tenant_id == tenant_id)
        archive_stmt = archive_stmt.where(Archive.tenant_id == tenant_id)
        month_stmt = month_stmt.where(Archive.tenant_id == tenant_id)

    return WorkbenchKpi(
        fonds_count=(await db.execute(fonds_stmt)).scalar_one(),
        archive_total=(await db.execute(archive_stmt)).scalar_one(),
        month_new=(await db.execute(month_stmt)).scalar_one(),
        todo_total=todo_total,
    )


# ── 待我审批（鉴定审核）──────────────────────────────────────────────────────


async def _approval_tab(db: AsyncSession, user: User) -> TodoTab:
    stmt = (
        select(AppraisalTask, AppraisalPlan)
        .join(AppraisalPlan, AppraisalTask.plan_id == AppraisalPlan.id)
        .where(
            AppraisalTask.is_deleted.is_(False),
            AppraisalTask.status == "submitted",
            AppraisalPlan.reviewer_id == user.id,
        )
    )
    rows, total = await _page(db, stmt, AppraisalTask.submitted_at.desc())
    assignee_ids = {t.assignee_id for t, _ in rows}
    names = await _user_names(db, assignee_ids)
    items = [
        TodoItem(
            id=str(task.id),
            title=f"鉴定任务待审核 - 全宗 {task.QZH} {task.fonds_name or ''}（{task.total} 件）",
            author=names.get(task.assignee_id),
            time=task.submitted_at,
            tag=plan.name,
            tag_color="blue",
            link="/archive/appraisal/review",
        )
        for task, plan in rows
    ]
    return TodoTab(key="approval", label="待我审批", count=total, items=items)


# ── 待鉴定档案 ────────────────────────────────────────────────────────────────


async def _appraisal_tab(db: AsyncSession, user: User) -> TodoTab:
    stmt = (
        select(AppraisalTask, AppraisalPlan)
        .join(AppraisalPlan, AppraisalTask.plan_id == AppraisalPlan.id)
        .where(
            AppraisalTask.is_deleted.is_(False),
            AppraisalTask.status.in_(APPRAISAL_ACTIVE),
            AppraisalTask.assignee_id == user.id,
        )
    )
    rows, total = await _page(db, stmt, AppraisalTask.create_time.desc())
    leader_ids = {p.leader_id for _, p in rows}
    names = await _user_names(db, leader_ids)
    items = [
        TodoItem(
            id=str(task.id),
            title=f"开放鉴定 - 全宗 {task.QZH} {task.fonds_name or ''}（{task.total} 件）",
            author=names.get(plan.leader_id),
            time=task.create_time,
            tag="已驳回" if task.status == "rejected" else plan.name,
            tag_color="red" if task.status == "rejected" else "blue",
            link="/archive/appraisal/evaluate",
        )
        for task, plan in rows
    ]
    return TodoTab(key="appraisal", label="待鉴定档案", count=total, items=items)


# ── 查档申请 ──────────────────────────────────────────────────────────────────


async def _request_tab(db: AsyncSession, tenant_id) -> TodoTab:
    stmt = select(UtilizationApplication).where(
        UtilizationApplication.is_deleted.is_(False),
        UtilizationApplication.status == "processing",
    )
    if tenant_id:
        stmt = stmt.where(UtilizationApplication.tenant_id == tenant_id)
    rows, total = await _page(db, stmt, UtilizationApplication.create_time.desc())
    items = [
        TodoItem(
            id=str(app.id),
            title=f"查档申请 - {app.applicant_name}（{USE_TYPE_LABELS.get(app.use_type, app.use_type)}）",
            author=app.organization or app.applicant_name,
            time=app.create_time,
            tag=app.reg_no,
            tag_color="cyan",
            link="/archive/utilization/apply",
        )
        for (app,) in rows
    ]
    return TodoTab(key="request", label="查档申请", count=total, items=items)


# ── 异常告警 ──────────────────────────────────────────────────────────────────


async def _alert_tab(db: AsyncSession, tenant_id) -> TodoTab:
    since = datetime.now(timezone.utc) - timedelta(days=30)
    stmt = select(DetectionBatch).where(
        DetectionBatch.is_deleted.is_(False),
        DetectionBatch.conclusion == "fail",
        DetectionBatch.create_time >= since,
    )
    if tenant_id:
        stmt = stmt.where(DetectionBatch.tenant_id == tenant_id)
    rows, total = await _page(db, stmt, DetectionBatch.create_time.desc())
    items = [
        TodoItem(
            id=str(batch.id),
            title=f"四性检测不合格 - {batch.scope_label or batch.batch_no}（不合格 {batch.failed} 件）",
            author="系统自动",
            time=batch.create_time,
            tag=batch.batch_no,
            tag_color="red",
            link="/archive/storage/detection",
        )
        for (batch,) in rows
    ]
    return TodoTab(key="alert", label="异常告警", count=total, danger=True, items=items)


# ── 内部 ──────────────────────────────────────────────────────────────────────


async def _page(db: AsyncSession, stmt, order_by) -> tuple[list, int]:
    total = (
        await db.execute(select(func.count()).select_from(stmt.subquery()))
    ).scalar_one()
    rows = (await db.execute(stmt.order_by(order_by).limit(TAB_LIMIT))).all()
    return rows, total


async def _user_names(db: AsyncSession, ids: set) -> dict[uuid.UUID, str]:
    ids = {i for i in ids if i}
    if not ids:
        return {}
    users = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    return {u.id: (u.full_name or u.username) for u in users}
