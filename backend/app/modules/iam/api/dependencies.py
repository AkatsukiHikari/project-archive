from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import uuid
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.infra.db.session import get_db
from app.modules.iam import models, schemas
from app.modules.iam.repositories.iam_repository import SQLAlchemyIAMRepository
from app.modules.iam.repositories.role_repository import SQLAlchemyRoleRepository
from app.modules.iam.repositories.tenant_repository import SQLAlchemyTenantRepository
from app.modules.iam.repositories.org_repository import SQLAlchemyOrganizationRepository
from app.modules.iam.repositories.menu_repository import SQLAlchemyMenuRepository

from app.modules.iam.services.iam_service import IAMService
from app.modules.iam.services.role_service import RoleService
from app.modules.iam.services.tenant_service import TenantService
from app.modules.iam.services.org_service import OrganizationService
from app.modules.iam.services.menu_service import MenuService

from app.core.security.token import ALGORITHM
from app.common.exceptions.base import AuthenticationException
from app.common.error_code import ErrorCode


# ---------------------------------------------------------------------------
# IAM 模块统一依赖注入入口
# ---------------------------------------------------------------------------

def get_iam_service(db: AsyncSession = Depends(get_db)) -> IAMService:
    repo = SQLAlchemyIAMRepository(db)
    role_repo = SQLAlchemyRoleRepository(db)
    return IAMService(repo, role_repo)

def get_role_service(db: AsyncSession = Depends(get_db)) -> RoleService:
    role_repo = SQLAlchemyRoleRepository(db)
    menu_repo = SQLAlchemyMenuRepository(db)
    return RoleService(role_repo, menu_repo)

def get_tenant_service(db: AsyncSession = Depends(get_db)) -> TenantService:
    repo = SQLAlchemyTenantRepository(db)
    return TenantService(repo)

def get_org_service(db: AsyncSession = Depends(get_db)) -> OrganizationService:
    repo = SQLAlchemyOrganizationRepository(db)
    return OrganizationService(repo)

def get_menu_service(db: AsyncSession = Depends(get_db)) -> MenuService:
    repo = SQLAlchemyMenuRepository(db)
    return MenuService(repo)


reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


async def get_current_user(
    token: Annotated[str, Depends(reusable_oauth2)],
    service: Annotated[IAMService, Depends(get_iam_service)],
) -> models.User:
    """从 JWT Token 解析当前登录用户"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthenticationException(
                code=ErrorCode.INVALID_TOKEN,
                message="无效的认证凭证",
            )
        token_data = schemas.TokenPayload(sub=user_id)
    except (jwt.PyJWTError, ValidationError):
        raise AuthenticationException(
            code=ErrorCode.INVALID_TOKEN,
            message="无效的认证凭证",
        )

    try:
        user_uuid = uuid.UUID(token_data.sub)
    except ValueError:
        raise AuthenticationException(
            code=ErrorCode.INVALID_TOKEN,
            message="无效的认证凭证格式",
        )

    user = await service.get_user_by_id(user_uuid)
    if not user:
        raise AuthenticationException(
            code=ErrorCode.USER_NOT_FOUND,
            message="用户不存在",
        )
    if not user.is_active:
        raise AuthenticationException(
            code=ErrorCode.USER_INACTIVE,
            message="用户已被禁用",
        )
    return user
