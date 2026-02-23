from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.common.entity.base import BaseEntity
from typing import List, Optional
import uuid

class Tenant(BaseEntity):
    __tablename__ = "iam_tenant"
    
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="租户编码")
    name: Mapped[str] = mapped_column(String(100), comment="租户名称")
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="租户描述")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    
    organizations: Mapped[List["Organization"]] = relationship("Organization", back_populates="tenant")
    users: Mapped[List["User"]] = relationship("User", back_populates="tenant")
    roles: Mapped[List["Role"]] = relationship("Role", back_populates="tenant")


class Organization(BaseEntity):
    __tablename__ = "iam_organization"
    
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_tenant.id", ondelete="CASCADE"), index=True, comment="所属租户ID")
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_organization.id", ondelete="CASCADE"), nullable=True, index=True, comment="父组织ID")
    
    name: Mapped[str] = mapped_column(String(100), comment="组织名称")
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True, comment="组织编码")
    sort_order: Mapped[int] = mapped_column(default=0, comment="排序号")
    
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="organizations")
    children: Mapped[List["Organization"]] = relationship("Organization", back_populates="parent", remote_side="Organization.id")
    parent: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="children", remote_side="Organization.parent_id")
    users: Mapped[List["User"]] = relationship("User", back_populates="organization")
