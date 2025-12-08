"""API 自定义异常类"""

__all__ = [
    "FWAPIError",
    "FWAuthenticationError",
    "FWNotFoundError",
    "FWAPIRetryExhausted",
    "FWValidationError",
    "FWTimeoutError",
    "FWServerError",
]


class FWAPIError(Exception):
    """API 基础异常类"""

    def __init__(self, message: str, status_code: int | None = None, response_data: dict | None = None):
        """
        初始化 API 异常

        Args:
            message: 错误消息
            status_code: HTTP 状态码（可选）
            response_data: 响应数据（可选）
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data


class FWAPIRetryExhausted(FWAPIError):
    """API 重试次数耗尽异常"""

    def __init__(self, message: str = "重试次数耗尽", status_code: int | None = None, response_data: dict | None = None):
        super().__init__(message, status_code, response_data)


class FWAuthenticationError(FWAPIError):
    """认证错误异常"""

    def __init__(self, message: str = "认证失败", status_code: int | None = None, response_data: dict | None = None):
        super().__init__(message, status_code, response_data)


class FWNotFoundError(FWAPIError):
    """资源未找到异常"""

    def __init__(self, message: str = "资源未找到", status_code: int | None = None, response_data: dict | None = None):
        super().__init__(message, status_code, response_data)


class FWValidationError(FWAPIError):
    """数据验证错误异常"""

    def __init__(self, message: str = "数据验证失败", status_code: int | None = None, response_data: dict | None = None):
        super().__init__(message, status_code, response_data)


class FWTimeoutError(FWAPIError):
    """请求超时异常"""

    def __init__(self, message: str = "请求超时", status_code: int | None = None, response_data: dict | None = None):
        super().__init__(message, status_code, response_data)


class FWServerError(FWAPIError):
    """服务器错误异常"""

    def __init__(self, message: str = "服务器错误", status_code: int | None = None, response_data: dict | None = None):
        super().__init__(message, status_code, response_data)
