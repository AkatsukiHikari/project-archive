from abc import ABC, abstractmethod
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.audit.models import AuditLog
from app.modules.audit import schemas
import uuid

class AuditRepository(ABC):
    @abstractmethod
    async def get_by_id(self, log_id: uuid.UUID) -> Optional[AuditLog]:
        pass

    @abstractmethod
    async def get_all(self, tenant_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        pass

    @abstractmethod
    async def create(self, log_in: schemas.AuditLogCreate) -> AuditLog:
        pass


class SQLAlchemyAuditRepository(AuditRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, log_id: uuid.UUID) -> Optional[AuditLog]:
        result = await self.db.execute(select(AuditLog).where(AuditLog.id == log_id))
        return result.scalars().first()

    async def get_all(self, tenant_id: Optional[uuid.UUID] = None, user_id: Optional[uuid.UUID] = None, skip: int = 0, limit: int = 100) -> List[AuditLog]:
        stmt = select(AuditLog)
        if tenant_id:
            stmt = stmt.where(AuditLog.tenant_id == tenant_id)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        
        result = await self.db.execute(stmt.order_by(AuditLog.create_time.desc()).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, log_in: schemas.AuditLogCreate) -> AuditLog:
        db_log = AuditLog(
            user_id=log_in.user_id,
            tenant_id=log_in.tenant_id,
            action=log_in.action,
            module=log_in.module,
            ip_address=log_in.ip_address,
            user_agent=log_in.user_agent,
            status=log_in.status,
            details=log_in.details,
            error_message=log_in.error_message
        )
        self.db.add(db_log)
        await self.db.commit()
        await self.db.refresh(db_log)
        return db_log
