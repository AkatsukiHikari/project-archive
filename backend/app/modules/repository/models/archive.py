"""
档案库核心数据模型

中国档案标准（DA/T）层级：
  全宗（Fonds）       — 一个机构/单位的全部档案集合，最顶层
    └── 案卷（ArchiveFile）— 若干相关文件组成的保管单位
          └── 文件条目（ArchiveItem）— 最小归档单元，对应一份具体文件

数据库表前缀：repo_
"""

import uuid
from typing import Optional, List
from sqlalchemy import String, Text, Integer, JSON, ForeignKey, Date, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.common.entity.base import BaseEntity
import enum


# ─── 枚举 ────────────────────────────────────────────────────────────────────

class RetentionPeriod(str, enum.Enum):
    """保管期限（DA/T 18-1999）"""
    PERMANENT = "permanent"   # 永久
    LONG = "long"             # 长期（30年）
    SHORT = "short"           # 短期（10年）


class ArchiveStatus(str, enum.Enum):
    """档案状态"""
    ACTIVE = "active"         # 正常
    RESTRICTED = "restricted" # 受限访问
    DESTROYED = "destroyed"   # 已销毁


class ItemType(str, enum.Enum):
    """文件类型"""
    DOCUMENT = "document"     # 文书档案
    AUDIO = "audio"           # 音频档案
    VIDEO = "video"           # 视频档案
    PHOTO = "photo"           # 照片档案
    ELECTRONIC = "electronic" # 电子档案


# ─── 全宗（Fonds）────────────────────────────────────────────────────────────

class Fonds(BaseEntity):
    """
    全宗：档案库最顶层单位，代表一个机构的全部档案集合。

    全宗号（fonds_code）是全国统一编号，如 "J001"（机关）/"Q001"（企业）。
    """
    __tablename__ = "repo_fonds"

    fonds_code: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="全宗号（全国唯一）"
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="全宗名称（机构全称）"
    )
    short_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="全宗简称"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="全宗说明"
    )
    start_year: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="起始年度"
    )
    end_year: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="截止年度（现存全宗为空）"
    )
    retention_period: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RetentionPeriod.PERMANENT.value, comment="保管期限"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ArchiveStatus.ACTIVE.value, comment="全宗状态"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="所属租户"
    )
    custodian_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="SET NULL"),
        nullable=True, comment="责任保管人"
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="扩展元数据"
    )

    # 关联
    archive_files: Mapped[List["ArchiveFile"]] = relationship(
        "ArchiveFile", back_populates="fonds", cascade="all, delete-orphan"
    )


# ─── 案卷（ArchiveFile）──────────────────────────────────────────────────────

class ArchiveFile(BaseEntity):
    """
    案卷：若干相关文件的集合体，是档案的保管和利用单位。
    一个全宗下可有多个案卷，按年度/业务分类组织。
    """
    __tablename__ = "repo_archive_file"

    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属全宗"
    )
    file_number: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="案卷号（同一全宗内唯一）"
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="案卷题名"
    )
    year: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True, comment="形成年度"
    )
    classification: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="分类（科目）"
    )
    retention_period: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RetentionPeriod.PERMANENT.value, comment="保管期限"
    )
    security_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="public", comment="密级：public/internal/confidential/secret"
    )
    item_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="文件条目数"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ArchiveStatus.ACTIVE.value, comment="案卷状态"
    )
    # SIP 来源（可选：由 SIP 审批归档后关联）
    source_sip_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("col_sip_record.id", ondelete="SET NULL"),
        nullable=True, comment="来源SIP包ID"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="所属租户"
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="扩展元数据"
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="备注"
    )

    # 关联
    fonds: Mapped["Fonds"] = relationship("Fonds", back_populates="archive_files")
    items: Mapped[List["ArchiveItem"]] = relationship(
        "ArchiveItem", back_populates="archive_file", cascade="all, delete-orphan"
    )


# ─── 文件条目（ArchiveItem）──────────────────────────────────────────────────

class ArchiveItem(BaseEntity):
    """
    文件条目：档案库的最小单元，对应一份具体的档案文件。
    每个条目记录文件的元数据、存储位置及完整性哈希。
    """
    __tablename__ = "repo_archive_item"

    archive_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_file.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属案卷"
    )
    item_number: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="文件号（案卷内序号）"
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="文件题名"
    )
    item_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ItemType.DOCUMENT.value, comment="文件类型"
    )
    author: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="责任者（作者/发文机关）"
    )
    document_date: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="文件日期（YYYY-MM-DD）"
    )
    pages: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="页数"
    )
    security_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="public", comment="密级"
    )
    # 存储引用
    storage_key: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="对象存储键（MinIO/S3 object key）"
    )
    storage_bucket: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, comment="存储桶名"
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="文件大小（字节）"
    )
    file_format: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="文件格式，如 pdf/docx/tiff"
    )
    # 完整性哈希（四性检测使用）
    sha256_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA-256 哈希值"
    )
    # AI 向量化状态
    embedding_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="向量化状态: pending/processing/done/failed"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="所属租户"
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="扩展元数据（原文件头信息等）"
    )

    # 关联
    archive_file: Mapped["ArchiveFile"] = relationship(
        "ArchiveFile", back_populates="items"
    )
