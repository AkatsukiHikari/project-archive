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

    async def register_user(self, user_in: schemas.UserCreate, created_by: Optional[uuid.UUID] = None) -> User:
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
        return await self.repository.create(user_in, hashed_pw, roles=roles, created_by=created_by)
        
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

        return await self.repository.save(user)

    async def upload_avatar(self, user_id: uuid.UUID, file: "UploadFile") -> str:
        """统一处理头像上传校验、流式存储、以及更新数据库"""
        from fastapi import status, UploadFile
        from app.infra.storage.factory import storage
        from app.infra.storage.adapter import StorageAdapter
        import os
        
        # 1. 校验类型
        allowed_content_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
        if file.content_type not in allowed_content_types:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="仅支持 JPG / PNG / WEBP / GIF 格式图片"
            )

        # 2. 校验大小（通过底层 spooled 也可以设置，这里简单 read 然后 seek）
        # 如果是极大的文件，FastAPI 在 UploadFile 里已经 spooled 到磁盘
        # 为了避免全量进内存，可以用 file.file 读取再重置指针
        # 这里仅做简单演示，生产级通常在 Nginx 层和 FastAPI Header 限制
        # FastAPI 默认情况下通过 UploadFile 会放入临时文件
        MAX_SIZE = 5 * 1024 * 1024
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)
        if file_size > MAX_SIZE:
             raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="头像文件不得超过 5MB"
            )

        # 3. 构建唯一对象键
        object_key = StorageAdapter.generate_object_key(str(user_id), file.filename)
        bucket = "avatars"

        # 4. 流式保存（同步 I/O 放入线程池，避免阻塞事件循环）
        import asyncio
        await asyncio.to_thread(
            storage.save,
            file_object=file.file,
            filename=object_key,
            bucket=bucket,
            content_type=file.content_type or "image/jpeg",
        )

        # 5. 生成永久公开 URL 并更新数据库
        avatar_url = storage.get_public_url(filename=object_key, bucket=bucket)

        user = await self.repository.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        user.avatar = avatar_url
        await self.repository.save(user)

        return avatar_url

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
        await self.repository.save(user)
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

    async def get_user_permissions(self, user_id: uuid.UUID) -> List[str]:
        """获取用户当前拥有的全部权限标识 (Menu code)"""
        from sqlalchemy import select
        from app.modules.iam.models.permission import Menu, role_menu_association
        from app.modules.iam.models.user import user_role_association

        stmt = (
            select(Menu.code)
            .join(role_menu_association, Menu.id == role_menu_association.c.menu_id)
            .join(user_role_association, role_menu_association.c.role_id == user_role_association.c.role_id)
            .where(user_role_association.c.user_id == user_id)
            .where(Menu.code.is_not(None))
        )
        
        result = await self.repository.db.execute(stmt)
        return list(set(result.scalars().all()))
