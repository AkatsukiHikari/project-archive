import uuid
from typing import Optional
from sqlalchemy import String, Boolean, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.common.entity.base import BaseEntity


class ArchiveNoRule(BaseEntity):
    """
    档号规则配置表。
    rule_template JSONB 存储规则段定义，由 Plan B 的规则引擎解释执行。
    """
    __tablename__ = "repo_archive_no_rule"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属门类"
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="规则名称")
    rule_template: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="规则段定义（见 docs/features/feature_档案管理.md 第五章）"
    )
    seq_scope: Mapped[str] = mapped_column(
        String(20), nullable=False, default="catalog_year",
        comment="序号重置范围: catalog | catalog_year | fonds"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", comment="是否启用"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
