"""数据字典 Pydantic schemas。"""
import uuid
from typing import Optional
from pydantic import BaseModel, Field


# ─── 字典项 ───────────────────────────────────────────────────────────────────

class DictItemCreate(BaseModel):
    item_value: str = Field(..., max_length=200, description="存储值")
    item_label: str = Field(..., max_length=200, description="显示标签")
    is_default: bool = False
    sort_order: int = 0
    description: Optional[str] = None


class DictItemUpdate(BaseModel):
    item_value: Optional[str] = Field(default=None, max_length=200)
    item_label: Optional[str] = Field(default=None, max_length=200)
    is_default: Optional[bool] = None
    sort_order: Optional[int] = None
    description: Optional[str] = None


class DictItemRead(BaseModel):
    id: uuid.UUID
    dict_type: str
    item_value: str
    item_label: str
    is_default: bool
    sort_order: int
    description: Optional[str] = None

    model_config = {"from_attributes": True}


# ─── 字典类型 ──────────────────────────────────────────────────────────────────

class DictCreate(BaseModel):
    dict_type: str = Field(..., max_length=64, description="字典代码，全局唯一")
    dict_name: str = Field(..., max_length=100, description="字典中文名")
    description: Optional[str] = None
    sort_order: int = 0


class DictUpdate(BaseModel):
    dict_name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    sort_order: Optional[int] = None


class DictRead(BaseModel):
    id: uuid.UUID
    dict_type: str
    dict_name: str
    description: Optional[str] = None
    is_builtin: bool
    sort_order: int
    items: list[DictItemRead] = []

    model_config = {"from_attributes": True}


class DictReadSimple(BaseModel):
    """不含 items 的轻量版，用于列表接口。"""
    id: uuid.UUID
    dict_type: str
    dict_name: str
    description: Optional[str] = None
    is_builtin: bool
    sort_order: int
    item_count: int = 0

    model_config = {"from_attributes": True}
