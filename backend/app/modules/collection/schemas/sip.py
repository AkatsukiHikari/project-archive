import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class SIPCreate(BaseModel):
    title: str = Field(..., max_length=512)
    description: Optional[str] = None
    tenant_id: Optional[uuid.UUID] = None
    metadata_json: Optional[Dict[str, Any]] = None


class SIPUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=512)
    description: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None


class SIPReviewRequest(BaseModel):
    accept: bool
    notes: Optional[str] = None


class SIPOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    description: Optional[str] = None
    submitter_id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    status: str
    metadata_json: Optional[Dict[str, Any]] = None
    file_count: int
    notes: Optional[str] = None
    create_time: datetime
    update_time: datetime
