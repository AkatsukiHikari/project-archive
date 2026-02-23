from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
import uuid
from datetime import datetime

# ==================== MENU / PERMISSION ====================

class MenuBase(BaseModel):
    parent_id: Optional[uuid.UUID] = Field(None, description="父级ID")
    code: str = Field(..., max_length=100, description="编码 e.g. 'system:user:add'")
    name: str = Field(..., max_length=50, description="名称")
    type: str = Field(..., max_length=20, description="类型: DIR, MENU, BUTTON")
    path: Optional[str] = Field(None, max_length=255, description="路由路径")
    icon: Optional[str] = Field(None, max_length=100, description="图标")
    sort_order: int = Field(0, description="排序号")
    is_visible: bool = Field(True, description="是否可见")

class MenuCreate(MenuBase):
    pass

class MenuUpdate(BaseModel):
    parent_id: Optional[uuid.UUID] = Field(None, description="父级ID")
    name: Optional[str] = Field(None, max_length=50, description="名称")
    code: Optional[str] = Field(None, max_length=100, description="编码")
    type: Optional[str] = Field(None, max_length=20, description="类型")
    path: Optional[str] = Field(None, max_length=255, description="路由路径")
    icon: Optional[str] = Field(None, max_length=100, description="图标")
    sort_order: Optional[int] = Field(None, description="排序号")
    is_visible: Optional[bool] = Field(None, description="是否可见")

class Menu(MenuBase):
    id: uuid.UUID
    create_time: datetime
    update_time: datetime
    
    model_config = ConfigDict(from_attributes=True)

class MenuTree(Menu):
    children: List["MenuTree"] = []
    
    model_config = ConfigDict(from_attributes=True)
