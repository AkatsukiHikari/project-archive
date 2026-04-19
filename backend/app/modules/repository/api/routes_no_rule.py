import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import ResponseModel, success
from app.infra.db.session import get_db
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models.user import User
from app.modules.repository.schemas.no_rule import (
    NoRuleCreate,
    NoRuleRead,
    NoRuleUpdate,
    PreviewRequest,
    PreviewResponse,
)
from app.modules.repository.services.no_rule_engine import ArchiveNoEngine
from app.modules.repository.services.no_rule_service import NoRuleService

router = APIRouter(prefix="/archive/no-rules", tags=["档号规则"])


@router.get("", response_model=ResponseModel[list[NoRuleRead]])
async def list_no_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    items = await svc.list_all(tenant_id=current_user.tenant_id)
    return success([NoRuleRead.model_validate(i) for i in items])


@router.post("", response_model=ResponseModel[NoRuleRead])
async def create_no_rule(
    data: NoRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    item = await svc.create(data, tenant_id=current_user.tenant_id)
    await db.commit()
    return success(NoRuleRead.model_validate(item))


@router.get("/{rule_id}", response_model=ResponseModel[NoRuleRead])
async def get_no_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    item = await svc.get(rule_id, tenant_id=current_user.tenant_id)
    return success(NoRuleRead.model_validate(item))


@router.put("/{rule_id}", response_model=ResponseModel[NoRuleRead])
async def update_no_rule(
    rule_id: uuid.UUID,
    data: NoRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    item = await svc.update(rule_id, data)
    await db.commit()
    return success(NoRuleRead.model_validate(item))


@router.delete("/{rule_id}", response_model=ResponseModel[None])
async def delete_no_rule(
    rule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    svc = NoRuleService(db)
    await svc.delete(rule_id)
    await db.commit()
    return success()


@router.post("/{rule_id}/preview", response_model=ResponseModel[PreviewResponse])
async def preview_no_rule(
    rule_id: uuid.UUID,
    req: PreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """用样本数据预览生成档号，不写 DB。"""
    svc = NoRuleService(db)
    rule = await svc.get(rule_id, tenant_id=current_user.tenant_id)
    engine = ArchiveNoEngine(db)
    archive_no, parts = await engine.preview(rule, req.model_dump(exclude_none=True))
    return success(PreviewResponse(archive_no=archive_no, segments=parts))
