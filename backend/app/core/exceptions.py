"""类型化错误体系：业务代码只抛 AppException 及其子类，
全局异常处理器统一转换为规范化的 JSON 结构，绝不泄露堆栈。"""
from typing import Any


class AppException(Exception):
    """业务异常基类。code 为业务错误码，http_status 为返回的 HTTP 状态码。"""

    code: int = 50000
    http_status: int = 500
    default_message: str = "服务器内部错误"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: int | None = None,
        http_status: int | None = None,
        details: Any = None,
    ):
        self.message = message or self.default_message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        self.details = details
        super().__init__(self.message)


class ValidationError(AppException):
    code = 40001
    http_status = 400
    default_message = "请求参数错误"


class AuthError(AppException):
    code = 40101
    http_status = 401
    default_message = "未认证或认证已过期"


class PermissionDeniedError(AppException):
    code = 40301
    http_status = 403
    default_message = "无权限执行该操作"


class NotFoundError(AppException):
    code = 40401
    http_status = 404
    default_message = "资源不存在"


class ConflictError(AppException):
    code = 40901
    http_status = 409
    default_message = "数据冲突"


class ImportValidationError(AppException):
    code = 42201
    http_status = 422
    default_message = "导入数据校验失败"
