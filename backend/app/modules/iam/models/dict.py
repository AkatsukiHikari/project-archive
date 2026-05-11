"""系统数据字典模型。

sys_dict       — 字典类型表（如 MJ=密级、BGQX=保管期限）
sys_dict_item  — 字典项表（字典类型下的选项列表）
"""
import uuid
from typing import Optional

from sqlalchemy import String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.common.entity.base import BaseEntity


class SysDict(BaseEntity):
    """字典类型：一行 = 一组选项集合，如"密级"。"""

    __tablename__ = "sys_dict"

    dict_type: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False,
        comment="字典类型代码，全局唯一，如 MJ / BGQX",
    )
    dict_name: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="字典中文名称",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="说明",
    )
    is_builtin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
        comment="是否系统内置（内置字典不可删除）",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0",
        comment="排序号（升序）",
    )

    items: Mapped[list["SysDictItem"]] = relationship(
        "SysDictItem",
        primaryjoin="and_(SysDict.dict_type == SysDictItem.dict_type, SysDictItem.is_deleted == False)",
        foreign_keys="SysDictItem.dict_type",
        lazy="select",
        order_by="SysDictItem.sort_order",
        viewonly=True,
    )


class SysDictItem(BaseEntity):
    """字典项：一行 = 字典中的一个选项。"""

    __tablename__ = "sys_dict_item"

    dict_type: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("sys_dict.dict_type", ondelete="CASCADE"),
        nullable=False, index=True,
        comment="所属字典类型代码",
    )
    item_value: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="存储值（也是 select options 的 value）",
    )
    item_label: Mapped[str] = mapped_column(
        String(200), nullable=False,
        comment="显示标签",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false",
        comment="是否默认选中",
    )
    sort_order: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0",
        comment="排序号（升序）",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
        comment="备注",
    )
