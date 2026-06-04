"""AI Patch 相关 schema（P1 仅暴露读取/查询，写入留 P3）。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


PatchStatus = Literal["pending", "approved", "rejected", "applied", "failed"]
PatchGate = Literal["auto", "review", "manual"]


class PatchListItem(BaseModel):
    id: uuid.UUID
    scenario_code: str
    target_type: str
    target_id: Optional[uuid.UUID] = None
    operation: str
    status: PatchStatus
    gate: PatchGate
    confidence: Optional[float] = None
    workflow_version: Optional[str] = None
    reviewer_id: Optional[uuid.UUID] = None
    create_time: datetime
    update_time: datetime


class PatchDetail(PatchListItem):
    payload: dict[str, Any]
    citations: list[dict[str, Any]] = Field(default_factory=list)
    reviewer_note: Optional[str] = None
    apply_error: Optional[str] = None


class PatchListResponse(BaseModel):
    total: int
    items: list[PatchListItem]


class PatchReviewAction(BaseModel):
    """审核操作（P3 实装；P1 接口存在但拒绝执行，返回 6003）。"""

    action: Literal["approve", "reject"]
    note: Optional[str] = Field(default=None, max_length=1000)
