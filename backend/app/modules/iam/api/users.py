from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, status, Query, UploadFile, File, HTTPException
from app.modules.iam import schemas
from app.modules.iam.models import User
from app.modules.iam.services.iam_service import IAMService
from app.modules.iam.api.dependencies import get_iam_service, get_current_user
from app.common.response import success
from app.infra.storage.factory import storage
import uuid
import os

router = APIRouter()


@router.get("/")
async def get_users(
    tenant_id: Optional[uuid.UUID] = Query(None, description="按租户过滤"),
    org_id: Optional[uuid.UUID] = Query(None, description="按组织过滤"),
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """获取用户列表"""
    users = await service.get_users(tenant_id=tenant_id, org_id=org_id)
    return success(data=[schemas.User.model_validate(u).model_dump(mode="json") for u in users])


@router.get("/me")
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    """获取当前登录用户详情"""
    return success(data=schemas.User.model_validate(current_user).model_dump(mode="json"))


@router.put("/me/profile")
async def update_my_profile(
    profile_in: schemas.UserProfileUpdate,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """当前用户修改个人信息"""
    user = await service.update_user_profile(current_user.id, profile_in)
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))


@router.post("/me/avatar")
async def upload_my_avatar(
    file: UploadFile = File(..., description="头像图片文件（JPG/PNG/WEBP，最大 5MB）"),
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """上传当前用户头像"""
    # 校验类型
    allowed_content_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_content_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="仅支持 JPG / PNG / WEBP / GIF 格式图片"
        )

    # 校验大小（5MB）
    MAX_SIZE = 5 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="头像文件不得超过 5MB"
        )

    # 构建唯一对象键：{user_id}/{uuid}.ext
    ext = os.path.splitext(file.filename or "avatar.jpg")[1] or ".jpg"
    object_key = f"{current_user.id}/{uuid.uuid4()}{ext}"
    bucket = "avatars"

    import io
    file_like = io.BytesIO(content)
    # save() 内部检测 avatars bucket 并自动设置公开读策略
    storage.save(
        file_object=file_like,
        filename=object_key,
        bucket=bucket,
        content_type=file.content_type or "image/jpeg",
    )

    # 头像是公共资源，调用各存储适配器统一接口构造永久公开 URL，直接存入数据库
    # 无论底层是 MinIO / S3 / AliOSS / Local，调用方完全不感知
    avatar_url = storage.get_public_url(filename=object_key, bucket=bucket)
    await service.update_user_avatar(current_user.id, avatar_url)

    return success(
        data={"avatar_url": avatar_url},
        message="头像上传成功"
    )



@router.put("/me/password")
async def update_my_password(
    password_in: schemas.UserPasswordUpdate,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """当前用户修改密码"""
    await service.update_user_password(current_user.id, password_in)
    return success(message="密码修改成功，建议重新登录")


@router.get("/{user_id}")
async def get_user(
    user_id: uuid.UUID,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """获取指定用户详情"""
    user = await service.get_user_by_id(user_id)
    if not user:
        return success(code=404, message="用户不存在")
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))


@router.post("/")
async def create_user(
    user_in: schemas.UserCreate,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """创建新用户并分配租户/组织/角色"""
    user = await service.register_user(user_in)
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))


@router.put("/{user_id}")
async def update_user(
    user_id: uuid.UUID,
    user_in: schemas.UserUpdate,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """更新用户信息及其关联角色"""
    user = await service.update_user(user_id, user_in)
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))


@router.delete("/{user_id}")
async def delete_user(
    user_id: uuid.UUID,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """删除用户 (软删除)"""
    await service.delete_user(user_id)
    return success(message="删除成功")
