from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query
from app.modules.iam import schemas
from app.modules.iam.models import User
from app.modules.iam.services.iam_service import IAMService
from app.modules.iam.api.dependencies import get_iam_service, get_current_user
from app.core.security.permissions import require_permissions
from app.common.response import success, ResponseModel
import uuid

router = APIRouter()


@router.get(
    "",
    response_model=ResponseModel[List[schemas.User]],
    summary="获取用户列表 (Admin)",
    response_description="支持按租户和组织过滤的用户列表"
)
async def get_users(
    tenant_id: Optional[uuid.UUID] = Query(None, description="按租户过滤"),
    org_id: Optional[uuid.UUID] = Query(None, description="按组织过滤"),
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(require_permissions("user:list"))
):
    """管理员获取系统用户列表。非超级管理员强制隔离到自己的租户。"""
    # 非超级管理员且未指定 tenant_id 时，强制使用自身租户
    effective_tenant_id = tenant_id
    if not current_user.is_superadmin and effective_tenant_id is None:
        effective_tenant_id = current_user.tenant_id
    users = await service.get_users(tenant_id=effective_tenant_id, org_id=org_id)
    return success(data=[schemas.User.model_validate(u).model_dump(mode="json") for u in users])


@router.get(
    "/{user_id}",
    response_model=ResponseModel[schemas.User],
    summary="获取指定用户详情 (Admin)",
    response_description="指定用户的全量信息"
)
async def get_user(
    user_id: uuid.UUID,
    service: IAMService = Depends(get_iam_service),
    _ = Depends(require_permissions("user:read"))
):
    """管理员根据 UUID 获取特定用户"""
    user = await service.get_user_by_id(user_id)
    if not user:
        return success(code=404, message="用户不存在")
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))


@router.post(
    "/",
    response_model=ResponseModel[schemas.User],
    summary="创建新用户 (Admin)",
    response_description="创建成功后的用户信息"
)
async def create_user(
    user_in: schemas.UserCreate,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(require_permissions("user:create"))
):
    """管理员创建新用户，可分配租户、组织、角色等"""
    user = await service.register_user(user_in, created_by=current_user.id)
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))


@router.put(
    "/{user_id}",
    response_model=ResponseModel[schemas.User],
    summary="更新用户信息 (Admin)",
    response_description="更新后的用户信息"
)
async def update_user(
    user_id: uuid.UUID,
    user_in: schemas.UserUpdate,
    service: IAMService = Depends(get_iam_service),
    _ = Depends(require_permissions("user:update"))
):
    """管理员全量或增量更新用户信息及关联角色"""
    user = await service.update_user(user_id, user_in)
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))


@router.delete(
    "/{user_id}",
    response_model=ResponseModel[None],
    summary="删除用户 (Admin)",
    response_description="仅返回成功消息"
)
async def delete_user(
    user_id: uuid.UUID,
    service: IAMService = Depends(get_iam_service),
    _ = Depends(require_permissions("user:delete"))
):
    """对用户进行软删除操作"""
    await service.delete_user(user_id)
    return success(message="删除成功")
