from typing import List, Optional
from fastapi import HTTPException
from app.modules.iam import schemas
from app.modules.iam.repositories.role_repository import RoleRepository
from app.modules.iam.repositories.menu_repository import MenuRepository
from app.modules.iam.models import Role
import uuid

class RoleService:
    def __init__(self, role_repo: RoleRepository, menu_repo: MenuRepository):
        self.role_repo = role_repo
        self.menu_repo = menu_repo

    async def get_role(self, role_id: uuid.UUID) -> Role:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        return role

    async def get_roles(self, tenant_id: Optional[uuid.UUID] = None) -> List[Role]:
        return await self.role_repo.get_all(tenant_id=tenant_id)

    async def create_role(self, role_in: schemas.RoleCreate) -> Role:
        existing = await self.role_repo.get_by_code(role_in.code)
        if existing:
            raise HTTPException(status_code=400, detail="角色编码已存在")
            
        menus = []
        if role_in.menu_ids:
            for menu_id in role_in.menu_ids:
                menu = await self.menu_repo.get_by_id(menu_id)
                if not menu:
                    raise HTTPException(status_code=400, detail=f"菜单/权限ID {menu_id} 不存在")
                menus.append(menu)
                
        return await self.role_repo.create(role_in, menus=menus)

    async def update_role(self, role_id: uuid.UUID, role_in: schemas.RoleUpdate) -> Role:
        role = await self.get_role(role_id)
        
        if role_in.code and role_in.code != role.code:
            existing = await self.role_repo.get_by_code(role_in.code)
            if existing:
                raise HTTPException(status_code=400, detail="角色编码已存在")
        
        menus = None
        if role_in.menu_ids is not None:
            menus = []
            for menu_id in role_in.menu_ids:
                menu = await self.menu_repo.get_by_id(menu_id)
                if not menu:
                    raise HTTPException(status_code=400, detail=f"菜单/权限ID {menu_id} 不存在")
                menus.append(menu)
                
        return await self.role_repo.update(role, role_in, menus=menus)

    async def delete_role(self, role_id: uuid.UUID) -> bool:
        role = await self.get_role(role_id)
        return await self.role_repo.delete(role.id)
