from abc import ABC, abstractmethod
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.modules.iam.models import Role, Menu
from app.modules.iam import schemas
import uuid

class RoleRepository(ABC):
    @abstractmethod
    async def get_by_id(self, role_id: uuid.UUID) -> Optional[Role]:
        pass

    @abstractmethod
    async def get_by_code(self, code: str) -> Optional[Role]:
        pass

    @abstractmethod
    async def get_all(self, tenant_id: Optional[uuid.UUID] = None) -> List[Role]:
        pass

    @abstractmethod
    async def create(self, role_in: schemas.RoleCreate, menus: List[Menu] = None) -> Role:
        pass

    @abstractmethod
    async def update(self, role: Role, role_in: schemas.RoleUpdate, menus: List[Menu] = None) -> Role:
        pass

    @abstractmethod
    async def delete(self, role_id: uuid.UUID) -> bool:
        pass


class SQLAlchemyRoleRepository(RoleRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, role_id: uuid.UUID) -> Optional[Role]:
        result = await self.db.execute(
            select(Role).options(selectinload(Role.menus)).where(Role.id == role_id, Role.is_deleted == False)
        )
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[Role]:
        result = await self.db.execute(
            select(Role).options(selectinload(Role.menus)).where(Role.code == code, Role.is_deleted == False)
        )
        return result.scalars().first()

    async def get_all(self, tenant_id: Optional[uuid.UUID] = None) -> List[Role]:
        stmt = select(Role).where(Role.is_deleted == False)
        if tenant_id:
            stmt = stmt.where(Role.tenant_id == tenant_id)
        result = await self.db.execute(stmt.options(selectinload(Role.menus)))
        return list(result.scalars().all())

    async def create(self, role_in: schemas.RoleCreate, menus: List[Menu] = None) -> Role:
        db_role = Role(
            name=role_in.name,
            code=role_in.code,
            description=role_in.description,
            tenant_id=role_in.tenant_id
        )
        if menus is not None:
            db_role.menus = menus
            
        self.db.add(db_role)
        await self.db.commit()
        await self.db.refresh(db_role)
        return db_role

    async def update(self, role: Role, role_in: schemas.RoleUpdate, menus: List[Menu] = None) -> Role:
        update_data = role_in.model_dump(exclude_unset=True, exclude={"menu_ids"})
        for field, value in update_data.items():
            setattr(role, field, value)
            
        if menus is not None:
            role.menus = menus
            
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def delete(self, role_id: uuid.UUID) -> bool:
        role = await self.get_by_id(role_id)
        if role:
            role.is_deleted = True
            await self.db.commit()
            return True
        return False
