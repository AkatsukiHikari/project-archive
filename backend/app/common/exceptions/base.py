"""
自定义异常体系

所有业务异常继承 BaseAPIException，配合全局异常处理器返回标准 {code, data, message} 格式。
code 使用 error_code.py 中的数字错误码。
"""

from typing import Any

from app.common.error_code import ErrorCode


class BaseAPIException(Exception):
    """业务异常基类"""

    def __init__(
        self,
        code: int = ErrorCode.INTERNAL_ERROR,
        message: str = "服务器内部错误",
        status_code: int = 500,
        data: Any = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


class AuthenticationException(BaseAPIException):
    """未认证 / Token 无效"""

    def __init__(self, code: int = ErrorCode.NOT_AUTHENTICATED, message: str = "未登录或 Token 无效"):
        super().__init__(code=code, message=message, status_code=401)


class AuthorizationException(BaseAPIException):
    """权限不足"""

    def __init__(self, code: int = ErrorCode.PERMISSION_DENIED, message: str = "权限不足"):
        super().__init__(code=code, message=message, status_code=403)


class NotFoundException(BaseAPIException):
    """资源不存在"""

    def __init__(self, code: int = ErrorCode.INTERNAL_ERROR, message: str = "资源不存在"):
        super().__init__(code=code, message=message, status_code=404)


class ValidationException(BaseAPIException):
    """参数校验 / 业务校验失败"""

    def __init__(self, code: int = ErrorCode.VALIDATION_ERROR, message: str = "参数校验失败"):
        super().__init__(code=code, message=message, status_code=422)
