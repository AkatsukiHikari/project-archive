import uuid
from typing import Optional, Literal, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class SegmentDef(BaseModel):
    """规则段定义"""
    type: Literal["field", "literal", "sequence", "date_part"]

    # type=field: 取档案 DA/T 规范化字段（拼音缩写，MLH/AJH/JH 已删除）
    field: Optional[str] = None        # QZH | ND | RZZ

    # type=literal: 固定字符串
    value: Optional[str] = None

    # type=sequence: 自增序号
    padding: int = 4                   # 补零位数，如 4 → "0023"
    scope: Literal["catalog", "catalog_year", "fonds"] = "catalog_year"

    # type=date_part: 从 WJRQ 提取日期部分
    date_field: str = "WJRQ"          # 来源字段（默认文件日期）
    date_format: str = "%Y"            # strftime 格式，如 "%Y%m%d"

    @model_validator(mode="after")
    def check_type_fields(self) -> "SegmentDef":
        if self.type == "field" and not self.field:
            raise ValueError("field segment requires 'field' to be set")
        if self.type == "literal" and self.value is None:
            raise ValueError("literal segment requires 'value' to be set")
        return self


class RuleTemplate(BaseModel):
    """档号规则模板"""
    separator: str = Field(default="-", max_length=5, description="段分隔符")
    segments: list[SegmentDef] = Field(..., min_length=1)


class NoRuleCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(..., max_length=100)
    rule_template: dict[str, Any]      # 存为 JSONB，通过 RuleTemplate 验证结构
    seq_scope: Literal["catalog", "catalog_year", "fonds"] = "catalog_year"
    is_active: bool = True

    @field_validator("rule_template", mode="before")
    @classmethod
    def validate_rule_template(cls, v: Any) -> Any:
        RuleTemplate.model_validate(v)  # raises ValidationError on bad input
        return v


class NoRuleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=100)
    rule_template: Optional[dict[str, Any]] = None
    seq_scope: Optional[Literal["catalog", "catalog_year", "fonds"]] = None
    is_active: Optional[bool] = None

    @field_validator("rule_template", mode="before")
    @classmethod
    def validate_rule_template(cls, v: Any) -> Any:
        if v is not None:
            RuleTemplate.model_validate(v)
        return v


class NoRuleRead(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    rule_template: Optional[dict[str, Any]]
    seq_scope: Literal["catalog", "catalog_year", "fonds"]
    is_active: bool
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class PreviewRequest(BaseModel):
    """预览档号时提供的档案字段样本（拼音缩写，MLH/AJH/JH 已删除）"""
    QZH: str = Field(default="J001", max_length=50)
    ND: Optional[int] = Field(default=2024)
    RZZ: Optional[str] = None
    WJRQ: Optional[str] = Field(default="2024-01-01", description="YYYY-MM-DD")


class PreviewResponse(BaseModel):
    DH: str
    segments: list[str]              # 各段生成值，便于前端展示
