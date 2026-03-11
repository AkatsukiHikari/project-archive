from typing import Optional, List
from app.modules.iam.models import User
from app.modules.iam import schemas
from app.modules.iam.repositories.iam_repository import IAMRepository
from app.modules.iam.repositories.role_repository import RoleRepository
from app.core.security.password import verify_password, get_password_hash
from app.common.exceptions.base import ValidationException
from app.common.error_code import ErrorCode
from fastapi import HTTPException
import uuid


class IAMService:
    """
    [Service Layer] IAM 业务逻辑
    """

    def __init__(self, repository: IAMRepository, role_repo: RoleRepository = None):
        self.repository = repository
        self.role_repo = role_repo

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """验证用户名密码，返回 User 或 None"""
        user = await self.repository.get_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
        
    async def get_users(self, tenant_id: Optional[uuid.UUID] = None, org_id: Optional[uuid.UUID] = None) -> List[User]:
        return await self.repository.get_all(tenant_id=tenant_id, org_id=org_id)

    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return await self.repository.get_by_id(user_id)

    async def register_user(self, user_in: schemas.UserCreate) -> User:
        """注册新用户，用户名重复则抛 ValidationException"""
        existing_user = await self.repository.get_by_username(user_in.username)
        if existing_user:
            raise ValidationException(
                code=ErrorCode.USERNAME_EXISTS,
                message="用户名已存在",
            )
            
        roles = []
        if user_in.role_ids and self.role_repo:
            for rid in user_in.role_ids:
                role = await self.role_repo.get_by_id(rid)
                if role:
                    roles.append(role)

        hashed_pw = get_password_hash(user_in.password)
        return await self.repository.create(user_in, hashed_pw, roles=roles)
        
    async def update_user(self, user_id: uuid.UUID, user_in: schemas.UserUpdate) -> User:
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
            
        if user_in.password:
            user.hashed_password = get_password_hash(user_in.password)
            
        roles = None
        if user_in.role_ids is not None and self.role_repo:
            roles = []
            for rid in user_in.role_ids:
                role = await self.role_repo.get_by_id(rid)
                if role:
                    roles.append(role)
                    
        return await self.repository.update(user, user_in, roles=roles)

    async def update_user_profile(self, user_id: uuid.UUID, profile_in: schemas.UserProfileUpdate) -> User:
        """用户自行修改个人资料"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
            
        # Manually set fields to avoid a full UserUpdate
        update_data = profile_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
            
        await self.repository.db.commit()
        await self.repository.db.refresh(user)
        return user

    async def update_user_avatar(self, user_id: uuid.UUID, avatar_url: str) -> User:
        """更新用户头像 URL"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user.avatar = avatar_url
        await self.repository.db.commit()
        await self.repository.db.refresh(user)
        return user

    async def update_user_password(self, user_id: uuid.UUID, password_in: schemas.UserPasswordUpdate) -> bool:
        """用户自行修改密码"""
        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
            
        if not verify_password(password_in.old_password, user.hashed_password):
            raise ValidationException(
                code=ErrorCode.INVALID_PASSWORD,
                message="旧密码错误",
            )
            
        user.hashed_password = get_password_hash(password_in.new_password)
        await self.repository.db.commit()
        return True

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        user = await self.repository.get_by_id(user_id)
        if user:
            user.is_deleted = True
            await self.repository.db.commit()
            return True
        return False

    async def get_user(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        return await self.repository.get_by_username(username)
