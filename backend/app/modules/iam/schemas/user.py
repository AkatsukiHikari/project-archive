from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
import uuid
from app.modules.iam.schemas.permission import Menu

# Role Schemas
class RoleBase(BaseModel):
    name: str = Field(..., max_length=50, description="角色展示名称", example="审计管理员")
    code: str = Field(..., max_length=50, description="角色系统编码（用于代码内的硬编码管控）", example="ROLE_AUDITOR")
    description: Optional[str] = Field(None, max_length=200, description="角色的业务描述")
    tenant_id: Optional[uuid.UUID] = Field(None, description="所属租户ID，为空表示全局级大角色")

class RoleCreate(RoleBase):
    menu_ids: Optional[List[uuid.UUID]] = Field(None, description="分配给此角色的菜单/权限节点ID集合")

class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50, description="修改后的角色展示名称")
    code: Optional[str] = Field(None, max_length=50, description="修改后的角色系统编码")
    description: Optional[str] = Field(None, max_length=200, description="修改后的业务描述")
    menu_ids: Optional[List[uuid.UUID]] = Field(None, description="重新分配的菜单/权限节点ID集合")

class Role(RoleBase):
    id: uuid.UUID = Field(..., description="角色系统唯一标识")
    is_system: bool = Field(False, description="系统内置角色，不可删除")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="最后一次更新时间")
    menus: List[Menu] = Field(default_factory=list, description="角色绑定的菜单/权限节点列表")

    model_config = ConfigDict(from_attributes=True)

# User Schemas
class UserBase(BaseModel):
    username: str = Field(..., description="登录用户名", example="admin")
    email: EmailStr = Field(..., description="用户邮箱地址", example="admin@example.com")
    full_name: Optional[str] = Field(None, description="用户真实姓名", example="系统管理员")
    is_active: bool = Field(True, description="账号是否启用")
    tenant_id: Optional[uuid.UUID] = Field(None, description="所属租户 ID")
    org_id: Optional[uuid.UUID] = Field(None, description="所属组织架构 ID")
    
    # Profile Extensions
    avatar: Optional[str] = Field(None, description="头像 URL 地址")
    phone: Optional[str] = Field(None, description="联系电话", example="13800138000")
    job_title: Optional[str] = Field(None, description="职务/头衔", example="软件工程师")
    location: Optional[str] = Field(None, description="办公地点", example="北京总部")
    bio: Optional[str] = Field(None, description="个人简介")
    last_login_time: Optional[datetime] = Field(None, description="最后登录时间")

class UserCreate(UserBase):
    password: str = Field(..., description="初始登录密码")
    role_ids: Optional[List[uuid.UUID]] = Field(None, description="分配的角色 ID 列表")

class UserUpdate(BaseModel):
    password: Optional[str] = Field(None, description="新登录密码")
    email: Optional[EmailStr] = Field(None, description="用户邮箱地址")
    full_name: Optional[str] = Field(None, description="用户真实姓名")
    is_active: Optional[bool] = Field(None, description="账号是否启用")
    tenant_id: Optional[uuid.UUID] = Field(None, description="所属租户 ID")
    org_id: Optional[uuid.UUID] = Field(None, description="所属组织架构 ID")
    role_ids: Optional[List[uuid.UUID]] = Field(None, description="重新分配的角色 ID 列表")

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = Field(None, description="用户真实姓名")
    avatar: Optional[str] = Field(None, description="头像 URL 地址")
    phone: Optional[str] = Field(None, description="联系电话")
    job_title: Optional[str] = Field(None, description="职务/头衔")
    location: Optional[str] = Field(None, description="办公地点")
    bio: Optional[str] = Field(None, description="个人简介", max_length=500)

class UserPasswordUpdate(BaseModel):
    old_password: str = Field(..., description="当前使用的旧密码（明文）", example="old123456")
    new_password: str = Field(..., min_length=6, description="希望设置的新密码（明文，建议包含字母和数字）", example="newSecure@2026")

class UserInDBBase(UserBase):
    id: uuid.UUID = Field(..., description="用户全局唯一UUID")
    create_time: datetime = Field(..., description="账号创建时间")
    update_time: datetime = Field(..., description="账号属性最后一次更新时间")

    model_config = ConfigDict(from_attributes=True)

class User(UserInDBBase):
    roles: List[Role] = []
    permissions: Optional[List[str]] = Field(None, description="用户当前具备的细粒度操作权限标识集")

class UserInDB(UserInDBBase):
    hashed_password: str
