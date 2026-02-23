from abc import ABC, abstractmethod
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.iam.models import Organization
from app.modules.iam import schemas
import uuid

class OrganizationRepository(ABC):
    @abstractmethod
    async def get_by_id(self, org_id: uuid.UUID) -> Optional[Organization]:
        pass

    @abstractmethod
    async def get_by_tenant(self, tenant_id: uuid.UUID) -> List[Organization]:
        pass

    @abstractmethod
    async def create(self, org_in: schemas.OrganizationCreate) -> Organization:
        pass

    @abstractmethod
    async def update(self, org: Organization, org_in: schemas.OrganizationUpdate) -> Organization:
        pass

    @abstractmethod
    async def delete(self, org_id: uuid.UUID) -> bool:
        pass


class SQLAlchemyOrganizationRepository(OrganizationRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, org_id: uuid.UUID) -> Optional[Organization]:
        result = await self.db.execute(select(Organization).where(Organization.id == org_id, Organization.is_deleted == False))
        return result.scalars().first()

    async def get_by_tenant(self, tenant_id: uuid.UUID) -> List[Organization]:
        result = await self.db.execute(
            select(Organization)
            .where(Organization.tenant_id == tenant_id, Organization.is_deleted == False)
            .order_by(Organization.sort_order)
        )
        return list(result.scalars().all())

    async def create(self, org_in: schemas.OrganizationCreate) -> Organization:
        db_org = Organization(
            tenant_id=org_in.tenant_id,
            parent_id=org_in.parent_id,
            name=org_in.name,
            code=org_in.code,
            sort_order=org_in.sort_order
        )
        self.db.add(db_org)
        await self.db.commit()
        await self.db.refresh(db_org)
        return db_org

    async def update(self, org: Organization, org_in: schemas.OrganizationUpdate) -> Organization:
        update_data = org_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(org, field, value)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def delete(self, org_id: uuid.UUID) -> bool:
        org = await self.get_by_id(org_id)
        if org:
            org.is_deleted = True
            await self.db.commit()
            return True
        return False
