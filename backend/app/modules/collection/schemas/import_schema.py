import uuid
from typing import Optional, Any
from pydantic import BaseModel, Field


# ── 上传阶段 ──────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    task_id: uuid.UUID
    columns: list[str]          # 文件中识别到的列头


# ── 字段映射 ──────────────────────────────────────────────────────────────────

class ColumnMapping(BaseModel):
    source_col: str             # 文件列头
    target_field: Optional[str] = None   # 档案字段名，None=忽略该列


class MappingPreviewRequest(BaseModel):
    task_id: uuid.UUID
    mappings: list[ColumnMapping]
    save_as_template: Optional[str] = None   # 非空则保存为模板，值为模板名


class DryRunRow(BaseModel):
    row: int
    status: str                 # ok / warning / error
    message: Optional[str] = None


class DryRunResponse(BaseModel):
    task_id: uuid.UUID
    total: int
    ok: int
    warning: int
    error: int
    sample_errors: list[DryRunRow]   # 最多返回 20 条错误样本


# ── 执行导入 ──────────────────────────────────────────────────────────────────

class ExecuteRequest(BaseModel):
    task_id: uuid.UUID


# ── 任务进度 ──────────────────────────────────────────────────────────────────

class ImportTaskRead(BaseModel):
    id: uuid.UUID
    status: str
    total: int
    success: int
    failed: int
    skipped: int
    original_filename: Optional[str]
    error_report_key: Optional[str]
    started_at: Optional[Any] = None
    finished_at: Optional[Any] = None

    model_config = {"from_attributes": True}


# ── 映射模板 ──────────────────────────────────────────────────────────────────

class MappingTemplateRead(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    mappings: Optional[list[dict]]
    is_default: bool

    model_config = {"from_attributes": True}
