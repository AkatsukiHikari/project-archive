from typing import List
from fastapi import APIRouter, Depends, status
from app.modules.iam import schemas
from app.modules.iam.api.dependencies import get_menu_service, get_current_user
from app.modules.iam.services.menu_service import MenuService
from app.modules.iam.models import User
from app.common.response import success
import uuid

router = APIRouter()

@router.get("/tree")
async def get_menu_tree(
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """获取所有菜单/权限的树状结构"""
    tree = await menu_service.get_menu_tree()
    return success(data=[schemas.MenuTree.model_validate(m).model_dump(mode="json") for m in tree])

@router.get("/{menu_id}")
async def get_menu(
    menu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """获取指定菜单/权限详情"""
    menu = await menu_service.get_menu(menu_id)
    return success(data=schemas.Menu.model_validate(menu).model_dump(mode="json"))

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_menu(
    menu_in: schemas.MenuCreate,
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """创建新菜单/权限节点"""
    menu = await menu_service.create_menu(menu_in)
    return success(data=schemas.Menu.model_validate(menu).model_dump(mode="json"))

@router.put("/{menu_id}")
async def update_menu(
    menu_id: uuid.UUID,
    menu_in: schemas.MenuUpdate,
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """更新菜单/权限信息"""
    menu = await menu_service.update_menu(menu_id, menu_in)
    return success(data=schemas.Menu.model_validate(menu).model_dump(mode="json"))

@router.delete("/{menu_id}")
async def delete_menu(
    menu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """删除菜单/权限节点"""
    await menu_service.delete_menu(menu_id)
    return success(message="删除成功")
