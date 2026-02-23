from fastapi import APIRouter
from app.modules.iam.api import users, routes_tenant, routes_org, routes_role, routes_menu
from app.modules.audit.api import routes as audits
from app.modules.notification.api import routes as notifications
from app.api.v1 import ws

# ---------------------------------------------------------------------------
# V1 版本路由
# ---------------------------------------------------------------------------

v1_router = APIRouter(prefix="/v1")

# IAM 相关路由
v1_router.include_router(users.router, prefix="/users", tags=["users"])
v1_router.include_router(routes_tenant.router, prefix="/tenants", tags=["tenants"])
v1_router.include_router(routes_org.router, prefix="/organizations", tags=["organizations"])
v1_router.include_router(routes_role.router, prefix="/roles", tags=["roles"])
v1_router.include_router(routes_menu.router, prefix="/menus", tags=["menus"])

# 其他系统集成路由
v1_router.include_router(audits.router, prefix="/audits", tags=["audits"])
v1_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])