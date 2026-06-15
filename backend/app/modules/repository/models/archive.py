"""
档案库核心数据模型 v3

层级结构（catalog_type 决定类型，档号命名约束体现案卷/卷内关系）：
  ArchiveCategory（门类，树形）
    └── Catalog（目录，catalog_type: 案卷目录 | 卷内目录 | 一文一件）
          ├── 案卷目录  → ArchiveStaging / Archive（案卷件）
          │     ↑ Catalog.volume_archive_id（1:1 指向对应案卷暂存 ID）
          ├── 卷内目录  → ArchiveStaging / Archive（卷内件）
          └── 一文一件  → ArchiveStaging / Archive（独立件）

两库设计：
  repo_archive_staging   临时库（非分区，draft/pending_review/rejected）
  repo_archive           正式库（PARTITION BY RANGE(ND)，archived→destroyed）

原文附件：
  repo_archive_attachment（archive_id 无 FK 约束，is_staging 标志来源库）

DA/T 核心字段删减说明：
  - 删除 MLH/AJH/JH：层级关系通过档号（DH）命名约束体现，非冗余列
  - 删除 level/parent_id：类型由 catalog_type 决定，层级由 DH 前缀推断
  - 正式库移除 storage 字段：原文挂 repo_archive_attachment
"""

import uuid
from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import AuditMixin, Base, BaseEntity

# DA/T 规范化字段：拼音缩写 → 中文标签（单一来源，供映射服务、规则引擎共用）
ARCHIVE_FIELD_MAP: dict[str, str] = {
    "DH": "档号",
    "QZH": "全宗号",
    "TM": "题名",
    "RZZ": "责任者",
    "ND": "年度",
    "WJRQ": "文件日期",
    "YS": "页数",
    "MJ": "密级",
    "BGQX": "保管期限",
    "KFZT": "开放状态",
}


class Catalog(BaseEntity):
    """目录：全宗下的整理单元，catalog_type 决定归档方式。"""

    __tablename__ = "repo_catalog"

    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属全宗",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="RESTRICT"),
        nullable=False,
        comment="对应门类",
    )
    catalog_no: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="目录号，同全宗内唯一"
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="目录名称")
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="年度")
    catalog_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="一文一件",
        comment="目录类型: 案卷目录 | 卷内目录 | 一文一件",
    )
    volume_archive_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="卷内目录专用：1:1 关联的案卷暂存记录 ID（无 DB FK 约束）",
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )


class ArchiveStaging(BaseEntity):
    """
    档案临时库（非分区）。

    状态机：draft → pending_review → rejected
                                   → archived（转入正式库后软删除）
    """

    __tablename__ = "repo_archive_staging"

    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_catalog.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    DH: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="档号（规则生成，可手动覆盖）"
    )
    QZH: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="全宗号（冗余自全宗，全宗号变更时通过工作流任务更新）",
    )
    TM: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True, comment="题名"
    )
    RZZ: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, index=True, comment="责任者"
    )
    ND: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, index=True, comment="年度"
    )
    WJRQ: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="文件日期 YYYY-MM-DD"
    )
    YS: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="页数")
    MJ: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="无",
        comment="密级: 无 | 秘密 | 机密 | 绝密（《保守国家秘密法》）",
    )
    BGQX: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="permanent",
        comment="保管期限: permanent | long | short",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="draft",
        comment="工作流状态: draft | pending_review | rejected",
    )
    ext_fields: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, comment="门类私有字段（GIN 索引）"
    )
    full_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="原文 OCR 全文（供全文检索，不在详情展示）"
    )
    embedding_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="向量化状态: pending | processing | done | failed",
    )
    es_synced_at: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    def __init__(self, **kwargs: object) -> None:
        kwargs.setdefault("MJ", "无")
        kwargs.setdefault("BGQX", "permanent")
        kwargs.setdefault("status", "draft")
        kwargs.setdefault("embedding_status", "pending")
        super().__init__(**kwargs)


class Archive(Base, AuditMixin):
    """
    档案正式库（PARTITION BY RANGE(ND)）。

    PK 为 (id, ND)，满足 PostgreSQL 分区表 PK 必须包含分区键的约束。
    ND NOT NULL — 归档时年度为必填项。
    子分区由 Alembic 迁移脚本按年创建（repo_archive_<year>）。

    状态机：archived → active → restricted → pending_destroy → destroyed
    """

    __tablename__ = "repo_archive"
    __table_args__ = (
        Index("ix_repo_archive_tenant_category", "tenant_id", "category_id"),
        Index("ix_repo_archive_catalog", "catalog_id"),
        {"postgresql_partition_by": 'RANGE ("ND")'},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    ND: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, comment="年度（分区键）"
    )

    fonds_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_fonds.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    catalog_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_catalog.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="RESTRICT"),
        nullable=False,
    )

    DH: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, index=True, comment="档号"
    )
    QZH: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="全宗号"
    )
    TM: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True, comment="题名"
    )
    RZZ: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, index=True, comment="责任者"
    )
    WJRQ: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="文件日期 YYYY-MM-DD"
    )
    YS: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="页数")
    MJ: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="无",
        comment="密级: 无 | 秘密 | 机密 | 绝密",
    )
    BGQX: Mapped[str] = mapped_column(
        String(20), nullable=False, default="permanent", comment="保管期限"
    )
    KFZT: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        index=True,
        comment="开放状态(当前访问标识): 开放 | 控制使用 | 延期开放 | 不开放（空=未鉴定）；"
        "鉴定日期/理由属鉴定过程元数据，见 appr_task/appr_item",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="archived",
        comment="工作流状态: archived | active | restricted | pending_destroy | destroyed",
    )
    ext_fields: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    full_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="原文 OCR 全文（供全文检索）"
    )
    embedding_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    es_synced_at: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
    )


class ArchiveAttachment(BaseEntity):
    """
    原文附件（电子版/扫描件）。

    archive_id 指向临时库（repo_archive_staging）或正式库（repo_archive）中的记录，
    is_staging 标志区分来源；不设 DB FK 约束，由应用层保证完整性。
    一条档案记录通常只有一个主附件（is_primary=True），特殊情况允许多个。
    """

    __tablename__ = "repo_archive_attachment"

    archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="档案记录 ID（临时库或正式库，无 DB FK 约束）",
    )
    is_staging: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="True=临时库附件，False=正式库附件",
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否主附件"
    )
    original_name: Mapped[str] = mapped_column(
        String(512), nullable=False, comment="原始文件名"
    )
    storage_key: Mapped[str] = mapped_column(
        String(1024), nullable=False, comment="对象存储路径"
    )
    storage_bucket: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="存储桶名"
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, comment="文件大小（字节）"
    )
    file_format: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="文件格式（pdf / jpg / …）"
    )
    page_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="页数（PDF）"
    )
    sha256_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="SHA256 完整性校验值"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="附件排序"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
