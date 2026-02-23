from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, status, Query
from app.modules.iam import schemas
from app.modules.iam.models import User
from app.modules.iam.services.iam_service import IAMService
from app.modules.iam.api.dependencies import get_iam_service, get_current_user
from app.common.response import success
import uuid

router = APIRouter()

@router.get("/")
async def get_users(
    tenant_id: Optional[uuid.UUID] = Query(None, description="按租户过滤"),
    org_id: Optional[uuid.UUID] = Query(None, description="按组织过滤"),
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """获取用户列表"""
    users = await service.get_users(tenant_id=tenant_id, org_id=org_id)
    return success(data=[schemas.User.model_validate(u).model_dump(mode="json") for u in users])

@router.get("/{user_id}")
async def get_user(
    user_id: uuid.UUID,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """获取指定用户详情"""
    user = await service.get_user_by_id(user_id)
    if not user:
        return success(code=404, message="用户不存在")
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))

@router.post("/")
async def create_user(
    user_in: schemas.UserCreate,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """创建新用户并分配租户/组织/角色"""
    user = await service.register_user(user_in)
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))

@router.put("/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    user_in: schemas.UserUpdate,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """更新用户信息及其关联角色"""
    user = await service.update_user(user_id, user_in)
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))

@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """删除用户 (软删除)"""
    await service.delete_user(user_id)
    return success(message="删除成功")
