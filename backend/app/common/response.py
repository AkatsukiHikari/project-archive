"""
统一响应包装器

所有 API 返回格式：
{
    "code": 0,          # 0 = 成功，非 0 = 业务错误码
    "data": {} | [] | null,
    "message": "success"
}
"""

from typing import Any, Generic, TypeVar, Optional
from pydantic import BaseModel, Field

from app.common.error_code import ErrorCode

DataT = TypeVar("DataT")

class ResponseModel(BaseModel, Generic[DataT]):
    """统一 API 响应模型，用于自动生成 OpenAPI Schema"""
    code: int = Field(default=0, description="响应状态码（0 代表成功）")
    data: Optional[DataT] = Field(default=None, description="业务数据 payload")
    message: str = Field(default="success", description="提示信息或错误描述")

def success(data: Any = None, message: str = "success") -> dict:
    """构建成功响应字典"""
    return {
        "code": ErrorCode.SUCCESS,
        "data": data,
        "message": message,
    }

def fail(code: int, message: str, data: Any = None) -> dict:
    """构建失败响应字典"""
    return {
        "code": code,
        "data": data,
        "message": message,
    }

