from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from app.modules.iam import schemas
from app.modules.iam.api.dependencies import get_role_service, get_current_user
from app.modules.iam.services.role_service import RoleService
from app.modules.iam.models import User
from app.common.response import success, ResponseModel
import uuid

router = APIRouter()

@router.get(
    "",
    response_model=ResponseModel[List[schemas.Role]],
    summary="获取角色列表",
    response_description="筛选条件下的系统角色列表记录"
)
async def list_roles(
    tenant_id: Optional[uuid.UUID] = Query(None, description="按租户过滤 (未提供则获取所有全局角色)"),
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """获取角色列表。非超级管理员强制隔离到自身租户。"""
    effective_tenant_id = tenant_id
    if not current_user.is_superadmin and effective_tenant_id is None:
        effective_tenant_id = current_user.tenant_id
    roles = await role_service.get_roles(effective_tenant_id)
    return success(data=[schemas.Role.model_validate(r).model_dump(mode="json") for r in roles])

@router.get(
    "/{role_id}",
    response_model=ResponseModel[schemas.Role],
    summary="获取指定角色详情",
    response_description="角色基础信息及所有绑定的权限菜单 IDs"
)
async def get_role(
    role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """获取指定角色详情"""
    role = await role_service.get_role(role_id)
    return success(data=schemas.Role.model_validate(role).model_dump(mode="json"))

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseModel[schemas.Role],
    summary="创建角色",
    response_description="角色全量记录"
)
async def create_role(
    role_in: schemas.RoleCreate,
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """创建新角色，并分配权限矩阵（传入 menu_ids）"""
    role = await role_service.create_role(role_in)
    return success(data=schemas.Role.model_validate(role).model_dump(mode="json"))

@router.put(
    "/{role_id}",
    response_model=ResponseModel[schemas.Role],
    summary="更新角色信息及关联的权限配置",
    response_description="更新后的角色记录"
)
async def update_role(
    role_id: uuid.UUID,
    role_in: schemas.RoleUpdate,
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """更新角色信息及关联的权限配置"""
    role = await role_service.update_role(role_id, role_in)
    return success(data=schemas.Role.model_validate(role).model_dump(mode="json"))

@router.delete(
    "/{role_id}",
    response_model=ResponseModel[None],
    summary="软删除指定角色",
    response_description="成功应答"
)
async def delete_role(
    role_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    role_service: RoleService = Depends(get_role_service)
):
    """删除角色 (软删除)"""
    await role_service.delete_role(role_id)
    return success(message="删除成功")
