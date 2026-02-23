from abc import ABC, abstractmethod
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.iam.models import Tenant
from app.modules.iam import schemas
import uuid

class TenantRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        pass

    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[Tenant]:
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        pass

    @abstractmethod
    async def create(self, tenant_in: schemas.TenantCreate) -> Tenant:
        pass

    @abstractmethod
    async def update(self, tenant: Tenant, tenant_in: schemas.TenantUpdate) -> Tenant:
        pass

    @abstractmethod
    async def delete(self, tenant_id: uuid.UUID) -> bool:
        pass


class SQLAlchemyTenantRepository(TenantRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, tenant_id: uuid.UUID) -> Optional[Tenant]:
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False))
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[Tenant]:
        result = await self.db.execute(select(Tenant).where(Tenant.code == code, Tenant.is_deleted == False))
        return result.scalars().first()

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        result = await self.db.execute(select(Tenant).where(Tenant.is_deleted == False).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, tenant_in: schemas.TenantCreate) -> Tenant:
        db_tenant = Tenant(
            code=tenant_in.code,
            name=tenant_in.name,
            description=tenant_in.description,
            is_active=tenant_in.is_active
        )
        self.db.add(db_tenant)
        await self.db.commit()
        await self.db.refresh(db_tenant)
        return db_tenant

    async def update(self, tenant: Tenant, tenant_in: schemas.TenantUpdate) -> Tenant:
        update_data = tenant_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def delete(self, tenant_id: uuid.UUID) -> bool:
        tenant = await self.get_by_id(tenant_id)
        if tenant:
            tenant.is_deleted = True
            await self.db.commit()
            return True
        return False
