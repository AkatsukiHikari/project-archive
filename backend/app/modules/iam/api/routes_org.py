from typing import List
from fastapi import APIRouter, Depends, status
from app.modules.iam import schemas
from app.modules.iam.api.dependencies import get_org_service, get_current_user
from app.modules.iam.services.org_service import OrganizationService
from app.modules.iam.models import User
import uuid

router = APIRouter()

@router.get("/tree", response_model=List[schemas.OrganizationTree])
async def get_org_tree(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """获取组织架构树"""
    return await org_service.get_org_tree(tenant_id)

@router.get("/{org_id}", response_model=schemas.Organization)
async def get_org(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """获取指定组织详情"""
    return await org_service.get_org(org_id)

@router.post("/", response_model=schemas.Organization, status_code=status.HTTP_201_CREATED)
async def create_org(
    org_in: schemas.OrganizationCreate,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """创建新组织"""
    return await org_service.create_org(org_in)

@router.put("/{org_id}", response_model=schemas.Organization)
async def update_org(
    org_id: uuid.UUID,
    org_in: schemas.OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """更新组织信息"""
    return await org_service.update_org(org_id, org_in)

@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """删除组织 (软删除)"""
    await org_service.delete_org(org_id)
