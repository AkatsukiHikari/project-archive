from sqlalchemy import String, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.common.entity.base import BaseEntity, Base
from typing import List, Optional
import uuid

# Association table for Role-Menu many-to-many relationship
role_menu_association = Table(
    "iam_role_menu",
    Base.metadata,
    Column("role_id", ForeignKey("iam_role.id", ondelete="CASCADE"), primary_key=True),
    Column("menu_id", ForeignKey("iam_menu.id", ondelete="CASCADE"), primary_key=True),
)

class Menu(BaseEntity):
    __tablename__ = "iam_menu"
    
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_menu.id", ondelete="CASCADE"), nullable=True, index=True, comment="父级菜单/权限ID")
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, comment="权限/菜单编码, 例如'system:user:add'")
    name: Mapped[str] = mapped_column(String(50), comment="名称")
    type: Mapped[str] = mapped_column(String(20), comment="类型: DIR(目录) MENU(菜单) BUTTON(按钮/权限)")
    
    path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="路由路径 (仅菜单)")
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="图标")
    sort_order: Mapped[int] = mapped_column(default=0, comment="排序号")
    is_visible: Mapped[bool] = mapped_column(default=True, comment="是否可见")
    is_system: Mapped[bool] = mapped_column(default=False, server_default="false", comment="系统内置菜单，不可删除")

    children: Mapped[List["Menu"]] = relationship("Menu", back_populates="parent", remote_side="Menu.id")
    parent: Mapped[Optional["Menu"]] = relationship("Menu", back_populates="children", remote_side="Menu.parent_id")
    roles: Mapped[List["Role"]] = relationship("Role", secondary=role_menu_association, back_populates="menus")
