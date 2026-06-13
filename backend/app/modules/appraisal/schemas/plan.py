"""鉴定计划 / 任务 / 明细 DTO。"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

KFZT_PATTERN = "^(开放|控制使用|延期开放|不开放)$"


# ── 到期圈定预览 ──────────────────────────────────────────────────────────────


class ScopeFondsGroup(BaseModel):
    """一个全宗下的到期待鉴定档案统计。"""

    fonds_id: uuid.UUID
    QZH: str
    fonds_name: Optional[str] = None
    due_count: int


class ScopePreviewOut(BaseModel):
    total: int
    groups: list[ScopeFondsGroup]


# ── 计划 ──────────────────────────────────────────────────────────────────────


class PlanTaskAssign(BaseModel):
    """创建计划时的任务分配：一个全宗 → 一个鉴定员。"""

    fonds_id: uuid.UUID
    assignee_id: uuid.UUID


class PlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    reviewer_id: uuid.UUID
    description: Optional[str] = None
    tasks: list[PlanTaskAssign] = Field(min_length=1)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    fonds_id: uuid.UUID
    QZH: str
    fonds_name: Optional[str] = None
    assignee_id: uuid.UUID
    assignee_name: Optional[str] = None
    status: str
    total: int
    decided: int = 0
    reject_reason: Optional[str] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    create_time: datetime
    # 任务列表上下文（计划名/审核人，由 service 填充）
    plan_name: Optional[str] = None
    plan_no: Optional[str] = None


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_no: str
    name: str
    appraisal_type: str
    leader_id: Optional[uuid.UUID] = None
    leader_name: Optional[str] = None
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None
    status: str
    description: Optional[str] = None
    total_tasks: int
    total_archives: int
    finished_at: Optional[datetime] = None
    create_time: datetime


class PlanDetail(PlanOut):
    tasks: list[TaskOut] = []


# ── 明细 ──────────────────────────────────────────────────────────────────────


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    archive_id: uuid.UUID
    ND: Optional[int] = None
    DH: Optional[str] = None
    TM: str
    QZH: Optional[str] = None
    MJ: Optional[str] = None
    BGQX: Optional[str] = None
    due_basis: Optional[str] = None
    ai_status: str
    ai_kfzt: Optional[str] = None
    ai_reason: Optional[str] = None
    ai_hit_words: Optional[list] = None
    ai_standard_code: Optional[str] = None
    ai_confidence: Optional[float] = None
    status: str
    final_kfzt: Optional[str] = None
    final_reason: Optional[str] = None
    final_standard_code: Optional[str] = None
    decided_at: Optional[datetime] = None


class ItemPage(BaseModel):
    total: int
    items: list[ItemOut]


class ItemDecide(BaseModel):
    """鉴定员给单条明细下结论。"""

    final_kfzt: str = Field(pattern=KFZT_PATTERN)
    final_reason: Optional[str] = None
    final_standard_code: Optional[str] = Field(default=None, max_length=40)


class TaskReject(BaseModel):
    reason: str = Field(min_length=1)


class TaskDetail(TaskOut):
    """任务详情（含明细统计）。"""

    ai_done: int = 0
    pending: int = 0


# ── 台账 ──────────────────────────────────────────────────────────────────────


class LedgerEntry(ItemOut):
    plan_name: Optional[str] = None
    plan_no: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class LedgerPage(BaseModel):
    total: int
    items: list[LedgerEntry]
