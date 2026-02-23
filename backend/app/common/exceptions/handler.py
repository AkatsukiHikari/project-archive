"""
全局异常处理器

捕获 BaseAPIException 及未知异常，统一返回 {code, data, message} 格式。
"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from app.common.error_code import ErrorCode
from app.common.exceptions.base import BaseAPIException

logger = logging.getLogger(__name__)


async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """处理所有自定义业务异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "data": exc.data,
            "message": exc.message,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理所有未捕获的未知异常"""
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "code": ErrorCode.INTERNAL_ERROR,
            "data": None,
            "message": "服务器内部错误",
        },
    )
