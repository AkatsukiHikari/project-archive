from typing import Annotated
from fastapi import APIRouter, Depends, UploadFile, File
from app.modules.iam import schemas
from app.modules.iam.models import User
from app.modules.iam.services.iam_service import IAMService
from app.modules.iam.api.dependencies import get_iam_service, get_current_user
from app.common.response import success, ResponseModel

router = APIRouter()

@router.get(
    "",
    response_model=ResponseModel[schemas.User],
    summary="获取当前登录用户详情",
    response_description="当前登录用户的全部基本信息及权限角色绑定关系"
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    service: IAMService = Depends(get_iam_service)
):
    """获取当前登录用户详情，包含权限标识"""
    permissions = await service.get_user_permissions(current_user.id)
    user_data = schemas.User.model_validate(current_user).model_dump(mode="json")
    user_data["permissions"] = permissions
    return success(data=user_data)


@router.put(
    "/profile",
    response_model=ResponseModel[schemas.User],
    summary="当前用户修改个人信息",
    response_description="更新后的用户信息"
)
async def update_my_profile(
    profile_in: schemas.UserProfileUpdate,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """允许用户自行修改手机号、简介等基本信息"""
    user = await service.update_user_profile(current_user.id, profile_in)
    return success(data=schemas.User.model_validate(user).model_dump(mode="json"))


@router.post(
    "/avatar",
    response_model=ResponseModel[dict],
    summary="流式上传当前用户头像",
    response_description="包含新头像公开 URL 的字典"
)
async def upload_my_avatar(
    file: UploadFile = File(..., description="头像图片文件（JPG/PNG/WEBP/GIF，最大 5MB）"),
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """采用流式上传技术，将头像保存至对象存储并更新系统记录"""
    avatar_url = await service.upload_avatar(current_user.id, file)
    return success(
        data={"avatar_url": avatar_url},
        message="头像上传成功"
    )


@router.put(
    "/password",
    response_model=ResponseModel[None],
    summary="当前用户修改密码",
    response_description="仅返回成功消息"
)
async def update_my_password(
    password_in: schemas.UserPasswordUpdate,
    service: IAMService = Depends(get_iam_service),
    current_user: User = Depends(get_current_user)
):
    """需要提供正确的旧密码才能设置新密码"""
    await service.update_user_password(current_user.id, password_in)
    return success(message="密码修改成功，建议重新登录")
