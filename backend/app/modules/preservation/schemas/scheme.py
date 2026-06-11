import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class CheckItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    dimension: str
    exec_type: str
    standard_ref: Optional[str] = None
    description: Optional[str] = None
    carrier_type: str
    default_weight: int
    default_blocking: bool
    enabled: bool


class SchemeItemIn(BaseModel):
    check_code: str
    enabled: bool = True
    weight: Optional[int] = None
    is_blocking: Optional[bool] = None
    params: Optional[dict[str, Any]] = None
    sort_order: int = 0


class SchemeItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    check_code: str
    check_name: Optional[str] = None
    dimension: Optional[str] = None
    exec_type: Optional[str] = None
    standard_ref: Optional[str] = None
    enabled: bool
    weight: int
    is_blocking: bool
    params: Optional[dict[str, Any]] = None
    sort_order: int


class SchemeCreate(BaseModel):
    name: str = Field(..., max_length=200)
    description: Optional[str] = None
    carrier_type: str = "electronic"
    is_default: bool = False
    items: list[SchemeItemIn] = Field(default_factory=list)


class SchemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    items: Optional[list[SchemeItemIn]] = None


class SchemeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: Optional[str] = None
    carrier_type: str
    is_default: bool
    version: int
    status: str
    create_time: datetime
    item_count: int = 0


class SchemeDetail(SchemeOut):
    items: list[SchemeItemOut] = Field(default_factory=list)
