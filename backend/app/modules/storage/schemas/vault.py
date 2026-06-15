"""档案保管 DTO。"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# ── 库房 ──────────────────────────────────────────────────────────────────────


class VaultCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=100)
    location: Optional[str] = None
    area_sqm: Optional[float] = None
    rows: int = Field(default=4, ge=1, le=20)
    columns: int = Field(default=6, ge=1, le=30)
    layers: int = Field(default=5, ge=1, le=12)
    capacity: int = Field(default=0, ge=0)
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    status: str = "active"
    notes: Optional[str] = None


class VaultUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    location: Optional[str] = None
    area_sqm: Optional[float] = None
    rows: Optional[int] = Field(default=None, ge=1, le=20)
    columns: Optional[int] = Field(default=None, ge=1, le=30)
    layers: Optional[int] = Field(default=None, ge=1, le=12)
    capacity: Optional[int] = Field(default=None, ge=0)
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class ShelfOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    row_index: int
    col_index: int
    capacity: int
    used: int
    label: Optional[str] = None


class VaultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    location: Optional[str] = None
    area_sqm: Optional[float] = None
    rows: int
    columns: int
    layers: int
    capacity: int
    used: int
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    status: str
    manager_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    fill_rate: float = 0.0


class VaultDetail(VaultOut):
    shelves: list[ShelfOut] = []


# ── 出入库 ────────────────────────────────────────────────────────────────────


class InoutCreate(BaseModel):
    direction: str = Field(pattern="^(out|in)$")
    biz_type: str = Field(pattern="^(borrow|repair|digitize|relocate|inventory|other)$")
    archive_id: Optional[uuid.UUID] = None
    DH: Optional[str] = None
    TM: Optional[str] = None
    qty: int = Field(default=1, ge=1)
    vault_id: Optional[uuid.UUID] = None
    counterparty: Optional[str] = None
    expected_return: Optional[datetime] = None
    notes: Optional[str] = None


class InoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    record_no: str
    direction: str
    biz_type: str
    archive_id: Optional[uuid.UUID] = None
    DH: Optional[str] = None
    TM: Optional[str] = None
    qty: int
    vault_id: Optional[uuid.UUID] = None
    counterparty: Optional[str] = None
    related_app_id: Optional[uuid.UUID] = None
    status: str
    out_time: Optional[datetime] = None
    expected_return: Optional[datetime] = None
    in_time: Optional[datetime] = None
    operator_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    create_time: datetime


class InoutPage(BaseModel):
    total: int
    items: list[InoutOut]
