"""
自定义异常类
为 APoU 爬虫提供清晰的错误类型
"""


class APoUError(Exception):
    """APoU 基础异常类"""

    def __init__(self, message: str, details: str = ""):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class AuthError(APoUError):
    """认证错误（BDUSS 无效或缺失）"""

    def __init__(self, message: str = "认证失败", details: str = ""):
        super().__init__(message, details)


class NetworkError(APoUError):
    """网络请求错误"""

    def __init__(self, message: str = "网络请求失败", details: str = ""):
        super().__init__(message, details)


class MaxRetriesExceededError(APoUError):
    """超过最大重试次数"""

    def __init__(self, page: int = 0, max_retries: int = 0):
        self.page = page
        self.max_retries = max_retries
        super().__init__(
            "超过最大重试次数",
            f"第 {page} 页，已重试 {max_retries} 次" if page else "",
        )
