from typing import List, Optional
from fastapi import HTTPException
from app.modules.iam import schemas
from app.modules.iam.repositories.tenant_repository import TenantRepository
from app.modules.iam.models import Tenant
import uuid

class TenantService:
    def __init__(self, tenant_repo: TenantRepository):
        self.tenant_repo = tenant_repo

    async def get_tenant(self, tenant_id: uuid.UUID) -> Tenant:
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="租户不存在")
        return tenant

    async def get_tenants(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        return await self.tenant_repo.get_all(skip=skip, limit=limit)

    async def create_tenant(self, tenant_in: schemas.TenantCreate) -> Tenant:
        existing = await self.tenant_repo.get_by_code(tenant_in.code)
        if existing:
            raise HTTPException(status_code=400, detail="租户编码已存在")
        return await self.tenant_repo.create(tenant_in)

    async def update_tenant(self, tenant_id: uuid.UUID, tenant_in: schemas.TenantUpdate) -> Tenant:
        tenant = await self.get_tenant(tenant_id)
        return await self.tenant_repo.update(tenant, tenant_in)

    async def delete_tenant(self, tenant_id: uuid.UUID) -> bool:
        tenant = await self.get_tenant(tenant_id)
        return await self.tenant_repo.delete(tenant.id)
