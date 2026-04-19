import uuid
from typing import Optional
from sqlalchemy import String, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.common.entity.base import BaseEntity


class ArchiveCategory(BaseEntity):
    """
    档案门类定义表。
    内置门类（is_builtin=True）对应 DA/T 标准，不可删除。
    自定义门类通过克隆内置门类后在表单设计器中编辑字段 schema。
    """
    __tablename__ = "repo_archive_category"

    code: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, comment="门类代码，如 WS/KJ/HJ"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="门类名称"
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="SET NULL"),
        nullable=True, comment="父门类（专业档案子门类使用）"
    )
    base_category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="SET NULL"),
        nullable=True, comment="克隆来源（自定义门类）"
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
        comment="是否内置 DA/T 标准门类"
    )
    requires_privacy_guard: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
        comment="是否含个人隐私字段（专业档案）"
    )
    field_schema: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="字段定义列表 list[FieldDefinition]"
    )
    archive_no_rule_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_no_rule.id", ondelete="SET NULL"),
        nullable=True, comment="激活的档号规则（NULL 表示不自动生成）"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True, comment="所属租户（NULL=系统内置）"
    )
