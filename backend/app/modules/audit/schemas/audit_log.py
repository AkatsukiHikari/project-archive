from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
import uuid
from datetime import datetime

class AuditLogBase(BaseModel):
    user_id: Optional[uuid.UUID] = Field(None, description="操作用户ID")
    tenant_id: Optional[uuid.UUID] = Field(None, description="所属租户ID")
    action: str = Field(..., max_length=100, description="操作动作")
    module: str = Field(..., max_length=50, description="功能模块")
    ip_address: Optional[str] = Field(None, max_length=50, description="IP地址")
    user_agent: Optional[str] = Field(None, max_length=255, description="用户代理解析")
    status: str = Field("SUCCESS", max_length=20, description="状态")
    details: Optional[Dict[str, Any]] = Field(None, description="结构化详情")
    error_message: Optional[str] = Field(None, max_length=500, description="错误信息")

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: uuid.UUID
    create_time: datetime
    update_time: datetime
    
    model_config = ConfigDict(from_attributes=True)
