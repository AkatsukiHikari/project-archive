import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class ScheduleParticipantSchema(BaseModel):
    user_id: uuid.UUID
    status: str = Field(default="pending")

class ScheduleEventBase(BaseModel):
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    is_all_day: bool = False
    location: Optional[str] = None
    event_type: str = "meeting"

class ScheduleEventCreate(ScheduleEventBase):
    participant_ids: List[uuid.UUID] = []

class ScheduleEventUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    is_all_day: Optional[bool] = None
    location: Optional[str] = None
    event_type: Optional[str] = None
    participant_ids: Optional[List[uuid.UUID]] = None

class ScheduleEventResponse(ScheduleEventBase):
    id: uuid.UUID
    tenant_id: Optional[uuid.UUID] = None
    creator_id: uuid.UUID
    create_time: datetime
    update_time: datetime
    participants: List[ScheduleParticipantSchema] = []

    model_config = {
        "from_attributes": True
    }
