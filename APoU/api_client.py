"""
API 客户端
封装对 tb.anova.me API 的请求，包含重试逻辑
"""
import time
from typing import Any, Dict, Optional

import requests

from .config import CrawlerConfig, DEFAULT_CONFIG
from .exceptions import (
    APIError,
    NetworkError,
    ParseError,
    RateLimitError,
    MaxRetriesExceededError,
)


class APIClient:
    """API 请求客户端"""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        """
        初始化 API 客户端

        Args:
            config: 爬虫配置，为空时使用默认配置
        """
        self.config = config or DEFAULT_CONFIG
        self._session = requests.Session()
        self._session.headers.update(self.config.headers)

    def fetch_page(
        self,
        username: str,
        page: int,
        forum: str = "",
    ) -> Dict[str, Any]:
        """
        获取指定页的数据

        Args:
            username: 用户名
            page: 页码
            forum: 贴吧名（留空表示所有贴吧）

        Returns:
            API 返回的 JSON 数据

        Raises:
            NetworkError: 网络请求失败
            APIError: API 返回非 200 状态码
            ParseError: JSON 解析失败
        """
        params = {
            "fname": forum,
            "username": username,
            "page": page,
        }

        try:
            response = self._session.get(
                self.config.base_url,
                params=params,
                timeout=self.config.request_timeout,
            )
        except requests.Timeout:
            raise NetworkError("请求超时", f"超过 {self.config.request_timeout} 秒")
        except requests.ConnectionError as e:
            raise NetworkError("连接失败", str(e))
        except requests.RequestException as e:
            raise NetworkError("请求失败", str(e))

        # 检查状态码
        if response.status_code == 429:
            raise RateLimitError("请求过于频繁", retry_after=60)
        if response.status_code != 200:
            raise APIError(
                "API 返回错误",
                status_code=response.status_code,
                response_text=response.text[:300],
            )

        # 解析 JSON
        try:
            data = response.json()
        except ValueError:
            raise ParseError("JSON 解析失败", response.text[:300])

        return data

    def fetch_page_with_retry(
        self,
        username: str,
        page: int,
        forum: str = "",
    ) -> Dict[str, Any]:
        """
        带重试的页面获取

        Args:
            username: 用户名
            page: 页码
            forum: 贴吧名

        Returns:
            API 返回的 JSON 数据

        Raises:
            MaxRetriesExceededError: 超过最大重试次数
        """
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries):
            try:
                return self.fetch_page(username, page, forum)

            except RateLimitError as e:
                # 速率限制，等待后重试
                print(f"[第 {page} 页] 触发速率限制，等待 {e.retry_after} 秒...")
                time.sleep(e.retry_after)
                last_error = e

            except (NetworkError, APIError, ParseError) as e:
                last_error = e
                remaining = self.config.max_retries - attempt - 1

                if remaining > 0:
                    print(f"[第 {page} 页] {e}，{self.config.retry_delay} 秒后重试 "
                          f"(剩余 {remaining} 次)")
                    time.sleep(self.config.retry_delay)
                else:
                    print(f"[第 {page} 页] {e}，重试次数已耗尽")

        # 所有重试都失败
        raise MaxRetriesExceededError(page, self.config.max_retries) from last_error

    def close(self):
        """关闭会话"""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
