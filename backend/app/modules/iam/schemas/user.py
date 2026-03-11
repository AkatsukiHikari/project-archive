from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
import uuid

# Role Schemas
class RoleBase(BaseModel):
    name: str = Field(..., max_length=50, description="角色名称")
    code: str = Field(..., max_length=50, description="角色编码")
    description: Optional[str] = Field(None, max_length=200, description="描述")
    tenant_id: Optional[uuid.UUID] = Field(None, description="所属租户ID")

class RoleCreate(RoleBase):
    menu_ids: Optional[List[uuid.UUID]] = Field(None, description="分配的菜单/权限ID列表")

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description="角色名称")
    code: Optional[str] = Field(None, max_length=50, description="角色编码")
    description: Optional[str] = Field(None, max_length=200, description="描述")
    menu_ids: Optional[List[uuid.UUID]] = Field(None, description="分配的菜单/权限ID列表")

class Role(RoleBase):
    id: uuid.UUID
    create_time: datetime
    update_time: datetime
    
    model_config = ConfigDict(from_attributes=True)

# User Schemas
class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True
    tenant_id: Optional[uuid.UUID] = None
    org_id: Optional[uuid.UUID] = None
    
    # Profile Extensions
    avatar: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    last_login_time: Optional[datetime] = None

class UserCreate(UserBase):
    password: str
    role_ids: Optional[List[uuid.UUID]] = None

class UserUpdate(BaseModel):
    password: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    tenant_id: Optional[uuid.UUID] = None
    org_id: Optional[uuid.UUID] = None
    role_ids: Optional[List[uuid.UUID]] = None

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    avatar: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None

class UserPasswordUpdate(BaseModel):
    old_password: str
    new_password: str

class UserInDBBase(UserBase):
    id: uuid.UUID
    create_time: datetime
    update_time: datetime

    model_config = ConfigDict(from_attributes=True)

class User(UserInDBBase):
    roles: List[Role] = []

class UserInDB(UserInDBBase):
    hashed_password: str
