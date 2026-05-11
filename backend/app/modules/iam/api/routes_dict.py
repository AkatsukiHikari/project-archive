"""数据字典 REST API。"""
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.iam.services.dict_service import DictService
from app.modules.iam.schemas.dict import (
    DictCreate, DictUpdate, DictRead, DictReadSimple,
    DictItemCreate, DictItemUpdate, DictItemRead,
)
from app.common.response import success, ResponseModel

router = APIRouter(prefix="/sys/dicts", tags=["数据字典"])


# ── 字典类型 ──────────────────────────────────────────────────────────────────

@router.get("", response_model=ResponseModel[list[DictReadSimple]])
async def list_dicts(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = DictService(db)
    rows = await svc.list_dicts()
    result = []
    for d, cnt in rows:
        s = DictReadSimple.model_validate(d)
        s.item_count = cnt
        result.append(s)
    return success(result)


@router.post("", response_model=ResponseModel[DictReadSimple])
async def create_dict(
    data: DictCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = DictService(db)
    d = await svc.create_dict(data)
    await db.commit()
    s = DictReadSimple.model_validate(d)
    s.item_count = 0
    return success(s)


@router.put("/{dict_type}", response_model=ResponseModel[DictReadSimple])
async def update_dict(
    dict_type: str,
    data: DictUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = DictService(db)
    d = await svc.update_dict(dict_type, data)
    await db.commit()
    s = DictReadSimple.model_validate(d)
    return success(s)


@router.delete("/{dict_type}", response_model=ResponseModel[None])
async def delete_dict(
    dict_type: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = DictService(db)
    await svc.delete_dict(dict_type)
    await db.commit()
    return success()


# ── 字典项 ────────────────────────────────────────────────────────────────────

@router.get("/{dict_type}/items", response_model=ResponseModel[list[DictItemRead]])
async def list_items(
    dict_type: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = DictService(db)
    items = await svc.get_items_by_type(dict_type)
    return success([DictItemRead.model_validate(i) for i in items])


@router.post("/{dict_type}/items", response_model=ResponseModel[DictItemRead])
async def create_item(
    dict_type: str,
    data: DictItemCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = DictService(db)
    item = await svc.create_item(dict_type, data)
    await db.commit()
    return success(DictItemRead.model_validate(item))


@router.put("/items/{item_id}", response_model=ResponseModel[DictItemRead])
async def update_item(
    item_id: uuid.UUID,
    data: DictItemUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = DictService(db)
    item = await svc.update_item(item_id, data)
    await db.commit()
    return success(DictItemRead.model_validate(item))


@router.delete("/items/{item_id}", response_model=ResponseModel[None])
async def delete_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    svc = DictService(db)
    await svc.delete_item(item_id)
    await db.commit()
    return success()
