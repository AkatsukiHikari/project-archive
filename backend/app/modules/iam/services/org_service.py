from typing import List, Optional
from fastapi import HTTPException
from app.modules.iam import schemas
from app.modules.iam.repositories.org_repository import OrganizationRepository
from app.modules.iam.models import Organization
import uuid

class OrganizationService:
    def __init__(self, org_repo: OrganizationRepository):
        self.org_repo = org_repo

    async def get_org(self, org_id: uuid.UUID) -> Organization:
        org = await self.org_repo.get_by_id(org_id)
        if not org:
            raise HTTPException(status_code=404, detail="组织不存在")
        return org

    async def get_org_tree(self, tenant_id: uuid.UUID) -> List[schemas.OrganizationTree]:
        orgs = await self.org_repo.get_by_tenant(tenant_id)
        
        # Build tree
        org_dict = {org.id: schemas.OrganizationTree.model_validate(org) for org in orgs}
        root_nodes = []
        
        for org in orgs:
            if org.parent_id and org.parent_id in org_dict:
                org_dict[org.parent_id].children.append(org_dict[org.id])
            else:
                root_nodes.append(org_dict[org.id])
                
        return root_nodes

    async def create_org(self, org_in: schemas.OrganizationCreate) -> Organization:
        if org_in.parent_id:
            parent = await self.org_repo.get_by_id(org_in.parent_id)
            if not parent or parent.tenant_id != org_in.tenant_id:
                raise HTTPException(status_code=400, detail="无效的父级组织")
        return await self.org_repo.create(org_in)

    async def update_org(self, org_id: uuid.UUID, org_in: schemas.OrganizationUpdate) -> Organization:
        org = await self.get_org(org_id)
        
        if org_in.parent_id:
            parent = await self.org_repo.get_by_id(org_in.parent_id)
            if not parent or parent.tenant_id != org.tenant_id:
                raise HTTPException(status_code=400, detail="无效的父级组织")
            # Prevent circular dependency (not fully implemented here, requires deep check)
            if org_in.parent_id == org.id:
                raise HTTPException(status_code=400, detail="不能将自己设为父组织")
                
        return await self.org_repo.update(org, org_in)

    async def delete_org(self, org_id: uuid.UUID) -> bool:
        org = await self.get_org(org_id)
        # Prevent deletion if it has children -> In a real app we'd query for children
        # For now, cascade deletion is handled by DB if configured, but soft-delete requires manual handling
        return await self.org_repo.delete(org.id)
