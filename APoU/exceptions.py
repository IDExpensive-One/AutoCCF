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


class NetworkError(APoUError):
    """网络请求错误"""

    def __init__(self, message: str = "网络请求失败", details: str = ""):
        super().__init__(message, details)


class APIError(APoUError):
    """API 响应错误"""

    def __init__(
        self,
        message: str = "API 返回错误",
        status_code: int = 0,
        response_text: str = "",
    ):
        self.status_code = status_code
        self.response_text = response_text
        details = f"状态码: {status_code}" if status_code else ""
        super().__init__(message, details)


class ParseError(APoUError):
    """数据解析错误"""

    def __init__(self, message: str = "数据解析失败", raw_data: str = ""):
        self.raw_data = raw_data
        details = raw_data[:200] if raw_data else ""
        super().__init__(message, details)


class RateLimitError(APoUError):
    """速率限制错误"""

    def __init__(self, message: str = "请求过于频繁", retry_after: int = 0):
        self.retry_after = retry_after
        details = f"建议 {retry_after} 秒后重试" if retry_after else ""
        super().__init__(message, details)


class EmptyPageError(APoUError):
    """空页面错误（可能是临时的）"""

    def __init__(self, page: int, message: str = "页面数据为空"):
        self.page = page
        super().__init__(message, f"第 {page} 页")


class MaxRetriesExceededError(APoUError):
    """超过最大重试次数"""

    def __init__(self, page: int, max_retries: int):
        self.page = page
        self.max_retries = max_retries
        super().__init__(
            "超过最大重试次数",
            f"第 {page} 页，已重试 {max_retries} 次"
        )
