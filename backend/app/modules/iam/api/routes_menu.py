from typing import List
from fastapi import APIRouter, Depends, status
from app.modules.iam import schemas
from app.modules.iam.api.dependencies import get_menu_service, get_current_user
from app.modules.iam.services.menu_service import MenuService
from app.modules.iam.models import User
import uuid

router = APIRouter()

@router.get("/tree", response_model=List[schemas.MenuTree])
async def get_menu_tree(
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """获取所有菜单/权限的树状结构"""
    return await menu_service.get_menu_tree()

@router.get("/{menu_id}", response_model=schemas.Menu)
async def get_menu(
    menu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """获取指定菜单/权限详情"""
    return await menu_service.get_menu(menu_id)

@router.post("/", response_model=schemas.Menu, status_code=status.HTTP_201_CREATED)
async def create_menu(
    menu_in: schemas.MenuCreate,
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """创建新菜单/权限节点"""
    return await menu_service.create_menu(menu_in)

@router.put("/{menu_id}", response_model=schemas.Menu)
async def update_menu(
    menu_id: uuid.UUID,
    menu_in: schemas.MenuUpdate,
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """更新菜单/权限信息"""
    return await menu_service.update_menu(menu_id, menu_in)

@router.delete("/{menu_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu(
    menu_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    menu_service: MenuService = Depends(get_menu_service)
):
    """删除菜单/权限节点"""
    await menu_service.delete_menu(menu_id)
