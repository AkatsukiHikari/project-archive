import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.services.category_service import CategoryService
from app.modules.repository.schemas.category import (
    CategoryCreate, CategoryUpdate, CategoryRead, FieldDefinition,
)
from app.common.response import success, ResponseModel

router = APIRouter(prefix="/archive/categories", tags=["档案门类"])


@router.get("", response_model=ResponseModel[list[CategoryRead]])
async def list_categories(
    parent_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    items = await svc.list_all(tenant_id=current_user.tenant_id, parent_id=parent_id)
    return success([CategoryRead.model_validate(i) for i in items])


@router.post("", response_model=ResponseModel[CategoryRead])
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(CategoryRead.model_validate(item))


@router.post("/{category_id}/clone", response_model=ResponseModel[CategoryRead])
async def clone_category(
    category_id: uuid.UUID,
    new_code: str = Query(...),
    new_name: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    item = await svc.clone(category_id, new_code, new_name, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(CategoryRead.model_validate(item))


@router.put("/{category_id}", response_model=ResponseModel[CategoryRead])
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    item = await svc.update(category_id, data)
    await db.commit()
    return success(CategoryRead.model_validate(item))


@router.delete("/{category_id}", response_model=ResponseModel[None])
async def delete_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = CategoryService(db)
    await svc.delete(category_id)
    await db.commit()
    return success()


@router.get("/{category_id}/schema", response_model=ResponseModel[list[FieldDefinition]])
async def get_category_schema(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """读取门类的字段 schema（表单设计器加载入口）。"""
    svc = CategoryService(db)
    category = await svc.get(category_id)
    schema = category.field_schema or []
    return success([FieldDefinition.model_validate(f) for f in schema])


@router.put("/{category_id}/schema", response_model=ResponseModel[list[FieldDefinition]])
async def update_category_schema(
    category_id: uuid.UUID,
    fields: list[FieldDefinition],
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """保存门类的字段 schema（表单设计器保存入口）。"""
    svc = CategoryService(db)
    serialized = [f.model_dump() for f in fields]
    category = await svc.update_schema(category_id, serialized)
    await db.commit()
    return success([FieldDefinition.model_validate(f) for f in category.field_schema])
