from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
import uuid
from datetime import datetime

# ==================== TENANT ====================

class TenantBase(BaseModel):
    code: str = Field(..., max_length=50, description="租户唯一系统编码（如 company_a）", example="tenant_001")
    name: str = Field(..., max_length=100, description="租户展示名称", example="演示企业租户")
    description: Optional[str] = Field(None, max_length=200, description="租户业务描述信息")
    is_active: bool = Field(True, description="租户是否处于激活与可登录状态")

class TenantCreate(TenantBase):
    pass

class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100, description="租户的新展示名称")
    description: Optional[str] = Field(None, max_length=200, description="租户的补充描述")
    is_active: Optional[bool] = Field(None, description="是否挂起或激活该租户")

class Tenant(TenantBase):
    id: uuid.UUID = Field(..., description="租户系统级全局唯一标识符 (UUID)")
    create_time: datetime = Field(..., description="租户创建时间")
    update_time: datetime = Field(..., description="租户资料最后一次更新时间")
    
    model_config = ConfigDict(from_attributes=True)


# ==================== ORGANIZATION ====================

class OrganizationBase(BaseModel):
    tenant_id: uuid.UUID = Field(..., description="所属租户ID，隔离不同租户的数据", example="123e4567-e89b-12d3-a456-426614174000")
    parent_id: Optional[uuid.UUID] = Field(None, description="上级组织节点ID，若为顶级则为 Null", example=None)
    name: str = Field(..., max_length=100, description="组织架构节点名称，如 '研发部'", example="研发部")
    code: Optional[str] = Field(None, max_length=50, description="组织机构外部溯源编码", example="ORG_RD_01")
    sort_order: int = Field(0, description="同级树节点的排序权重（数字越小越靠前）", example=1)

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    parent_id: Optional[uuid.UUID] = Field(None, description="挂载到的新上级组织节点ID")
    name: Optional[str] = Field(None, max_length=100, description="组织的新名称")
    code: Optional[str] = Field(None, max_length=50, description="组织的自定义编码")
    sort_order: Optional[int] = Field(None, description="新的同级排序号")

class Organization(OrganizationBase):
    id: uuid.UUID
    create_time: datetime
    update_time: datetime
    
    model_config = ConfigDict(from_attributes=True)

class OrganizationTree(Organization):
    children: List["OrganizationTree"] = []
    
    model_config = ConfigDict(from_attributes=True)
