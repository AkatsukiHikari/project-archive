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
    default_value: Optional[Any] = Field(
        default=None,
        description="默认值；$currentYear=当前年度、$currentUser=当前用户名",
    )
    sort_order: int = Field(default=0, description="字段显示顺序（升序）")
    inherited: bool = Field(default=False, description="从父门类继承，不可删除")


# ── 表单排版 Layout ────────────────────────────────────────────────────────────

class FormLayoutCell(BaseModel):
    """排版单元格：指向一个字段，span 1=半行 2=整行"""
    field: str = Field(..., description="FieldDefinition.name")
    span: int = Field(default=1, ge=1, le=2)


class FormLayoutRow(BaseModel):
    """排版行，包含 1~2 个单元格"""
    id: str = Field(..., description="唯一行 ID（前端生成）")
    cells: list[FormLayoutCell]


class FormLayout(BaseModel):
    """表单排版定义，存入 repo_archive_category.form_layout"""
    cols: int = Field(default=2, description="表单总列数（当前固定 2）")
    rows: list[FormLayoutRow] = []


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
    form_layout: Optional[FormLayout] = None


class CategoryRead(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    parent_id: Optional[uuid.UUID] = None
    base_category_id: Optional[uuid.UUID] = None
    is_builtin: bool
    requires_privacy_guard: bool
    field_schema: Optional[list[FieldDefinition]] = None
    form_layout: Optional[FormLayout] = None
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}
