from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.modules.audit import schemas
from app.modules.audit.services.audit_service import AuditService
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models import User
from app.infra.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.repositories.audit_repository import SQLAlchemyAuditRepository
from app.common.response import success
import uuid


def get_audit_service(db: AsyncSession = Depends(get_db)) -> AuditService:
    repo = SQLAlchemyAuditRepository(db)
    return AuditService(repo)


router = APIRouter()


@router.get("")
async def list_audit_logs(
    tenant_id: Optional[uuid.UUID] = Query(None, description="按租户过滤"),
    user_id: Optional[uuid.UUID] = Query(None, description="按用户过滤"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """获取审计日志列表（管理员视图）"""
    logs = await audit_service.get_audit_logs(
        tenant_id=tenant_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )
    return success(data=[schemas.AuditLog.model_validate(log).model_dump(mode="json") for log in logs])


@router.get("/me")
async def list_my_audit_logs(
    skip: int = Query(0, ge=0, description="跳过条数"),
    limit: int = Query(20, ge=1, le=100, description="每页条数"),
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """获取当前登录用户自己的操作日志"""
    logs = await audit_service.get_audit_logs(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    return success(data=[schemas.AuditLog.model_validate(log).model_dump(mode="json") for log in logs])


@router.post("")
async def create_audit_log(
    log_in: schemas.AuditLogCreate,
    audit_service: AuditService = Depends(get_audit_service)
):
    """创建审计日志（内部服务调用）"""
    log = await audit_service.create_audit_log(log_in)
    return success(data=schemas.AuditLog.model_validate(log).model_dump(mode="json"))
