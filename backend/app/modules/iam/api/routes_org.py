from typing import List
from fastapi import APIRouter, Depends, status
from app.modules.iam import schemas
from app.modules.iam.api.dependencies import get_org_service, get_current_user
from app.modules.iam.services.org_service import OrganizationService
from app.modules.iam.models import User
from app.common.response import success, ResponseModel
import uuid

router = APIRouter()

@router.get(
    "/tree",
    response_model=ResponseModel[List[schemas.OrganizationTree]],
    summary="获取组织架构树",
    response_description="该租户下所有组织的树状层级结构"
)
async def get_org_tree(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """获取组织架构树"""
    tree = await org_service.get_org_tree(tenant_id)
    return success(data=[schemas.OrganizationTree.model_validate(o).model_dump(mode="json") for o in tree])

@router.get(
    "/{org_id}",
    response_model=ResponseModel[schemas.Organization],
    summary="获取指定组织详情",
    response_description="单条组织机构的表单信息"
)
async def get_org(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """获取指定组织详情"""
    org = await org_service.get_org(org_id)
    return success(data=schemas.Organization.model_validate(org).model_dump(mode="json"))

@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseModel[schemas.Organization],
    summary="创建新组织",
    response_description="创建成功后的组织属性"
)
async def create_org(
    org_in: schemas.OrganizationCreate,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """创建新组织"""
    org = await org_service.create_org(org_in)
    return success(data=schemas.Organization.model_validate(org).model_dump(mode="json"))

@router.put(
    "/{org_id}",
    response_model=ResponseModel[schemas.Organization],
    summary="更新组织信息",
    response_description="更新成功后的组织记录"
)
async def update_org(
    org_id: uuid.UUID,
    org_in: schemas.OrganizationUpdate,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """更新组织信息"""
    org = await org_service.update_org(org_id, org_in)
    return success(data=schemas.Organization.model_validate(org).model_dump(mode="json"))

@router.delete(
    "/{org_id}",
    response_model=ResponseModel[None],
    summary="删除组织",
    response_description="成功或失败的提示"
)
async def delete_org(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_org_service)
):
    """删除组织 (软删除)"""
    await org_service.delete_org(org_id)
    return success(message="删除成功")
