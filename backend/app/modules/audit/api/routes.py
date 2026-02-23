from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.modules.audit import schemas
from app.modules.audit.services.audit_service import AuditService
# Use `get_current_user` from IAM module to verify session
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models import User
from app.infra.db.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.audit.repositories.audit_repository import SQLAlchemyAuditRepository
import uuid

def get_audit_service(db: AsyncSession = Depends(get_db)):
    repo = SQLAlchemyAuditRepository(db)
    return AuditService(repo)

router = APIRouter()

@router.get("/", response_model=List[schemas.AuditLog])
async def list_audit_logs(
    tenant_id: Optional[uuid.UUID] = Query(None, description="按租户过滤"),
    user_id: Optional[uuid.UUID] = Query(None, description="按用户过滤"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """获取检索审计日志"""
    return await audit_service.get_audit_logs(tenant_id=tenant_id, user_id=user_id, skip=skip, limit=limit)

@router.post("/", response_model=schemas.AuditLog)
async def create_audit_log(
    log_in: schemas.AuditLogCreate,
    # Normally this endpoint would be restricted to internal system usage or authorized services
    # current_user: User = Depends(get_current_user),
    audit_service: AuditService = Depends(get_audit_service)
):
    """创建审计日志 (供给内部微服务或其它模块调用)"""
    return await audit_service.create_audit_log(log_in)
