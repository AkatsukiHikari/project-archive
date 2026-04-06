from sqlalchemy import String, ForeignKey, Table, Column, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.common.entity.base import BaseEntity, Base
from typing import List, Optional
from datetime import datetime

# Association table for User-Role many-to-many relationship
user_role_association = Table(
    "iam_user_role",
    Base.metadata,
    Column("user_id", ForeignKey("iam_user.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", ForeignKey("iam_role.id", ondelete="CASCADE"), primary_key=True),
)

import uuid

class Role(BaseEntity):
    __tablename__ = "iam_role"
    
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="角色名称")
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="角色编码")
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="描述")
    
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_tenant.id", ondelete="CASCADE"), index=True, nullable=True, comment="所属租户ID (空为全局)")

    users: Mapped[List["User"]] = relationship(
        secondary=user_role_association, back_populates="roles"
    )
    menus: Mapped[List["Menu"]] = relationship(
        "Menu", secondary="iam_role_menu", back_populates="roles"
    )
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="roles")


class User(BaseEntity):
    __tablename__ = "iam_user"

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, comment="用户名")
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="邮箱")
    hashed_password: Mapped[str] = mapped_column(String(255), comment="加密密码")
    full_name: Mapped[Optional[str]] = mapped_column(String(100), comment="姓名")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否激活")
    is_superadmin: Mapped[bool] = mapped_column(default=False, server_default="false", comment="是否超级管理员")
    
    # Profile Fields
    avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="头像URL")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, comment="手机号")
    job_title: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="职位")
    location: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="办公地点")
    bio: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="个人简介")
    last_login_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="最后登录时间")
    
    # Multi-tenant and Org fields
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_tenant.id", ondelete="CASCADE"), nullable=True, index=True, comment="所属租户ID")
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_organization.id", ondelete="SET NULL"), nullable=True, index=True, comment="所属组织ID")

    roles: Mapped[List[Role]] = relationship(
        secondary=user_role_association, back_populates="users"
    )
    tenant: Mapped[Optional["Tenant"]] = relationship("Tenant", back_populates="users")
    organization: Mapped[Optional["Organization"]] = relationship("Organization", back_populates="users")
