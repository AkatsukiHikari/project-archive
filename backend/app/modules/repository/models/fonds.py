import uuid
from typing import Optional
from sqlalchemy import String, Text, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.common.entity.base import BaseEntity


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
        String(20), nullable=False, comment="保管期限"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="全宗状态"
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
