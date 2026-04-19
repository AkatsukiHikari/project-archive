import uuid
from typing import Optional, Any, Literal
from pydantic import BaseModel, Field


# ── 目录 ──────────────────────────────────────────────────────────────────────

class CatalogCreate(BaseModel):
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    catalog_no: str = Field(..., max_length=50)
    name: str = Field(..., max_length=255)
    year: Optional[int] = None
    org_mode: Literal["by_item", "by_volume"] = "by_item"


class CatalogUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)
    year: Optional[int] = None
    org_mode: Optional[Literal["by_item", "by_volume"]] = None


class CatalogRead(BaseModel):
    id: uuid.UUID
    fonds_id: uuid.UUID
    category_id: uuid.UUID
    catalog_no: str
    name: str
    year: Optional[int] = None
    org_mode: str
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


# ── 档案 ──────────────────────────────────────────────────────────────────────

class ArchiveCreate(BaseModel):
    fonds_id: uuid.UUID
    catalog_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    category_id: uuid.UUID
    level: Literal["volume", "item"] = "item"

    # DA/T 必有项
    title: str = Field(..., max_length=512, description="题名（必填）")
    fonds_code: str = Field(..., max_length=50)
    year: Optional[int] = None
    creator: Optional[str] = Field(default=None, max_length=200)
    catalog_no: Optional[str] = Field(default=None, max_length=50)
    volume_no: Optional[str] = Field(default=None, max_length=50)
    item_no: Optional[str] = Field(default=None, max_length=50)
    archive_no: Optional[str] = Field(default=None, max_length=100)
    security_level: Literal["public", "internal", "confidential", "secret"] = "public"
    retention_period: Literal["permanent", "long", "short"] = "permanent"
    doc_date: Optional[str] = None
    pages: Optional[int] = None

    # 门类私有字段
    ext_fields: Optional[dict[str, Any]] = None

    # 存储（可选，归档后再填）
    storage_key: Optional[str] = None
    storage_bucket: Optional[str] = None
    file_size: Optional[int] = None
    file_format: Optional[str] = None
    sha256_hash: Optional[str] = None


class ArchiveUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=512)
    creator: Optional[str] = Field(default=None, max_length=200)
    year: Optional[int] = None
    security_level: Optional[Literal["public", "internal", "confidential", "secret"]] = None
    retention_period: Optional[Literal["permanent", "long", "short"]] = None
    doc_date: Optional[str] = None
    pages: Optional[int] = None
    status: Optional[Literal["active", "restricted", "destroyed"]] = None
    ext_fields: Optional[dict[str, Any]] = None
    archive_no: Optional[str] = Field(default=None, max_length=100)


class ArchiveRead(BaseModel):
    id: uuid.UUID
    fonds_id: uuid.UUID
    catalog_id: uuid.UUID
    parent_id: Optional[uuid.UUID] = None
    category_id: uuid.UUID
    level: str
    archive_no: Optional[str] = None
    fonds_code: str
    catalog_no: Optional[str] = None
    volume_no: Optional[str] = None
    item_no: Optional[str] = None
    year: Optional[int] = None
    title: str
    creator: Optional[str] = None
    security_level: str
    retention_period: str
    doc_date: Optional[str] = None
    pages: Optional[int] = None
    status: str
    ext_fields: Optional[dict[str, Any]] = None
    file_format: Optional[str] = None
    file_size: Optional[int] = None
    embedding_status: str
    tenant_id: Optional[uuid.UUID] = None

    model_config = {"from_attributes": True}


class ArchiveListQuery(BaseModel):
    """档案列表查询参数"""
    fonds_id: Optional[uuid.UUID] = None
    catalog_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    year: Optional[int] = None
    keyword: Optional[str] = Field(default=None, description="题名/责任者关键字")
    security_level: Optional[str] = None
    status: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
