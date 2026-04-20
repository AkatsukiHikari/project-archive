import uuid
from typing import Optional

from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.common.entity.base import BaseEntity


class FieldMappingTemplate(BaseEntity):
    """
    字段映射模板表。
    保存"文件列头 → 档案字段"的映射规则，供下次导入自动预填。
    """
    __tablename__ = "repo_field_mapping_template"

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repo_archive_category.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属门类"
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="模板名称"
    )
    mappings: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True,
        comment="映射列表 [{source_col: '文件题名', target_field: 'title'}, ...]"
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
        comment="是否为该门类的默认映射模板"
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
