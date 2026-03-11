from typing import List
from fastapi import APIRouter, Depends, status
from app.modules.iam import schemas
from app.modules.iam.api.dependencies import get_tenant_service, get_current_user
from app.modules.iam.services.tenant_service import TenantService
from app.modules.iam.models import User
from app.common.response import success
import uuid

router = APIRouter()

@router.get("")
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """获取所有租户列表"""
    tenants = await tenant_service.get_tenants(skip=skip, limit=limit)
    return success(data=[schemas.Tenant.model_validate(t).model_dump(mode="json") for t in tenants])

@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """获取指定租户详情"""
    tenant = await tenant_service.get_tenant(tenant_id)
    return success(data=schemas.Tenant.model_validate(tenant).model_dump(mode="json"))

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: schemas.TenantCreate,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """创建新租户"""
    tenant = await tenant_service.create_tenant(tenant_in)
    return success(data=schemas.Tenant.model_validate(tenant).model_dump(mode="json"))

@router.put("/{tenant_id}")
async def update_tenant(
    tenant_id: uuid.UUID,
    tenant_in: schemas.TenantUpdate,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """更新租户信息"""
    tenant = await tenant_service.update_tenant(tenant_id, tenant_in)
    return success(data=schemas.Tenant.model_validate(tenant).model_dump(mode="json"))

@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """删除租户 (软删除)"""
    await tenant_service.delete_tenant(tenant_id)
    return success(message="删除成功")
