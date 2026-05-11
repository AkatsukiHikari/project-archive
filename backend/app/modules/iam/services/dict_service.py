"""数据字典 Service。"""
import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.exceptions.base import NotFoundException, ValidationException
from app.common.error_code import ErrorCode
from app.modules.iam.models.dict import SysDict, SysDictItem
from app.modules.iam.schemas.dict import (
    DictCreate, DictUpdate, DictItemCreate, DictItemUpdate,
)


class DictService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    # ── 字典类型 CRUD ─────────────────────────────────────────────────────────

    async def list_dicts(self) -> list[tuple[SysDict, int]]:
        """返回 (SysDict, item_count) 列表，按 sort_order 升序。"""
        stmt = (
            select(SysDict, func.count(SysDictItem.id).label("item_count"))
            .outerjoin(
                SysDictItem,
                (SysDictItem.dict_type == SysDict.dict_type)
                & SysDictItem.is_deleted.is_(False),
            )
            .where(SysDict.is_deleted.is_(False))
            .group_by(SysDict.id)
            .order_by(SysDict.sort_order, SysDict.dict_type)
        )
        result = await self._db.execute(stmt)
        return list(result.all())

    async def get_dict(self, dict_type: str) -> SysDict:
        stmt = (
            select(SysDict)
            .where(SysDict.dict_type == dict_type, SysDict.is_deleted.is_(False))
            .options(
                selectinload(SysDict.items)  # type: ignore[attr-defined]
            )
        )
        row = (await self._db.execute(stmt)).scalar_one_or_none()
        if not row:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message=f"字典 {dict_type} 不存在")
        return row

    async def get_items_by_type(self, dict_type: str) -> list[SysDictItem]:
        """快速获取字典项列表（不加载父字典对象）。"""
        stmt = (
            select(SysDictItem)
            .where(
                SysDictItem.dict_type == dict_type,
                SysDictItem.is_deleted.is_(False),
            )
            .order_by(SysDictItem.sort_order, SysDictItem.item_value)
        )
        return list((await self._db.execute(stmt)).scalars().all())

    async def create_dict(self, data: DictCreate) -> SysDict:
        # 检查 dict_type 唯一
        exists = (await self._db.execute(
            select(SysDict.id).where(
                SysDict.dict_type == data.dict_type,
                SysDict.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if exists:
            raise ValidationException(
                code=ErrorCode.VALIDATION_ERROR,
                message=f"字典代码 {data.dict_type} 已存在",
            )
        d = SysDict(
            dict_type=data.dict_type,
            dict_name=data.dict_name,
            description=data.description,
            sort_order=data.sort_order,
            is_builtin=False,
        )
        self._db.add(d)
        await self._db.flush()
        return d

    async def update_dict(self, dict_type: str, data: DictUpdate) -> SysDict:
        d = await self._get_dict_model(dict_type)
        if data.dict_name is not None:
            d.dict_name = data.dict_name
        if data.description is not None:
            d.description = data.description
        if data.sort_order is not None:
            d.sort_order = data.sort_order
        await self._db.flush()
        return d

    async def delete_dict(self, dict_type: str) -> None:
        d = await self._get_dict_model(dict_type)
        if d.is_builtin:
            raise ValidationException(
                code=ErrorCode.VALIDATION_ERROR,
                message="内置字典不可删除",
            )
        d.is_deleted = True
        # 软删字典项
        items = await self.get_items_by_type(dict_type)
        for item in items:
            item.is_deleted = True
        await self._db.flush()

    # ── 字典项 CRUD ───────────────────────────────────────────────────────────

    async def create_item(self, dict_type: str, data: DictItemCreate) -> SysDictItem:
        await self._get_dict_model(dict_type)  # 确保字典存在
        item = SysDictItem(
            dict_type=dict_type,
            item_value=data.item_value,
            item_label=data.item_label,
            is_default=data.is_default,
            sort_order=data.sort_order,
            description=data.description,
        )
        self._db.add(item)
        await self._db.flush()
        return item

    async def update_item(self, item_id: uuid.UUID, data: DictItemUpdate) -> SysDictItem:
        item = await self._get_item_model(item_id)
        if data.item_value is not None:
            item.item_value = data.item_value
        if data.item_label is not None:
            item.item_label = data.item_label
        if data.is_default is not None:
            item.is_default = data.is_default
        if data.sort_order is not None:
            item.sort_order = data.sort_order
        if data.description is not None:
            item.description = data.description
        await self._db.flush()
        return item

    async def delete_item(self, item_id: uuid.UUID) -> None:
        item = await self._get_item_model(item_id)
        item.is_deleted = True
        await self._db.flush()

    # ── 内部辅助 ──────────────────────────────────────────────────────────────

    async def _get_dict_model(self, dict_type: str) -> SysDict:
        row = (await self._db.execute(
            select(SysDict).where(
                SysDict.dict_type == dict_type,
                SysDict.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if not row:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message=f"字典 {dict_type} 不存在")
        return row

    async def _get_item_model(self, item_id: uuid.UUID) -> SysDictItem:
        row = (await self._db.execute(
            select(SysDictItem).where(
                SysDictItem.id == item_id,
                SysDictItem.is_deleted.is_(False),
            )
        )).scalar_one_or_none()
        if not row:
            raise NotFoundException(code=ErrorCode.NOT_FOUND, message="字典项不存在")
        return row
