"""档案整理 DTO：批量修改 / 批量重编档号 / 挂接数字化成果 / 归档入库。"""

import uuid
from typing import Optional

from pydantic import BaseModel, Field

from app.modules.repository.schemas.archive import ArchiveListQuery

# ── 批量修改字段 ──────────────────────────────────────────────────────────────


class BatchUpdateRequest(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1)
    MJ: Optional[str] = None
    BGQX: Optional[str] = None
    RZZ: Optional[str] = None
    ND: Optional[int] = None
    WJRQ: Optional[str] = None


class BatchUpdateResult(BaseModel):
    updated: int


# ── 批量重编档号 ──────────────────────────────────────────────────────────────


class RenumberRequest(BaseModel):
    """重编范围三选一：勾选 ids ＞ 查询条件 query ＞ 目录 catalog_id。"""

    rule_id: uuid.UUID
    catalog_id: Optional[uuid.UUID] = None
    ids: Optional[list[uuid.UUID]] = None
    query: Optional["ArchiveListQuery"] = None
    start_seq: int = Field(default=1, ge=1)


class RenumberRow(BaseModel):
    id: uuid.UUID
    TM: str
    WJRQ: Optional[str] = None
    DH_old: Optional[str] = None
    DH_new: str
    conflict: bool = False


class RenumberPreview(BaseModel):
    total: int
    conflicts: int
    rows: list[RenumberRow]


class RenumberResult(BaseModel):
    renumbered: int


# ── 挂接数字化成果 ────────────────────────────────────────────────────────────


class AttachMatchRequest(BaseModel):
    filenames: list[str] = Field(min_length=1)


class AttachMatchRow(BaseModel):
    filename: str
    DH: str
    status: str  # 预检: matched | not_found | has_primary；执行: attached | skipped | not_found
    source: Optional[str] = None  # staging | formal
    archive_id: Optional[uuid.UUID] = None
    TM: Optional[str] = None
    reason: Optional[str] = None


class AttachMatchPreview(BaseModel):
    total: int
    matched: int
    not_found: int
    has_primary: int
    rows: list[AttachMatchRow]


class AttachBatchResult(BaseModel):
    batch_no: str
    attached: int
    skipped: int
    not_found: int
    rows: list[AttachMatchRow]  # status: attached | skipped | not_found


# ── 归档入库 ──────────────────────────────────────────────────────────────────


class ArchiveToFormalRequest(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1)


class ArchiveToFormalRow(BaseModel):
    id: uuid.UUID
    DH: Optional[str] = None
    TM: str
    status: str  # ok | failed
    reason: Optional[str] = None


class ArchiveToFormalResult(BaseModel):
    archived: int
    failed: int
    rows: list[ArchiveToFormalRow]
