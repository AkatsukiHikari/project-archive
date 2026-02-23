from typing import List
from fastapi import APIRouter, Depends, status
from app.modules.iam import schemas
from app.modules.iam.api.dependencies import get_tenant_service, get_current_user
from app.modules.iam.services.tenant_service import TenantService
from app.modules.iam.models import User
import uuid

router = APIRouter()

@router.get("/", response_model=List[schemas.Tenant])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """获取所有租户列表"""
    return await tenant_service.get_tenants(skip=skip, limit=limit)

@router.get("/{tenant_id}", response_model=schemas.Tenant)
async def get_tenant(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """获取指定租户详情"""
    return await tenant_service.get_tenant(tenant_id)

@router.post("/", response_model=schemas.Tenant, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_in: schemas.TenantCreate,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """创建新租户"""
    return await tenant_service.create_tenant(tenant_in)

@router.put("/{tenant_id}", response_model=schemas.Tenant)
async def update_tenant(
    tenant_id: uuid.UUID,
    tenant_in: schemas.TenantUpdate,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """更新租户信息"""
    return await tenant_service.update_tenant(tenant_id, tenant_in)

@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """删除租户 (软删除)"""
    await tenant_service.delete_tenant(tenant_id)
