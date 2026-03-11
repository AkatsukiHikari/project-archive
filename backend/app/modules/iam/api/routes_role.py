from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from app.modules.iam import schemas
from app.modules.iam.api.dependencies import get_role_service, get_current_user
from app.modules.iam.services.role_service import RoleService
from app.modules.iam.models import User
from app.common.response import success
import uuid

router = APIRouter()

@router.get("")
async def list_roles(
    tenant_id: Optional[uuid.UUID] = Query(None, description="按租户过滤 (未提供则获取所有全局角色)"),
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """获取角色列表"""
    roles = await role_service.get_roles(tenant_id)
    return success(data=[schemas.Role.model_validate(r).model_dump(mode="json") for r in roles])

@router.get("/{role_id}")
async def get_role(
    role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """获取指定角色详情"""
    role = await role_service.get_role(role_id)
    return success(data=schemas.Role.model_validate(role).model_dump(mode="json"))

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_role(
    role_in: schemas.RoleCreate,
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """创建新角色，并分配权限矩阵"""
    role = await role_service.create_role(role_in)
    return success(data=schemas.Role.model_validate(role).model_dump(mode="json"))

@router.put("/{role_id}")
async def update_role(
    role_id: uuid.UUID,
    role_in: schemas.RoleUpdate,
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """更新角色信息及关联的权限配置"""
    role = await role_service.update_role(role_id, role_in)
    return success(data=schemas.Role.model_validate(role).model_dump(mode="json"))

@router.delete("/{role_id}")
async def delete_role(
    role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """删除角色 (软删除)"""
    await role_service.delete_role(role_id)
    return success(message="删除成功")
