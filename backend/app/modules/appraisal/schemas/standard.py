"""鉴定标准 / 敏感词 DTO。"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# ── 标准条款 ──────────────────────────────────────────────────────────────────


class StandardCreate(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    target_kfzt: str = Field(pattern="^(开放|控制使用|延期开放|不开放)$")
    keywords: Optional[list[str]] = None
    source: Optional[str] = Field(default=None, max_length=200)
    is_enabled: bool = True
    sort_order: int = 0


class StandardUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    content: Optional[str] = Field(default=None, min_length=1)
    target_kfzt: Optional[str] = Field(
        default=None, pattern="^(开放|控制使用|延期开放|不开放)$"
    )
    keywords: Optional[list[str]] = None
    source: Optional[str] = Field(default=None, max_length=200)
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class StandardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    content: str
    target_kfzt: str
    keywords: Optional[list[str]] = None
    source: Optional[str] = None
    is_enabled: bool
    sort_order: int
    create_time: datetime


# ── 敏感词 ────────────────────────────────────────────────────────────────────


class SensitiveWordCreate(BaseModel):
    word: str = Field(min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=50)
    suggest_kfzt: str = Field(
        default="控制使用", pattern="^(控制使用|延期开放|不开放)$"
    )
    is_enabled: bool = True


class SensitiveWordUpdate(BaseModel):
    word: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=50)
    suggest_kfzt: Optional[str] = Field(
        default=None, pattern="^(控制使用|延期开放|不开放)$"
    )
    is_enabled: Optional[bool] = None


class SensitiveWordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    word: str
    category: Optional[str] = None
    suggest_kfzt: str
    is_enabled: bool
    create_time: datetime
