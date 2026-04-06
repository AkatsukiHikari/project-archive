from abc import ABC, abstractmethod
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.modules.iam.models import User, Role
from app.modules.iam import schemas
import uuid

class IAMRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_all(self, tenant_id: Optional[uuid.UUID] = None, org_id: Optional[uuid.UUID] = None) -> List[User]:
        pass

    @abstractmethod
    async def create(self, user_create: schemas.UserCreate, hashed_password: str, roles: List[Role] = None, created_by: uuid.UUID = None) -> User:
        pass

    @abstractmethod
    async def update(self, user: User, user_update: schemas.UserUpdate, roles: List[Role] = None) -> User:
        pass

    @abstractmethod
    async def save(self, user: User) -> User:
        """将已修改的 User 对象持久化（commit + refresh）"""
        pass


class SQLAlchemyIAMRepository(IAMRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.menus))
            .where(User.id == user_id, User.is_deleted == False)
        )
        return result.scalars().first()

    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.menus))
            .where(User.username == username, User.is_deleted == False)
        )
        return result.scalars().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).options(selectinload(User.roles)).where(User.email == email, User.is_deleted == False)
        )
        return result.scalars().first()

    async def get_all(self, tenant_id: Optional[uuid.UUID] = None, org_id: Optional[uuid.UUID] = None) -> List[User]:
        stmt = select(User).options(selectinload(User.roles)).where(User.is_deleted == False)
        if tenant_id:
            stmt = stmt.where(User.tenant_id == tenant_id)
        if org_id:
            stmt = stmt.where(User.org_id == org_id)
        result = await self.db.execute(stmt.order_by(User.create_time.desc()))
        return list(result.scalars().all())

    async def create(self, user_create: schemas.UserCreate, hashed_password: str, roles: List[Role] = None, created_by: uuid.UUID = None) -> User:
        db_user = User(
            username=user_create.username,
            email=user_create.email,
            full_name=user_create.full_name,
            hashed_password=hashed_password,
            is_active=user_create.is_active,
            tenant_id=user_create.tenant_id,
            org_id=user_create.org_id,
            create_by=created_by,
        )
        if roles is not None:
            db_user.roles = roles
        self.db.add(db_user)
        await self.db.commit()
        await self.db.refresh(db_user)
        return db_user

    async def update(self, user: User, user_update: schemas.UserUpdate, roles: List[Role] = None) -> User:
        update_data = user_update.model_dump(exclude_unset=True, exclude={"password", "role_ids"})
        for field, value in update_data.items():
            setattr(user, field, value)

        if roles is not None:
            user.roles = roles

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def save(self, user: User) -> User:
        await self.db.commit()
        await self.db.refresh(user)
        return user
