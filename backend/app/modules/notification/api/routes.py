"""
通知 API 路由

端点：
- GET    /notifications            — 分页查询当前用户通知
- GET    /notifications/unread-count — 获取未读数量
- PUT    /notifications/{id}/read  — 标记单条已读
- PUT    /notifications/read-all   — 全部标记已读
- DELETE /notifications/{id}       — 删除通知
"""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query

from app.modules.iam.api.dependencies import get_current_user
from app.modules.iam.models import User
from app.modules.notification.api.dependencies import get_notification_service
from app.modules.notification.services.notification_service import NotificationService
from app.modules.notification import schemas
from app.common.response import success, fail
from app.common.error_code import ErrorCode

router = APIRouter()


@router.get("/")
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    type: Optional[str] = Query(None, description="过滤类型: system / todo / message"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """分页查询当前用户通知"""
    items, total = await service.get_user_notifications(
        user_id=current_user.id,
        type_filter=type,
        page=page,
        page_size=page_size,
    )
    return success(
        data=schemas.NotificationPage(
            items=[schemas.NotificationOut.model_validate(n) for n in items],
            total=total,
            page=page,
            page_size=page_size,
        ).model_dump(mode="json")
    )


@router.get("/unread-count")
async def unread_count(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
):
    """获取未读通知数量"""
    count = await service.get_unread_count(current_user.id)
    return success(data=schemas.UnreadCount(count=count).model_dump())


@router.put("/{notification_id}/read")
async def mark_read(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
):
    """标记单条通知为已读"""
    ok = await service.mark_as_read(notification_id, current_user.id)
    if not ok:
        return fail(ErrorCode.VALIDATION_ERROR, "通知不存在或已读")
    return success(message="已标记为已读")


@router.put("/read-all")
async def mark_all_read(
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
):
    """全部标记为已读"""
    count = await service.mark_all_read(current_user.id)
    return success(data={"marked_count": count}, message=f"已标记 {count} 条为已读")


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
):
    """删除通知（逻辑删除）"""
    ok = await service.delete_notification(notification_id, current_user.id)
    if not ok:
        return fail(ErrorCode.VALIDATION_ERROR, "通知不存在")
    return success(message="已删除")
