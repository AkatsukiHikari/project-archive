from typing import List, Callable
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.modules.iam.models.user import User, Role
from app.modules.iam.models.permission import Menu, role_menu_association
from app.modules.iam.api.dependencies import get_current_user
from app.infra.db.session import get_db

def require_permissions(*permissions: str) -> Callable:
    """
    RBAC 权限校验依赖。
    检查当前登录用户是否具备指定的全部权限。
    如果用户所在角色具备 superadmin 或包含了目标权限点，则放行。
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        # 超级管理员字段放行（不依赖用户名硬编码）
        if current_user.is_superadmin:
            return current_user

        user_roles = [role.code for role in current_user.roles] if hasattr(current_user, 'roles') else []

        # 具备 superadmin 角色的用户一票放行
        if "superadmin" in user_roles:
            return current_user
            
        if not user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="尚未分配任何角色，禁止访问核心资源"
            )
            
        # 查库获取当前用户关联的所有角色拥有的细粒度 Menu Code
        role_ids = [r.id for r in current_user.roles]
        stmt = (
            select(Menu.code)
            .join(role_menu_association, Menu.id == role_menu_association.c.menu_id)
            .where(role_menu_association.c.role_id.in_(role_ids))
            .where(Menu.code.is_not(None))
        )
        
        result = await db.execute(stmt)
        user_permissions = set(result.scalars().all())
        
        for req_perm in permissions:
            if req_perm not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"权限不足，需要权限节点: {req_perm}"
                )
                
        return current_user

    return permission_checker
