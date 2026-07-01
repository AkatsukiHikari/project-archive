import uuid
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# ── 目录 ──────────────────────────────────────────────────────────────────────

CatalogType = Literal["案卷目录", "卷内目录", "一文一件"]


class CatalogCreate(BaseModel):
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    catalog_no: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    year: Optional[int] = None
    catalog_type: CatalogType = "一文一件"
    volume_archive_id: Optional[uuid.UUID] = None


class CatalogUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    year: Optional[int] = None
    catalog_type: Optional[CatalogType] = None
    volume_archive_id: Optional[uuid.UUID] = None


class CatalogRead(BaseModel):
    id: uuid.UUID
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    catalog_no: str
    name: str
    year: Optional[int] = None
    catalog_type: str
    volume_archive_id: Optional[uuid.UUID] = None
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


# ── 档案（临时库 / 正式库通用） ───────────────────────────────────────────────

ArchiveMJ = Literal["无", "秘密", "机密", "绝密"]
ArchiveBGQX = Literal["permanent", "long", "short"]
StagingStatus = Literal["draft", "pending_review", "rejected"]
PermanentStatus = Literal[
    "archived", "active", "restricted", "pending_destroy", "destroyed"
]


class ArchiveCreate(BaseModel):
    fonds_id: uuid.UUID
    catalog_id: uuid.UUID
    category_id: uuid.UUID

    TM: str = Field(..., max_length=512)
    QZH: str = Field(..., max_length=50)
    ND: Optional[int] = None
    RZZ: Optional[str] = Field(default=None, max_length=200)
    DH: Optional[str] = Field(default=None, max_length=100)
    # MJ/BGQX 的合法取值由门类字段定义(field_schema/字典)决定，不再用 API Literal 写死
    MJ: Optional[str] = Field(default="无", max_length=50)
    BGQX: Optional[str] = Field(default="long", max_length=50)
    WJRQ: Optional[str] = None
    YS: Optional[int] = None
    ext_fields: Optional[dict[str, Any]] = None


class ArchiveUpdate(BaseModel):
    TM: Optional[str] = Field(default=None, max_length=512)
    RZZ: Optional[str] = Field(default=None, max_length=200)
    ND: Optional[int] = None
    MJ: Optional[str] = Field(default=None, max_length=50)
    BGQX: Optional[str] = Field(default=None, max_length=50)
    WJRQ: Optional[str] = None
    YS: Optional[int] = None
    DH: Optional[str] = Field(default=None, max_length=100)
    status: Optional[StagingStatus] = None
    ext_fields: Optional[dict[str, Any]] = None


class ArchiveRead(BaseModel):
    id: uuid.UUID
    fonds_id: uuid.UUID
    catalog_id: uuid.UUID
    category_id: uuid.UUID
    DH: Optional[str] = None
    QZH: str
    TM: str
    RZZ: Optional[str] = None
    ND: Optional[int] = None
    WJRQ: Optional[str] = None
    YS: Optional[int] = None
    MJ: str
    BGQX: str
    KFZT: Optional[str] = None  # 开放状态/当前访问标识（暂存库无此列 → 未鉴定）
    status: str
    ext_fields: Optional[dict[str, Any]] = None
    embedding_status: str
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class ArchiveListQuery(BaseModel):
    fonds_id: Optional[uuid.UUID] = None
    catalog_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    ND: Optional[int] = None
    keyword: Optional[str] = Field(
        default=None, description="题名/责任者/档号 综合关键字"
    )
    MJ: Optional[str] = None
    status: Optional[str] = None
    # ── 高级组合检索字段（逐字段精确/范围） ──
    TM: Optional[str] = Field(default=None, description="题名（模糊）")
    RZZ: Optional[str] = Field(default=None, description="责任者（模糊）")
    DH: Optional[str] = Field(default=None, description="档号（模糊）")
    BGQX: Optional[str] = Field(default=None, description="保管期限")
    ND_from: Optional[int] = Field(default=None, description="年度起")
    ND_to: Optional[int] = Field(default=None, description="年度止")
    WJRQ_from: Optional[str] = Field(default=None, description="文件日期起 YYYY-MM-DD")
    WJRQ_to: Optional[str] = Field(default=None, description="文件日期止 YYYY-MM-DD")
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


# ── 原文附件 ──────────────────────────────────────────────────────────────────


class AttachmentCreate(BaseModel):
    archive_id: uuid.UUID
    is_staging: bool = True
    is_primary: bool = True
    original_name: str = Field(..., max_length=512)
    storage_key: str = Field(..., max_length=1024)
    storage_bucket: str = Field(..., max_length=255)
    file_size: Optional[int] = None
    file_format: Optional[str] = Field(default=None, max_length=50)
    page_count: Optional[int] = None
    sha256_hash: Optional[str] = Field(default=None, max_length=64)
    sort_order: int = 0


class AttachmentRead(BaseModel):
    id: uuid.UUID
    archive_id: uuid.UUID
    is_staging: bool
    is_primary: bool
    original_name: str
    storage_key: str
    storage_bucket: str
    file_size: Optional[int] = None
    file_format: Optional[str] = None
    page_count: Optional[int] = None
    sha256_hash: Optional[str] = None
    sort_order: int
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}
