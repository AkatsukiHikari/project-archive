from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
import uuid
from datetime import datetime

# ==================== MENU / PERMISSION ====================

class MenuBase(BaseModel):
    parent_id: Optional[uuid.UUID] = Field(None, description="上级菜单/权限节点的ID，顶级则为空")
    code: str = Field(..., max_length=100, description="前端代码或后端鉴权中使用的权限标识 (e.g. 'system:user:add')", example="system:user:add")
    name: str = Field(..., max_length=50, description="菜单或按钮的展示名称", example="新增用户")
    type: str = Field(..., max_length=20, description="节点类型: DIR(目录), MENU(菜单), BUTTON(按钮权限)", example="BUTTON")
    path: Optional[str] = Field(None, max_length=255, description="前端路由路径，仅 DIR/MENU 需要")
    icon: Optional[str] = Field(None, max_length=100, description="菜单图标标识（如 Lucide/Heroicon name）")
    sort_order: int = Field(0, description="同级展示排序号")
    is_visible: bool = Field(True, description="是否在侧边栏渲染可见（某些隐式路由可设为 False）")

class MenuCreate(MenuBase):
    pass

class MenuUpdate(BaseModel):
    parent_id: Optional[uuid.UUID] = Field(None, description="挂载到的新上级节点ID")
    name: Optional[str] = Field(None, max_length=50, description="新展示名称")
    code: Optional[str] = Field(None, max_length=100, description="新权限标识码")
    type: Optional[str] = Field(None, max_length=20, description="节点类型: DIR, MENU, BUTTON")
    path: Optional[str] = Field(None, max_length=255, description="前端路由路径")
    icon: Optional[str] = Field(None, max_length=100, description="图标标识")
    sort_order: Optional[int] = Field(None, description="排序号")
    is_visible: Optional[bool] = Field(None, description="是否可见")

class Menu(MenuBase):
    id: uuid.UUID = Field(..., description="权限菜单唯一系统标识")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="最近修改时间")
    
    model_config = ConfigDict(from_attributes=True)

class MenuTree(Menu):
    children: List["MenuTree"] = []
    
    model_config = ConfigDict(from_attributes=True)
