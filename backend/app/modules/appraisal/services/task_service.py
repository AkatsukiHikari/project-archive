"""鉴定任务：鉴定员核对结论 → 提交 → 审核员审核 → 结论回写档案。"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.error_code import ErrorCode
from app.common.exceptions.base import (
    AuthorizationException,
    NotFoundException,
    ValidationException,
)
from app.modules.appraisal.models import AppraisalItem, AppraisalPlan, AppraisalTask
from app.modules.appraisal.schemas.plan import ItemDecide
from app.modules.appraisal.services.plan_service import PlanService
from app.modules.iam.models.user import User
from app.modules.repository.models.archive import Archive

# 鉴定员可继续操作的任务状态
EDITABLE_STATUSES = ("pending", "ai_running", "ai_done", "rejected")


class TaskService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── 查询 ──────────────────────────────────────────────────────────────────

    async def list_my_tasks(
        self,
        user_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
        role: str = "assignee",
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[dict]]:
        """role=assignee 我鉴定的任务；role=reviewer 我审核的任务。"""
        stmt = (
            select(AppraisalTask, AppraisalPlan)
            .join(AppraisalPlan, AppraisalTask.plan_id == AppraisalPlan.id)
            .where(
                AppraisalTask.is_deleted.is_(False),
                AppraisalPlan.is_deleted.is_(False),
            )
        )
        if role == "reviewer":
            stmt = stmt.where(AppraisalPlan.reviewer_id == user_id)
        else:
            stmt = stmt.where(AppraisalTask.assignee_id == user_id)
        if tenant_id:
            stmt = stmt.where(AppraisalTask.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(AppraisalTask.status == status)

        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (
            await self.db.execute(
                stmt.order_by(AppraisalTask.create_time.desc())
                .offset(skip)
                .limit(limit)
            )
        ).all()

        tasks = [r[0] for r in rows]
        plan_svc = PlanService(self.db)
        decided_map = await plan_svc._decided_counts([t.id for t in tasks])
        names = await plan_svc._user_names({t.assignee_id for t in tasks})

        result = []
        for task, plan in rows:
            d = PlanService._task_dict(task, names, decided_map)
            d["plan_name"] = plan.name
            d["plan_no"] = plan.plan_no
            result.append(d)
        return total, result

    async def get_task(
        self, task_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> dict:
        task, plan = await self._require_task(task_id, tenant_id)
        plan_svc = PlanService(self.db)
        names = await plan_svc._user_names({task.assignee_id})
        decided_map = await plan_svc._decided_counts([task.id])
        data = PlanService._task_dict(task, names, decided_map)
        data["plan_name"] = plan.name
        data["plan_no"] = plan.plan_no

        counts = (
            await self.db.execute(
                select(AppraisalItem.ai_status, func.count())
                .where(
                    AppraisalItem.task_id == task.id,
                    AppraisalItem.is_deleted.is_(False),
                )
                .group_by(AppraisalItem.ai_status)
            )
        ).all()
        ai_counts = {r[0]: r[1] for r in counts}
        data["ai_done"] = ai_counts.get("done", 0)
        data["pending"] = task.total - data["decided"]
        return data

    async def list_items(
        self,
        task_id: uuid.UUID,
        tenant_id: Optional[uuid.UUID],
        status: Optional[str] = None,
        kfzt: Optional[str] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[AppraisalItem]]:
        await self._require_task(task_id, tenant_id)
        stmt = select(AppraisalItem).where(
            AppraisalItem.task_id == task_id, AppraisalItem.is_deleted.is_(False)
        )
        if status:
            stmt = stmt.where(AppraisalItem.status == status)
        if kfzt:
            stmt = stmt.where(AppraisalItem.ai_kfzt == kfzt)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                AppraisalItem.TM.ilike(like) | AppraisalItem.DH.ilike(like)
            )

        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        items = (
            (
                await self.db.execute(
                    stmt.order_by(AppraisalItem.DH.asc().nulls_last())
                    .offset(skip)
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return total, items

    # ── 鉴定员操作 ────────────────────────────────────────────────────────────

    async def decide_item(
        self,
        item_id: uuid.UUID,
        body: ItemDecide,
        user: User,
        tenant_id: Optional[uuid.UUID],
    ) -> AppraisalItem:
        item = await self._require_item(item_id, tenant_id)
        task, _ = await self._require_task(item.task_id, tenant_id)
        self._assert_assignee(task, user)
        self._assert_editable(task)

        item.final_kfzt = body.final_kfzt
        item.final_reason = body.final_reason
        item.final_standard_code = body.final_standard_code
        item.status = "decided"
        item.decided_by = user.id
        item.decided_at = datetime.now(timezone.utc)
        await self.db.flush()
        return item

    async def adopt_ai(
        self, task_id: uuid.UUID, user: User, tenant_id: Optional[uuid.UUID]
    ) -> int:
        """批量采纳：把所有未定且有 AI 建议的明细按建议落人工结论。"""
        task, _ = await self._require_task(task_id, tenant_id)
        self._assert_assignee(task, user)
        self._assert_editable(task)

        result = await self.db.execute(
            update(AppraisalItem)
            .where(
                AppraisalItem.task_id == task_id,
                AppraisalItem.is_deleted.is_(False),
                AppraisalItem.status == "pending",
                AppraisalItem.ai_kfzt.is_not(None),
            )
            .values(
                final_kfzt=AppraisalItem.ai_kfzt,
                final_reason=AppraisalItem.ai_reason,
                final_standard_code=AppraisalItem.ai_standard_code,
                status="decided",
                decided_by=user.id,
                decided_at=datetime.now(timezone.utc),
            )
        )
        return result.rowcount or 0

    async def submit_task(
        self, task_id: uuid.UUID, user: User, tenant_id: Optional[uuid.UUID]
    ) -> AppraisalTask:
        task, _ = await self._require_task(task_id, tenant_id)
        self._assert_assignee(task, user)
        self._assert_editable(task)

        undecided = (
            await self.db.execute(
                select(func.count())
                .select_from(AppraisalItem)
                .where(
                    AppraisalItem.task_id == task_id,
                    AppraisalItem.is_deleted.is_(False),
                    AppraisalItem.status != "decided",
                )
            )
        ).scalar_one()
        if undecided:
            raise ValidationException(
                code=ErrorCode.APPRAISAL_ITEMS_UNDECIDED,
                message=f"还有 {undecided} 件档案未给出鉴定结论，不能提交审核",
            )

        task.status = "submitted"
        task.submitted_at = datetime.now(timezone.utc)
        task.reject_reason = None
        await self.db.flush()
        return task

    # ── 审核员操作 ────────────────────────────────────────────────────────────

    async def approve_task(
        self, task_id: uuid.UUID, user: User, tenant_id: Optional[uuid.UUID]
    ) -> AppraisalTask:
        task, plan = await self._require_task(task_id, tenant_id)
        self._assert_reviewer(plan, user)
        if task.status != "submitted":
            raise ValidationException(
                code=ErrorCode.APPRAISAL_STATE_CONFLICT, message="任务不在待审核状态"
            )

        await self._writeback_archives(task)
        task.status = "approved"
        task.reviewed_at = datetime.now(timezone.utc)
        await PlanService(self.db).refresh_plan_status(task.plan_id)
        await self.db.flush()
        return task

    async def reject_task(
        self,
        task_id: uuid.UUID,
        reason: str,
        user: User,
        tenant_id: Optional[uuid.UUID],
    ) -> AppraisalTask:
        task, plan = await self._require_task(task_id, tenant_id)
        self._assert_reviewer(plan, user)
        if task.status != "submitted":
            raise ValidationException(
                code=ErrorCode.APPRAISAL_STATE_CONFLICT, message="任务不在待审核状态"
            )
        task.status = "rejected"
        task.reject_reason = reason
        task.reviewed_at = datetime.now(timezone.utc)
        await self.db.flush()
        return task

    async def _writeback_archives(self, task: AppraisalTask) -> None:
        """审核通过：仅回写档案的当前开放状态（KFZT）。

        鉴定日期/理由/引用标准属于鉴定过程元数据，留在 appr_task/appr_item，
        不冗余到档案表；需要时按 archive_id 关联查最近一条审核通过的鉴定明细。
        """
        items = (
            (
                await self.db.execute(
                    select(AppraisalItem).where(
                        AppraisalItem.task_id == task.id,
                        AppraisalItem.is_deleted.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
        for item in items:
            stmt = (
                update(Archive)
                .where(Archive.id == item.archive_id)
                .values(KFZT=item.final_kfzt)
            )
            if item.ND is not None:
                stmt = stmt.where(Archive.ND == item.ND)  # 分区裁剪
            await self.db.execute(stmt)

    # ── 档案最近鉴定结论（按 archive_id 关联查，替代档案表的 JDRQ/KFLY 快照）──

    async def latest_conclusion(
        self, archive_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> Optional[dict]:
        """某档案最近一条审核通过的鉴定结论：开放状态/理由/引用标准/鉴定日期/所属计划。"""
        stmt = (
            select(AppraisalItem, AppraisalTask, AppraisalPlan)
            .join(AppraisalTask, AppraisalItem.task_id == AppraisalTask.id)
            .join(AppraisalPlan, AppraisalItem.plan_id == AppraisalPlan.id)
            .where(
                AppraisalItem.archive_id == archive_id,
                AppraisalItem.is_deleted.is_(False),
                AppraisalTask.status == "approved",
            )
            .order_by(AppraisalTask.reviewed_at.desc())
            .limit(1)
        )
        if tenant_id:
            stmt = stmt.where(AppraisalItem.tenant_id == tenant_id)
        row = (await self.db.execute(stmt)).first()
        if not row:
            return None
        item, task, plan = row
        return {
            "kfzt": item.final_kfzt,
            "reason": item.final_reason,
            "standard_code": item.final_standard_code,
            "appraised_at": (
                task.reviewed_at.date().isoformat() if task.reviewed_at else None
            ),
            "plan_no": plan.plan_no,
            "plan_name": plan.name,
        }

    # ── 鉴定台账（审核通过的明细）─────────────────────────────────────────────

    async def list_ledger(
        self,
        tenant_id: Optional[uuid.UUID],
        qzh: Optional[str] = None,
        kfzt: Optional[str] = None,
        plan_id: Optional[uuid.UUID] = None,
        keyword: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[int, list[dict]]:
        stmt = (
            select(AppraisalItem, AppraisalTask, AppraisalPlan)
            .join(AppraisalTask, AppraisalItem.task_id == AppraisalTask.id)
            .join(AppraisalPlan, AppraisalItem.plan_id == AppraisalPlan.id)
            .where(
                AppraisalItem.is_deleted.is_(False),
                AppraisalTask.status == "approved",
            )
        )
        if tenant_id:
            stmt = stmt.where(AppraisalItem.tenant_id == tenant_id)
        if qzh:
            stmt = stmt.where(AppraisalItem.QZH == qzh)
        if kfzt:
            stmt = stmt.where(AppraisalItem.final_kfzt == kfzt)
        if plan_id:
            stmt = stmt.where(AppraisalItem.plan_id == plan_id)
        if keyword:
            like = f"%{keyword}%"
            stmt = stmt.where(
                AppraisalItem.TM.ilike(like) | AppraisalItem.DH.ilike(like)
            )

        total = (
            await self.db.execute(select(func.count()).select_from(stmt.subquery()))
        ).scalar_one()
        rows = (
            await self.db.execute(
                stmt.order_by(AppraisalTask.reviewed_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).all()

        entries = []
        for item, task, plan in rows:
            data = {
                c: getattr(item, c)
                for c in (
                    "id",
                    "task_id",
                    "archive_id",
                    "ND",
                    "DH",
                    "TM",
                    "QZH",
                    "MJ",
                    "BGQX",
                    "due_basis",
                    "ai_status",
                    "ai_kfzt",
                    "ai_reason",
                    "ai_hit_words",
                    "ai_standard_code",
                    "ai_confidence",
                    "status",
                    "final_kfzt",
                    "final_reason",
                    "final_standard_code",
                    "decided_at",
                )
            }
            data["plan_name"] = plan.name
            data["plan_no"] = plan.plan_no
            data["reviewed_at"] = task.reviewed_at
            entries.append(data)
        return total, entries

    # ── 校验 ──────────────────────────────────────────────────────────────────

    async def _require_task(
        self, task_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> tuple[AppraisalTask, AppraisalPlan]:
        stmt = (
            select(AppraisalTask, AppraisalPlan)
            .join(AppraisalPlan, AppraisalTask.plan_id == AppraisalPlan.id)
            .where(AppraisalTask.id == task_id, AppraisalTask.is_deleted.is_(False))
        )
        if tenant_id:
            stmt = stmt.where(AppraisalTask.tenant_id == tenant_id)
        row = (await self.db.execute(stmt)).first()
        if not row:
            raise NotFoundException(
                code=ErrorCode.APPRAISAL_TASK_NOT_FOUND, message="鉴定任务不存在"
            )
        return row[0], row[1]

    async def _require_item(
        self, item_id: uuid.UUID, tenant_id: Optional[uuid.UUID]
    ) -> AppraisalItem:
        stmt = select(AppraisalItem).where(
            AppraisalItem.id == item_id, AppraisalItem.is_deleted.is_(False)
        )
        if tenant_id:
            stmt = stmt.where(AppraisalItem.tenant_id == tenant_id)
        item = (await self.db.execute(stmt)).scalars().first()
        if not item:
            raise NotFoundException(
                code=ErrorCode.APPRAISAL_ITEM_NOT_FOUND, message="鉴定明细不存在"
            )
        return item

    @staticmethod
    def _assert_assignee(task: AppraisalTask, user: User) -> None:
        if user.is_superadmin or user.username in ("admin", "superadmin"):
            return
        if task.assignee_id != user.id:
            raise AuthorizationException(
                code=ErrorCode.APPRAISAL_NOT_ASSIGNEE, message="只有任务鉴定员可以操作"
            )

    @staticmethod
    def _assert_reviewer(plan: AppraisalPlan, user: User) -> None:
        if user.is_superadmin or user.username in ("admin", "superadmin"):
            return
        if plan.reviewer_id != user.id:
            raise AuthorizationException(
                code=ErrorCode.APPRAISAL_NOT_REVIEWER, message="只有计划审核员可以审核"
            )

    @staticmethod
    def _assert_editable(task: AppraisalTask) -> None:
        if task.status not in EDITABLE_STATUSES:
            raise ValidationException(
                code=ErrorCode.APPRAISAL_STATE_CONFLICT,
                message="任务已提交或已完成，不能再修改",
            )
