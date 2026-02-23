import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, func, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Base class for all database models"""
    pass

class AuditMixin:
    """Mixin for audit columns"""
    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(), 
        comment="更新时间"
    )
    create_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), 
        nullable=True, 
        comment="创建人ID"
    )
    is_deleted: Mapped[bool] = mapped_column(
        default=False, 
        server_default="false", 
        comment="是否逻辑删除"
    )

class BaseEntity(Base, AuditMixin):
    """Base entity with UUID primary key and audit columns"""
    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="唯一标识"
    )
