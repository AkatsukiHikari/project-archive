"""
管理后台统计 API

端点：
- GET /v1/stats/dashboard — 仪表盘摘要数据
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.infra.db.session import get_db
from app.modules.iam.models.user import User
from app.modules.iam.models.tenant import Tenant
from app.modules.iam.api.dependencies import get_current_user
from app.common.response import success, ResponseModel
from pydantic import BaseModel

router = APIRouter()


class DashboardStats(BaseModel):
    active_tenants: int
    total_users: int
    active_users: int
    pending_sips: int


@router.get(
    "/dashboard",
    response_model=ResponseModel[DashboardStats],
    summary="获取仪表盘统计数据",
)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """返回管理后台首页所需的摘要统计数据"""
    # 活跃租户数
    tenant_count_result = await db.execute(
        select(func.count()).select_from(Tenant).where(
            Tenant.is_deleted == False,
            Tenant.is_active == True,
        )
    )
    active_tenants = tenant_count_result.scalar_one()

    # 用户总数 / 活跃用户数（仅限当前租户，超管看全部）
    user_stmt = select(func.count()).select_from(User).where(User.is_deleted == False)
    active_user_stmt = select(func.count()).select_from(User).where(
        User.is_deleted == False, User.is_active == True
    )
    if not current_user.is_superadmin and current_user.tenant_id:
        user_stmt = user_stmt.where(User.tenant_id == current_user.tenant_id)
        active_user_stmt = active_user_stmt.where(User.tenant_id == current_user.tenant_id)

    total_users = (await db.execute(user_stmt)).scalar_one()
    active_users = (await db.execute(active_user_stmt)).scalar_one()

    # 待审批 SIP 数量
    try:
        from app.modules.collection.models.sip import SIPRecord
        sip_stmt = select(func.count()).select_from(SIPRecord).where(
            SIPRecord.is_deleted == False,
            SIPRecord.status == "submitted",
        )
        if not current_user.is_superadmin and current_user.tenant_id:
            sip_stmt = sip_stmt.where(SIPRecord.tenant_id == current_user.tenant_id)
        pending_sips = (await db.execute(sip_stmt)).scalar_one()
    except Exception:
        pending_sips = 0

    return success(
        data=DashboardStats(
            active_tenants=active_tenants,
            total_users=total_users,
            active_users=active_users,
            pending_sips=pending_sips,
        ).model_dump()
    )
