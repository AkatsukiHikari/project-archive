import uuid
from typing import Optional
from sqlalchemy import String, Text, Integer, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.common.entity.base import BaseEntity


class SIPRecord(BaseEntity):
    __tablename__ = "col_sip_record"

    title: Mapped[str] = mapped_column(String(512), nullable=False, comment="SIP标题")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="描述")
    submitter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="提交人ID",
    )
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("iam_tenant.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="所属租户ID",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="draft",
        comment="状态: draft/submitted/reviewing/accepted/rejected",
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="档案元数据JSON"
    )
    file_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="文件数量"
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="备注")
