from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
import uuid
from datetime import datetime

# ==================== TENANT ====================

class TenantBase(BaseModel):
    code: str = Field(..., max_length=50, description="租户编码")
    name: str = Field(..., max_length=100, description="租户名称")
    description: Optional[str] = Field(None, max_length=200, description="描述")
    is_active: bool = Field(True, description="是否启用")

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="租户名称")
    description: Optional[str] = Field(None, max_length=200, description="描述")
    is_active: Optional[bool] = Field(None, description="是否启用")

class Tenant(TenantBase):
    id: uuid.UUID
    create_time: datetime
    update_time: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ==================== ORGANIZATION ====================

class OrganizationBase(BaseModel):
    tenant_id: uuid.UUID = Field(..., description="所属租户ID")
    parent_id: Optional[uuid.UUID] = Field(None, description="父级组织ID")
    name: str = Field(..., max_length=100, description="组织名称")
    code: Optional[str] = Field(None, max_length=50, description="组织编码")
    sort_order: int = Field(0, description="排序号")

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    parent_id: Optional[uuid.UUID] = Field(None, description="父级组织ID")
    name: Optional[str] = Field(None, max_length=100, description="组织名称")
    code: Optional[str] = Field(None, max_length=50, description="组织编码")
    sort_order: Optional[int] = Field(None, description="排序号")

class Organization(OrganizationBase):
    id: uuid.UUID
    create_time: datetime
    update_time: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OrganizationTree(Organization):
    children: List["OrganizationTree"] = []
    
    model_config = ConfigDict(from_attributes=True)
