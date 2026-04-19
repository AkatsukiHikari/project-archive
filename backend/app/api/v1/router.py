from fastapi import APIRouter, Depends
from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.api import users, profile, routes_tenant, routes_org, routes_role, routes_menu
from app.modules.audit.api import routes as audits
from app.modules.notification.api import routes as notifications
from app.modules.schedule.api import routes as schedules
from app.modules.preservation.api import routes as preservation_routes
from app.modules.collection.api import routes as collection_routes
from app.modules.ai.api import routes as ai_routes
from app.modules.repository.api import routes as repository_routes
from app.modules.repository.api.routes_category import router as archive_category_router
from app.modules.repository.api.routes_archive import router as archive_router
from app.modules.repository.api.routes_no_rule import router as no_rule_router
from app.api.v1 import ws, stats

# ---------------------------------------------------------------------------
# V1 版本路由
# ---------------------------------------------------------------------------

v1_router = APIRouter(
    prefix="/v1", 
    redirect_slashes=False,
    dependencies=[Depends(get_current_user)]
)

# IAM 相关路由
v1_router.include_router(profile.router, prefix="/users/me", tags=["profile"])
v1_router.include_router(users.router, prefix="/users", tags=["users"])
v1_router.include_router(routes_tenant.router, prefix="/tenants", tags=["tenants"])
v1_router.include_router(routes_org.router, prefix="/organizations", tags=["organizations"])
v1_router.include_router(routes_role.router, prefix="/roles", tags=["roles"])
v1_router.include_router(routes_menu.router, prefix="/menus", tags=["menus"])

# 其他系统集成路由
v1_router.include_router(audits.router, prefix="/audits", tags=["audits"])
v1_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
v1_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
v1_router.include_router(preservation_routes.router, prefix="/preservation/detections", tags=["preservation"])
v1_router.include_router(collection_routes.router, prefix="/collection/sip", tags=["collection"])
v1_router.include_router(stats.router, prefix="/stats", tags=["stats"])
v1_router.include_router(ai_routes.router, prefix="/ai", tags=["ai"])
v1_router.include_router(repository_routes.router, prefix="/repository", tags=["repository"])
v1_router.include_router(archive_category_router)
v1_router.include_router(archive_router)
v1_router.include_router(no_rule_router)

from app.modules.utilization.api.search import router as search_router
v1_router.include_router(search_router, prefix="/utilization", tags=["utilization"])