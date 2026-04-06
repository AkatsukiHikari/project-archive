import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class DetectionResult(BaseModel):
    is_valid: bool
    details: Dict[str, Any]
    score: float


class DetectionRequest(BaseModel):
    archive_id: uuid.UUID
    filename: str
    expected_hash: str
    algorithm: str = Field(default="sha256")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    content_text: str = Field(default="")


class DetectionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    archive_id: uuid.UUID
    filename: str
    status: str
    score: float
    details: Optional[Dict[str, Any]] = None
    checked_at: Optional[datetime] = None
    create_time: datetime

    @classmethod
    def from_orm_model(cls, record: Any) -> "DetectionRecordOut":
        return cls(
            id=record.id,
            archive_id=record.archive_id,
            filename=record.filename,
            status=record.status,
            score=record.score,
            details=record.details_json,
            checked_at=record.checked_at,
            create_time=record.create_time,
        )
