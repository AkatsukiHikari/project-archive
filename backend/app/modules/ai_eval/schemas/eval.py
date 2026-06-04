"""AI Eval 模块 schema（P1 仅读侧）。"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class EvalRunListItem(BaseModel):
    id: uuid.UUID
    scenario_code: str
    workflow_version: Optional[str] = None
    model_tier: Optional[str] = None
    status: str
    total: Optional[int] = None
    passed: Optional[int] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    threshold: dict[str, Any] = Field(default_factory=dict)
    blocked_upgrade: bool = False
    create_time: datetime
    update_time: datetime


class EvalRunListResponse(BaseModel):
    total: int
    items: list[EvalRunListItem]


class GoldenItem(BaseModel):
    id: uuid.UUID
    scenario_code: str
    input: dict[str, Any]
    expected: dict[str, Any]
    tags: list[str] = Field(default_factory=list)
    source: str
    note: Optional[str] = None
    create_time: datetime


class GoldenListResponse(BaseModel):
    total: int
    items: list[GoldenItem]
