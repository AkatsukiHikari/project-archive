import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── 归档计划 ──────────────────────────────────────────────────────────────────

class TransferPlanCreate(BaseModel):
    year: int = Field(..., ge=1900, le=2100)
    source_unit: str = Field(..., max_length=200)
    source_org_id: Optional[uuid.UUID] = None
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    planned_count: int = Field(0, ge=0)
    due_date: Optional[date] = None
    notes: Optional[str] = None


class TransferPlanUpdate(BaseModel):
    planned_count: Optional[int] = Field(None, ge=0)
    due_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class TransferPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    year: int
    source_unit: str
    source_org_id: Optional[uuid.UUID] = None
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    planned_count: int
    due_date: Optional[date] = None
    status: str
    notes: Optional[str] = None
    create_time: datetime


# ── 移交明细 ──────────────────────────────────────────────────────────────────

class TransferEntryIn(BaseModel):
    TM: str = Field(..., max_length=512)
    RZZ: Optional[str] = None
    ND: Optional[int] = None
    WJRQ: Optional[str] = None
    YS: Optional[int] = None
    MJ: Optional[str] = None
    BGQX: Optional[str] = None
    ext_fields: Optional[dict[str, Any]] = None


class TransferEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    row_no: int
    TM: str
    RZZ: Optional[str] = None
    ND: Optional[int] = None
    WJRQ: Optional[str] = None
    YS: Optional[int] = None
    MJ: Optional[str] = None
    BGQX: Optional[str] = None
    ext_fields: Optional[dict[str, Any]] = None
    precheck_status: str
    precheck_issues: Optional[Any] = None
    staging_id: Optional[uuid.UUID] = None


# ── 移交单 ────────────────────────────────────────────────────────────────────

class TransferBatchCreate(BaseModel):
    source_unit: str = Field(..., max_length=200)
    source_org_id: Optional[uuid.UUID] = None
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    catalog_id: Optional[uuid.UUID] = None
    year: int = Field(..., ge=1900, le=2100)
    handover_person: str = Field(..., max_length=100)
    handover_date: Optional[date] = None
    plan_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    entries: list[TransferEntryIn] = Field(default_factory=list)


class TransferEntriesReplace(BaseModel):
    entries: list[TransferEntryIn]


class TransferBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    transfer_no: str
    plan_id: Optional[uuid.UUID] = None
    source_unit: str
    source_org_id: Optional[uuid.UUID] = None
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    catalog_id: Optional[uuid.UUID] = None
    year: int
    handover_person: str
    handover_date: Optional[date] = None
    expected_count: int
    status: str
    submitted_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    handler_id: Optional[uuid.UUID] = None
    precheck_score: Optional[float] = None
    precheck_passed: Optional[bool] = None
    precheck_detail: Optional[Any] = None
    return_reason: Optional[str] = None
    notes: Optional[str] = None
    create_time: datetime


class TransferBatchDetail(TransferBatchOut):
    entries: list[TransferEntryOut] = Field(default_factory=list)


# ── 接收动作 ──────────────────────────────────────────────────────────────────

class ReceiveAcceptRequest(BaseModel):
    catalog_id: Optional[uuid.UUID] = None   # 接收时可指定/覆盖目标目录
    force: bool = False                       # 预检未通过时是否强制接收（需权限）


class ReceiveReturnRequest(BaseModel):
    return_reason: str = Field(..., min_length=1)


class PrecheckResponse(BaseModel):
    score: float
    passed: bool
    threshold: float
    total: int
    ok: int
    warning: int
    error: int
    dimensions: list[dict[str, Any]]
    entries: list[dict[str, Any]]


# ── 收集台账 / 催交看板 ───────────────────────────────────────────────────────

class LedgerRow(BaseModel):
    year: int
    source_unit: str
    fonds_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    planned_count: int          # 应交
    accepted_count: int         # 已接收（件）
    submitted_count: int        # 已提交未接收（件）
    batch_total: int            # 移交单数
    completion_rate: float      # 完成率 %
    overdue: bool               # 是否逾期欠交
    due_date: Optional[date] = None


class LedgerSummary(BaseModel):
    year: Optional[int] = None
    total_planned: int
    total_accepted: int
    total_submitted: int
    overall_completion_rate: float
    overdue_units: int
    rows: list[LedgerRow]
