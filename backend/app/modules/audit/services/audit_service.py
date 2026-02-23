from typing import List, Optional
from app.modules.audit import schemas
from app.modules.audit.repositories.audit_repository import AuditRepository
from app.modules.audit.models import AuditLog
import uuid

class AuditService:
    def __init__(self, audit_repo: AuditRepository):
        self.audit_repo = audit_repo

    async def get_audit_log(self, log_id: uuid.UUID) -> Optional[AuditLog]:
        return await self.audit_repo.get_by_id(log_id)

    async def get_audit_logs(
        self, 
        tenant_id: Optional[uuid.UUID] = None, 
        user_id: Optional[uuid.UUID] = None, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[AuditLog]:
        return await self.audit_repo.get_all(tenant_id=tenant_id, user_id=user_id, skip=skip, limit=limit)

    async def create_audit_log(self, log_in: schemas.AuditLogCreate) -> AuditLog:
        return await self.audit_repo.create(log_in)
