"""开放鉴定 计划 / 任务 / 明细 模型。

层级（做任务的模型）：
  AppraisalPlan（鉴定计划：组长制定，指定审核员）
    └── AppraisalTask（按全宗分配给鉴定员的任务）
          └── AppraisalItem（档案级明细：AI 建议 + 人工结论；审核通过后即台账记录）

状态机：
  plan: in_progress → completed（全部任务 approved 时）
  task: pending → ai_running → ai_done → submitted → approved
                                        ↘ rejected →（鉴定员修改后重新 submitted）
  item: pending（未定）→ decided（人工已定结论）
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class AppraisalPlan(BaseEntity):
    """鉴定计划（一次开放鉴定工作，含一组按全宗划分的任务）。"""

    __tablename__ = "appr_plan"

    plan_no: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True, comment="计划编号 JDyyyymmddNNN"
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="计划名称")
    appraisal_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="open",
        comment="鉴定类型: open 开放鉴定（value 价值鉴定预留）",
    )
    leader_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="组长（制定计划/分配任务）",
    )
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="审核员",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="in_progress",
        comment="in_progress 进行中 | completed 已完成",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="说明"
    )
    total_tasks: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="任务数"
    )
    total_archives: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="档案件数"
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="完成时间"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class AppraisalTask(BaseEntity):
    """鉴定任务（一个全宗 → 一个鉴定员）。"""

    __tablename__ = "appr_task"

    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appr_plan.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="CASCADE"),
        nullable=False,
        comment="目标全宗",
    )
    QZH: Mapped[str] = mapped_column(String(50), nullable=False, comment="全宗号快照")
    fonds_name: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="全宗名称快照"
    )
    assignee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="鉴定员",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending | ai_running | ai_done | submitted | approved | rejected",
    )
    total: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="档案件数"
    )
    reject_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="驳回原因"
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class AppraisalItem(BaseEntity):
    """鉴定明细（一件档案的鉴定记录；审核通过后即台账条目）。

    archive_id 指向 repo_archive（分区表，无 DB FK），冗余 DH/TM 等快照便于台账展示。
    """

    __tablename__ = "appr_item"

    task_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appr_task.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appr_plan.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="冗余计划 ID（台账查询）",
    )
    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True, comment="档案 ID（无 DB FK）"
    )
    ND: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="年度快照（分区键定位）"
    )
    DH: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="档号快照"
    )
    TM: Mapped[str] = mapped_column(String(512), nullable=False, comment="题名快照")
    QZH: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="全宗号快照"
    )
    MJ: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="密级快照"
    )
    BGQX: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="保管期限快照"
    )
    due_basis: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="到期依据，如 成文日期 2003-05-12 + 25年"
    )

    # ── AI 预鉴定建议（只写建议，不动档案本身）──
    ai_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending 未跑 | done | failed | skipped",
    )
    ai_kfzt: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="AI 建议开放状态"
    )
    ai_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="AI 建议理由"
    )
    ai_hit_words: Mapped[Optional[list]] = mapped_column(
        JSONB, nullable=True, comment="命中敏感词"
    )
    ai_standard_code: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True, comment="AI 引用标准条款编码"
    )
    ai_confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="AI 置信度"
    )

    # ── 人工结论（鉴定员核对后填，审核通过回写档案）──
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        index=True,
        comment="pending 未定 | decided 已定",
    )
    final_kfzt: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="人工结论开放状态"
    )
    final_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="结论理由"
    )
    final_standard_code: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True, comment="引用标准条款编码"
    )
    decided_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True,
        comment="结论给出人",
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
