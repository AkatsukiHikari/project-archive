"""
档案库 Pydantic Schema（请求/响应 DTO）
"""

import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


# ─── Fonds（全宗）────────────────────────────────────────────────────────────

class FondsCreate(BaseModel):
    fonds_code: str = Field(..., max_length=50, description="全宗号")
    name: str = Field(..., max_length=255, description="全宗名称")
    short_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    retention_period: str = Field("permanent", description="保管期限: permanent/long/short")
    tenant_id: Optional[uuid.UUID] = None
    custodian_id: Optional[uuid.UUID] = None
    metadata_json: Optional[dict] = None


class FondsUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    short_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    retention_period: Optional[str] = None
    status: Optional[str] = None
    custodian_id: Optional[uuid.UUID] = None
    metadata_json: Optional[dict] = None


class FondsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fonds_code: str
    name: str
    short_name: Optional[str]
    description: Optional[str]
    start_year: Optional[int]
    end_year: Optional[int]
    retention_period: str
    status: str
    tenant_id: Optional[uuid.UUID]
    custodian_id: Optional[uuid.UUID]
    metadata_json: Optional[dict]
    create_time: datetime
    update_time: datetime

    # 统计（按需填充）
    archive_file_count: Optional[int] = None


# ─── ArchiveFile（案卷）──────────────────────────────────────────────────────

class ArchiveFileCreate(BaseModel):
    fonds_id: uuid.UUID = Field(..., description="所属全宗 ID")
    file_number: str = Field(..., max_length=100, description="案卷号")
    title: str = Field(..., max_length=512, description="案卷题名")
    year: Optional[int] = None
    classification: Optional[str] = Field(None, max_length=100)
    retention_period: str = Field("permanent")
    security_level: str = Field("public")
    tenant_id: Optional[uuid.UUID] = None
    source_sip_id: Optional[uuid.UUID] = None
    metadata_json: Optional[dict] = None
    notes: Optional[str] = None


class ArchiveFileUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=512)
    year: Optional[int] = None
    classification: Optional[str] = None
    retention_period: Optional[str] = None
    security_level: Optional[str] = None
    status: Optional[str] = None
    metadata_json: Optional[dict] = None
    notes: Optional[str] = None


class ArchiveFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    fonds_id: uuid.UUID
    file_number: str
    title: str
    year: Optional[int]
    classification: Optional[str]
    retention_period: str
    security_level: str
    item_count: int
    status: str
    source_sip_id: Optional[uuid.UUID]
    tenant_id: Optional[uuid.UUID]
    metadata_json: Optional[dict]
    notes: Optional[str]
    create_time: datetime
    update_time: datetime


# ─── ArchiveItem（文件条目）──────────────────────────────────────────────────

class ArchiveItemCreate(BaseModel):
    archive_file_id: uuid.UUID = Field(..., description="所属案卷 ID")
    item_number: str = Field(..., max_length=100)
    title: str = Field(..., max_length=512)
    item_type: str = Field("document")
    author: Optional[str] = Field(None, max_length=200)
    document_date: Optional[str] = None
    pages: Optional[int] = None
    security_level: str = Field("public")
    storage_key: Optional[str] = None
    storage_bucket: Optional[str] = None
    file_size: Optional[int] = None
    file_format: Optional[str] = None
    sha256_hash: Optional[str] = None
    tenant_id: Optional[uuid.UUID] = None
    metadata_json: Optional[dict] = None


class ArchiveItemUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=512)
    author: Optional[str] = None
    document_date: Optional[str] = None
    pages: Optional[int] = None
    security_level: Optional[str] = None
    metadata_json: Optional[dict] = None


class ArchiveItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    archive_file_id: uuid.UUID
    item_number: str
    title: str
    item_type: str
    author: Optional[str]
    document_date: Optional[str]
    pages: Optional[int]
    security_level: str
    storage_key: Optional[str]
    storage_bucket: Optional[str]
    file_size: Optional[int]
    file_format: Optional[str]
    sha256_hash: Optional[str]
    embedding_status: str
    tenant_id: Optional[uuid.UUID]
    metadata_json: Optional[dict]
    create_time: datetime
    update_time: datetime


# ─── 聚合视图（档案树节点） ───────────────────────────────────────────────────

class FondsTree(FondsOut):
    """全宗树（含案卷列表，不含条目，用于左侧导航树）"""
    children: List[ArchiveFileOut] = Field(default_factory=list)
