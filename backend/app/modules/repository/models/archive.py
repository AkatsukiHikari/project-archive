"""
档案库核心数据模型 v2

层级：
  全宗（Fonds，repo_fonds）             ← 保留不变
    └── 目录（Catalog）                  ← 档号编号域，新增
          ├── [一文一件] 件（Archive, level=item）
          └── [案卷卷内] 案卷（Archive, level=volume）
                        └── 卷内文件（Archive, level=item, parent_id=案卷id）

旧表 repo_archive_file / repo_archive_item 保留（不删），待确认后清理。
"""
import uuid
from typing import Optional, List
from sqlalchemy import String, Integer, BigInteger, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.common.entity.base import BaseEntity


class Catalog(BaseEntity):
    """目录：全宗下的编号域，案卷号/件号在目录范围内唯一。"""
    __tablename__ = "repo_catalog"

    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属全宗"
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="RESTRICT"),
        nullable=False, comment="对应门类"
    )
    catalog_no: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="目录号，同全宗内唯一"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="目录名称")
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="年度")
    org_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="by_item",
        comment="整理方式: by_item（一文一件）| by_volume（案卷卷内）"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )


class Archive(BaseEntity):
    """
    档案主表：统一存储件（item）和案卷（volume）。
    level=volume 时为案卷，level=item 且 parent_id=NULL 时为独立件，
    parent_id 有值时为卷内文件。
    """
    __tablename__ = "repo_archive"

    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_catalog.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="NULL=顶级，有值=卷内文件"
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="RESTRICT"),
        nullable=False, index=True
    )
    level: Mapped[str] = mapped_column(
        String(10), nullable=False, comment="volume | item"
    )

    # ── DA/T 必有项（规范化列，全部建索引）──────────────────────────
    archive_no: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="档号（生成结果，可手动覆盖）"
    )
    fonds_code: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="全宗号"
    )
    catalog_no: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="目录号"
    )
    volume_no: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="案卷号（一文一件时为空）"
    )
    item_no: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="件号"
    )
    year: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True, comment="年度"
    )
    title: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True, comment="题名"
    )
    creator: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, index=True, comment="责任者"
    )
    security_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="public",
        comment="密级: public | internal | confidential | secret"
    )
    retention_period: Mapped[str] = mapped_column(
        String(20), nullable=False, default="permanent",
        comment="保管期限: permanent | long | short"
    )
    doc_date: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="文件日期 YYYY-MM-DD"
    )
    pages: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="页数")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        comment="active | restricted | destroyed"
    )

    # ── 门类私有字段 ─────────────────────────────────────────────────
    ext_fields: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="门类私有字段（GIN 索引）"
    )

    # ── 存储引用 ──────────────────────────────────────────────────────
    storage_key: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    storage_bucket: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    file_format: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sha256_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # ── 系统字段 ──────────────────────────────────────────────────────
    embedding_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="ES/向量化状态: pending | processing | done | failed"
    )
    es_synced_at: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True, comment="最后成功同步 ES 的时间 ISO8601"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )

    # ── 关联 ──────────────────────────────────────────────────────────
    children: Mapped[List["Archive"]] = relationship(
        "Archive", back_populates="parent",
        foreign_keys="Archive.parent_id"
    )
    parent: Mapped[Optional["Archive"]] = relationship(
        "Archive", back_populates="children",
        foreign_keys="Archive.parent_id", remote_side="Archive.id"
    )
