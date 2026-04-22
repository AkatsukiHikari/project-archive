import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FondsCreate(BaseModel):
    fonds_code: str = Field(..., max_length=50, description="全宗号（全国唯一）")
    name: str = Field(..., max_length=255, description="全宗名称（机构全称）")
    short_name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    retention_period: str = Field(default="permanent", max_length=20)
    status: str = Field(default="active", max_length=20)
    custodian_id: Optional[uuid.UUID] = None


class FondsUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    short_name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    retention_period: Optional[str] = Field(default=None, max_length=20)
    status: Optional[str] = Field(default=None, max_length=20)
    custodian_id: Optional[uuid.UUID] = None


class FondsRead(BaseModel):
    id: uuid.UUID
    fonds_code: str
    name: str
    short_name: Optional[str] = None
    description: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    retention_period: str
    status: str
    custodian_id: Optional[uuid.UUID] = None
    tenant_id: Optional[uuid.UUID] = None
    create_time: Optional[datetime] = None

    model_config = {"from_attributes": True}
