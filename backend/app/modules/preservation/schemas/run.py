import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class RunRequest(BaseModel):
    archive_id: uuid.UUID
    scheme_id: Optional[uuid.UUID] = None   # 空则用默认方案


class BatchRunRequest(BaseModel):
    """按 目录 / 全宗 / 门类 / 年度 批量检测（至少给一个范围条件）。"""
    scheme_id: Optional[uuid.UUID] = None
    fonds_id: Optional[uuid.UUID] = None
    catalog_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    ND: Optional[int] = None


class BatchRunResult(BaseModel):
    total: int
    passed: int = 0      # 合格
    warned: int = 0      # 基本合格
    failed: int = 0      # 不合格
    pending: int = 0     # 待复核
    scheme_name: Optional[str] = None


class ResultItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    check_code: str
    check_name: str
    dimension: str
    exec_type: str
    result: str
    score: float
    weight: int
    is_blocking: bool
    message: Optional[str] = None
    evidence: Optional[dict[str, Any]] = None
    confidence: Optional[float] = None
    standard_ref: Optional[str] = None
    decided_by: Optional[uuid.UUID] = None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    target_label: Optional[str] = None
    scheme_id: Optional[uuid.UUID] = None
    scheme_name: Optional[str] = None
    scheme_version: Optional[int] = None
    overall_score: float
    dim_scores: Optional[dict[str, Any]] = None
    conclusion: str
    status: str
    total: int
    passed: int
    warned: int
    failed: int
    manual_pending: int
    operator_id: Optional[uuid.UUID] = None
    reviewer_id: Optional[uuid.UUID] = None
    finished_at: Optional[datetime] = None
    create_time: datetime


class RunDetail(RunOut):
    results: list[ResultItemOut] = Field(default_factory=list)


class ManualDecision(BaseModel):
    result: str = Field(..., description="pass | warn | fail")
    message: Optional[str] = None


class BatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    batch_no: str
    scope_type: str
    scope_label: Optional[str] = None
    scheme_name: Optional[str] = None
    total: int
    passed: int
    warned: int
    failed: int
    pending: int
    avg_score: float
    dim_scores: Optional[dict[str, Any]] = None
    conclusion: str
    status: str
    operator_id: Optional[uuid.UUID] = None
    finished_at: Optional[datetime] = None
    create_time: datetime


class BatchDetail(BatchOut):
    runs: list[RunOut] = Field(default_factory=list)
