"""鉴定计划：创建（圈定 + 分配任务）、查询。"""

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import NotFoundException, ValidationException
from app.modules.appraisal.models import (AppraisalItem, AppraisalPlan,
                                          AppraisalTask)
from app.modules.appraisal.schemas.plan import PlanCreate
from app.modules.appraisal.services.scope_service import (DueArchive,
                                                          ScopeService)
from app.modules.iam.models.user import User
from app.modules.repository.models.fonds import Fonds


class PlanService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.scope = ScopeService(db)

    # ── 圈定预览 ──────────────────────────────────────────────────────────────

    async def scope_preview(self, tenant_id: Optional[uuid.UUID]) -> dict:
        due = await self.scope.find_due_archives(tenant_id)
        groups = await self.scope.group_by_fonds(due, tenant_id)
        return {"total": len(due), "groups": groups}

    # ── 创建计划 ──────────────────────────────────────────────────────────────

    async def create_plan(
        self, body: PlanCreate, leader_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> AppraisalPlan:
        due = await self.scope.find_due_archives(tenant_id)
        by_fonds: dict[uuid.UUID, list[DueArchive]] = {}
        for d in due:
            by_fonds.setdefault(d.archive.fonds_id, []).append(d)

        fonds_ids = [t.fonds_id for t in body.tasks]
        if len(set(fonds_ids)) != len(fonds_ids):
            raise ValidationException(message="同一全宗不能重复分配任务")

        missing = [fid for fid in fonds_ids if not by_fonds.get(fid)]
        if missing:
            raise ValidationException(
                code=ErrorCode.APPRAISAL_NO_ARCHIVES,
                message="所选全宗下已无到期待鉴定档案，请刷新圈定预览",
            )

        fonds_map = {
            f.id: f
            for f in (
                await self.db.execute(
                    select(Fonds).where(
                        Fonds.id.in_(fonds_ids), Fonds.is_deleted.is_(False)
                    )
                )
            ).scalars()
        }

        plan = AppraisalPlan(
            plan_no=await self._next_plan_no(),
            name=body.name,
            appraisal_type="open",
            leader_id=leader_id,
            reviewer_id=body.reviewer_id,
            description=body.description,
            status="in_progress",
            tenant_id=tenant_id,
            create_by=leader_id,
        )
        self.db.add(plan)
        await self.db.flush()

        total_archives = 0
        for assign in body.tasks:
            fonds = fonds_map.get(assign.fonds_id)
            if not fonds:
                raise NotFoundException(
                    code=ErrorCode.FONDS_NOT_FOUND, message="全宗不存在"
                )
            dues = by_fonds[assign.fonds_id]
            task = AppraisalTask(
                plan_id=plan.id,
                fonds_id=fonds.id,
                QZH=fonds.fonds_code,
                fonds_name=fonds.name,
                assignee_id=assign.assignee_id,
                status="pending",
                total=len(dues),
                tenant_id=tenant_id,
                create_by=leader_id,
            )
            self.db.add(task)
            await self.db.flush()

            for d in dues:
                a = d.archive
                self.db.add(
                    AppraisalItem(
                        task_id=task.id,
                        plan_id=plan.id,
                        archive_id=a.id,
                        ND=a.ND,
                        DH=a.DH,
                        TM=a.TM,
                        QZH=a.QZH,
                        MJ=a.MJ,
                        BGQX=a.BGQX,
                        due_basis=d.due_basis,
                        tenant_id=tenant_id,
                        create_by=leader_id,
                    )
                )
            total_archives += len(dues)

        plan.total_tasks = len(body.tasks)
        plan.total_archives = total_archives
        await self.db.flush()
        return plan

    async def _next_plan_no(self) -> str:
        today = date.today().strftime("%Y%m%d")
        prefix = f"JD{today}"
        count = (
            await self.db.execute(
                select(func.count())
                .select_from(AppraisalPlan)
                .where(AppraisalPlan.plan_no.like(f"{prefix}%"))
            )
        ).scalar_one()
        return f"{prefix}{count + 1:03d}"

    # ── 查询 ──────────────────────────────────────────────────────────────────

    async def list_plans(
        self,
        tenant_id: Optional[uuid.UUID],
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[dict]]:
        stmt = select(AppraisalPlan).where(AppraisalPlan.is_deleted.is_(False))
        if tenant_id:
            stmt = stmt.where(AppraisalPlan.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(AppraisalPlan.status == status)

        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        plans = (
            (
                await self.db.execute(
                    stmt.order_by(AppraisalPlan.create_time.desc())
                    .offset(skip)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )

        names = await self._user_names(
            {p.leader_id for p in plans} | {p.reviewer_id for p in plans}
        )
        return total, [self._plan_dict(p, names) for p in plans]

    async def get_plan(
        self, plan_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> dict:
        plan = await self._require_plan(plan_id, tenant_id)
        tasks = (
            (
                await self.db.execute(
                    select(AppraisalTask)
                    .where(
                        AppraisalTask.plan_id == plan.id,
                        AppraisalTask.is_deleted.is_(False),
                    )
                    .order_by(AppraisalTask.QZH)
                )
            )
            .scalars()
            .all()
        )

        decided_map = await self._decided_counts([t.id for t in tasks])
        names = await self._user_names(
            {plan.leader_id, plan.reviewer_id} | {t.assignee_id for t in tasks}
        )
        data = self._plan_dict(plan, names)
        data["tasks"] = [self._task_dict(t, names, decided_map) for t in tasks]
        return data

    async def _require_plan(
        self, plan_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> AppraisalPlan:
        stmt = select(AppraisalPlan).where(
            AppraisalPlan.id == plan_id, AppraisalPlan.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(AppraisalPlan.tenant_id == tenant_id)
        plan = (await self.db.execute(stmt)).scalars().first()
        if not plan:
            raise NotFoundException(
                code=ErrorCode.APPRAISAL_PLAN_NOT_FOUND, message="鉴定计划不存在"
            )
        return plan

    # ── 完成检测（任务全部 approved 时计划完结）─────────────────────────────

    async def refresh_plan_status(self, plan_id: uuid.UUID) -> None:
        unfinished = (
            await self.db.execute(
                select(func.count())
                .select_from(AppraisalTask)
                .where(
                    AppraisalTask.plan_id == plan_id,
                    AppraisalTask.is_deleted.is_(False),
                    AppraisalTask.status != "approved",
                )
            )
        ).scalar_one()
        if unfinished == 0:
            plan = (
                (
                    await self.db.execute(
                        select(AppraisalPlan).where(AppraisalPlan.id == plan_id)
                    )
                )
                .scalars()
                .first()
            )
            if plan and plan.status != "completed":
                plan.status = "completed"
                plan.finished_at = datetime.now(timezone.utc)

    # ── 内部 ──────────────────────────────────────────────────────────────────

    async def _user_names(self, ids: set) -> dict[uuid.UUID, str]:
        ids = {i for i in ids if i}
        if not ids:
            return {}
        users = (
            (await self.db.execute(select(User).where(User.id.in_(ids))))
            .scalars()
            .all()
        )
        return {u.id: (u.full_name or u.username) for u in users}

    async def _decided_counts(self, task_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
        if not task_ids:
            return {}
        rows = (
            await self.db.execute(
                select(AppraisalItem.task_id, func.count())
                .where(
                    AppraisalItem.task_id.in_(task_ids),
                    AppraisalItem.is_deleted.is_(False),
                    AppraisalItem.status == "decided",
                )
                .group_by(AppraisalItem.task_id)
            )
        ).all()
        return {r[0]: r[1] for r in rows}

    @staticmethod
    def _plan_dict(plan: AppraisalPlan, names: dict) -> dict:
        return {
            "id": plan.id,
            "plan_no": plan.plan_no,
            "name": plan.name,
            "appraisal_type": plan.appraisal_type,
            "leader_id": plan.leader_id,
            "leader_name": names.get(plan.leader_id),
            "reviewer_id": plan.reviewer_id,
            "reviewer_name": names.get(plan.reviewer_id),
            "status": plan.status,
            "description": plan.description,
            "total_tasks": plan.total_tasks,
            "total_archives": plan.total_archives,
            "finished_at": plan.finished_at,
            "create_time": plan.create_time,
        }

    @staticmethod
    def _task_dict(
        task: AppraisalTask, names: dict, decided_map: Optional[dict] = None
    ) -> dict:
        return {
            "id": task.id,
            "plan_id": task.plan_id,
            "fonds_id": task.fonds_id,
            "QZH": task.QZH,
            "fonds_name": task.fonds_name,
            "assignee_id": task.assignee_id,
            "assignee_name": names.get(task.assignee_id),
            "status": task.status,
            "total": task.total,
            "decided": (decided_map or {}).get(task.id, 0),
            "reject_reason": task.reject_reason,
            "submitted_at": task.submitted_at,
            "reviewed_at": task.reviewed_at,
            "create_time": task.create_time,
        }
