"""
统一响应包装器

所有 API 返回格式：
{
    "code": 0,          # 0 = 成功，非 0 = 业务错误码
    "data": {} | [] | null,
    "message": "success"
}
"""

from typing import Any

from app.common.error_code import ErrorCode


def success(data: Any = None, message: str = "success") -> dict:
    """构建成功响应"""
    return {
        "code": ErrorCode.SUCCESS,
        "data": data,
        "message": message,
    }


def fail(code: int, message: str, data: Any = None) -> dict:
    """构建失败响应"""
    return {
        "code": code,
        "data": data,
        "message": message,
    }
