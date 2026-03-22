"""
API 客户端
基于 aiotieba 库，通过百度贴吧官方 protobuf API 获取用户数据
"""
import asyncio
import logging
from typing import Any, Dict, Optional

try:
    import aiotieba as tb
except ImportError:
    raise ImportError(
        "aiotieba 未安装，请运行: pip install aiotieba>=4.4.9"
    )

from .config import CrawlerConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class TiebaAPIClient:
    """基于 aiotieba 的异步 API 客户端"""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._client: Optional[tb.Client] = None
        self._forum_cache: Dict[int, str] = {}

    async def __aenter__(self) -> "TiebaAPIClient":
        self._client = tb.Client(self.config.bduss)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    async def _request_with_retry(
        self,
        method_name: str,
        *args,
        operation: str = "",
        **kwargs,
    ) -> Optional[Any]:
        """
        带重试的请求封装

        Args:
            method_name: aiotieba Client 方法名
            *args: 位置参数
            operation: 操作描述（日志用）
            **kwargs: 关键字参数

        Returns:
            请求结果或 None
        """
        for attempt in range(1, self.config.max_retries + 1):
            try:
                method = getattr(self._client, method_name)
                result = await asyncio.wait_for(
                    method(*args, **kwargs),
                    timeout=self.config.request_timeout,
                )
                # aiotieba 通过 .err 属性传递错误
                if hasattr(result, "err") and result.err is not None:
                    logger.warning(
                        f"{operation} 错误 ({attempt}/{self.config.max_retries}): "
                        f"{result.err}"
                    )
                else:
                    return result

            except asyncio.TimeoutError:
                logger.warning(
                    f"{operation} 超时 ({attempt}/{self.config.max_retries})"
                )
            except Exception as e:
                logger.warning(
                    f"{operation} 异常 ({attempt}/{self.config.max_retries}): {e}"
                )

            if attempt < self.config.max_retries:
                await asyncio.sleep(self.config.retry_delay * attempt)

        return None

    async def fetch_user_threads(
        self,
        username: str,
        pn: int = 1,
    ) -> Optional[Any]:
        """
        获取用户发布的主题帖

        Args:
            username: 用户名
            pn: 页码

        Returns:
            UserThreads 对象（可迭代得到 UserThread）或 None
        """
        return await self._request_with_retry(
            "get_user_threads",
            username,
            pn,
            operation=f"获取用户主题帖 [user={username}, pn={pn}]",
        )

    async def fetch_user_posts(
        self,
        username: str,
        pn: int = 1,
        rn: int = 20,
    ) -> Optional[Any]:
        """
        获取用户发布的回复

        Args:
            username: 用户名
            pn: 页码
            rn: 每页条数

        Returns:
            UserPostss 对象（可迭代得到 UserPosts 分组）或 None
        """
        return await self._request_with_retry(
            "get_user_posts",
            username,
            pn,
            rn=rn,
            operation=f"获取用户回复 [user={username}, pn={pn}]",
        )

    async def resolve_forum_name(self, fid: int) -> str:
        """
        根据贴吧 ID 解析贴吧名（带缓存）

        Args:
            fid: 贴吧 ID

        Returns:
            贴吧名
        """
        if fid <= 0:
            return ""

        if fid in self._forum_cache:
            return self._forum_cache[fid]

        try:
            result = await asyncio.wait_for(
                self._client.get_forum_detail(fid),
                timeout=self.config.request_timeout,
            )
            if result and hasattr(result, "err") and result.err is None:
                fname = getattr(result, "fname", "")
                if fname:
                    self._forum_cache[fid] = fname
                    return fname
        except Exception as e:
            logger.debug(f"解析贴吧名失败 [fid={fid}]: {e}")

        return ""

    def seed_forum_cache(self, fid: int, fname: str) -> None:
        """
        预填充贴吧名缓存（从 UserThread 获取的数据可以复用）

        Args:
            fid: 贴吧 ID
            fname: 贴吧名
        """
        if fid > 0 and fname:
            self._forum_cache[fid] = fname

    def close(self):
        """兼容旧接口"""
        pass

    def __enter__(self):
        raise TypeError("请使用 async with TiebaAPIClient(...) as client:")

    def __exit__(self, *args):
        pass
