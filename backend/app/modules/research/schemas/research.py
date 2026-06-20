"""档案编研 DTO。"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

RESULT_TYPE = "^(大事记|组织沿革|专题汇编|基础数字汇编|参考资料|全宗指南)$"


# ── 项目 ──────────────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    project_type: str = Field(pattern=RESULT_TYPE)
    editor_id: Optional[uuid.UUID] = None
    reviewer_id: Optional[uuid.UUID] = None
    members: Optional[list[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    purpose: Optional[str] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    project_type: Optional[str] = Field(default=None, pattern=RESULT_TYPE)
    editor_id: Optional[uuid.UUID] = None
    reviewer_id: Optional[uuid.UUID] = None
    members: Optional[list[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    purpose: Optional[str] = None
    status: Optional[str] = Field(default=None, pattern="^(in_progress|completed)$")


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    project_type: str
    editor_id: Optional[uuid.UUID] = None
    editor_name: Optional[str] = None
    reviewer_id: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None
    members: Optional[list[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    purpose: Optional[str] = None
    status: str
    material_count: int = 0
    result_count: int = 0
    create_time: datetime


# ── 素材 / 档案快照 ────────────────────────────────────────────────────────────


class MaterialAdd(BaseModel):
    archive_ids: list[uuid.UUID] = Field(min_length=1)


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    archive_id: uuid.UUID
    DH: Optional[str] = None
    TM: str
    RZZ: Optional[str] = None
    ND: Optional[int] = None
    WJRQ: Optional[str] = None
    QZH: Optional[str] = None


# ── 成果档案库（成果自有引用档案集）──────────────────────────────────────────────


class ResultArchiveAdd(BaseModel):
    archive_ids: Optional[list[uuid.UUID]] = None
    from_project: bool = Field(
        default=False, description="为真时把所属项目素材一并导入"
    )


class ResultArchiveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    archive_id: uuid.UUID
    DH: Optional[str] = None
    TM: str
    RZZ: Optional[str] = None
    ND: Optional[int] = None
    WJRQ: Optional[str] = None
    QZH: Optional[str] = None
    sort_order: int = 0


# ── 成果 ──────────────────────────────────────────────────────────────────────


class ResultCreate(BaseModel):
    project_id: Optional[uuid.UUID] = None
    title: str = Field(min_length=1, max_length=200)
    result_type: str = Field(pattern=RESULT_TYPE)
    summary: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[dict] = None
    template_id: Optional[uuid.UUID] = Field(
        default=None, description="从模板新建时带入模板正文"
    )


class ResultUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    result_type: Optional[str] = Field(default=None, pattern=RESULT_TYPE)
    summary: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[dict] = None


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    project_title: Optional[str] = None
    title: str
    result_type: str
    summary: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[dict] = None
    status: str
    author_id: Optional[uuid.UUID] = None
    reviewer_id: Optional[uuid.UUID] = None
    finalized_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    archive_count: int = 0
    create_time: datetime


class ResultListItem(BaseModel):
    """列表项（不含正文，减小载荷）。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: Optional[uuid.UUID] = None
    project_title: Optional[str] = None
    title: str
    result_type: str
    summary: Optional[str] = None
    status: str
    archive_count: int = 0
    create_time: datetime


# ── 模板 ──────────────────────────────────────────────────────────────────────


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    result_type: str = Field(pattern=RESULT_TYPE)
    description: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[dict] = None
    sort_order: int = 0


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    result_type: Optional[str] = Field(default=None, pattern=RESULT_TYPE)
    description: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[dict] = None
    sort_order: Optional[int] = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    result_type: str
    description: Optional[str] = None
    content: Optional[str] = None
    content_json: Optional[dict] = None
    is_builtin: bool = False
    sort_order: int = 0
    create_time: datetime


# ── AI 辅助起草 ────────────────────────────────────────────────────────────────


class AiDraftRequest(BaseModel):
    """基于成果自有档案库（或所属项目素材）让 AI 生成可插入文档的正文片段。"""

    result_id: uuid.UUID
    topic: Optional[str] = Field(default=None, description="编研主题/聚焦点（可选）")


class AiDraftResult(BaseModel):
    summary: Optional[str] = None
    content: str = Field(description="可直接插入编辑器的 HTML 片段")


# ── 文件上传 ──────────────────────────────────────────────────────────────────


class UploadResult(BaseModel):
    id: str
    url: str
    name: str
    size: int
    type: str
