from typing import List
from fastapi import APIRouter, Depends, status
from app.modules.iam import schemas
from app.modules.iam.api.dependencies import get_org_service, get_current_user
from app.modules.iam.services.org_service import OrganizationService
from app.modules.iam.models import User
from app.common.response import success
import uuid

router = APIRouter()

@router.get("/tree")
async def get_org_tree(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """获取组织架构树"""
    tree = await org_service.get_org_tree(tenant_id)
    return success(data=[schemas.OrganizationTree.model_validate(o).model_dump(mode="json") for o in tree])

@router.get("/{org_id}")
async def get_org(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """获取指定组织详情"""
    org = await org_service.get_org(org_id)
    return success(data=schemas.Organization.model_validate(org).model_dump(mode="json"))

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_org(
    org_in: schemas.OrganizationCreate,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """创建新组织"""
    org = await org_service.create_org(org_in)
    return success(data=schemas.Organization.model_validate(org).model_dump(mode="json"))

@router.put("/{org_id}")
async def update_org(
    org_id: uuid.UUID,
    org_in: schemas.OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """更新组织信息"""
    org = await org_service.update_org(org_id, org_in)
    return success(data=schemas.Organization.model_validate(org).model_dump(mode="json"))

@router.delete("/{org_id}")
async def delete_org(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """删除组织 (软删除)"""
    await org_service.delete_org(org_id)
    return success(message="删除成功")
