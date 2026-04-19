import uuid
from typing import Optional, Any
from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    """单个字段的 schema 定义（表单设计器产出）"""
    name: str = Field(..., description="字段 key，存入 ext_fields")
    label: str = Field(..., description="显示标签")
    type: str = Field(..., description="text | number | date | select | boolean | textarea")
    required: bool = False
    placeholder: Optional[str] = None
    validation: Optional[dict[str, Any]] = None
    options: Optional[list[str]] = None
    inherited: bool = Field(default=False, description="从父门类继承，不可删除")


class CategoryCreate(BaseModel):
    code: str = Field(..., max_length=20, description="门类代码")
    name: str = Field(..., max_length=100)
    parent_id: Optional[uuid.UUID] = None
    base_category_id: Optional[uuid.UUID] = Field(
        default=None, description="克隆来源门类 ID"
    )
    requires_privacy_guard: bool = False
    field_schema: Optional[list[FieldDefinition]] = None
    is_builtin: bool = False


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    requires_privacy_guard: Optional[bool] = None
    field_schema: Optional[list[FieldDefinition]] = None


class CategoryRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    parent_id: Optional[uuid.UUID] = None
    base_category_id: Optional[uuid.UUID] = None
    is_builtin: bool
    requires_privacy_guard: bool
    field_schema: Optional[list[FieldDefinition]] = None
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}
