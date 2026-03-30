"""
tb.anova.me 回退 API 客户端
当 aiotieba 因用户隐私保护返回 0 条结果时，使用此客户端作为回退。

API 契约（实测确认）:
  GET https://tb.anova.me/getPostsNew?fname=&username={username}&page={N}
  成功: {"msg": "Success.", "posts": [...], "user": {...}, "hasNext": 1}
  空结果: {"msg": "没有查询到回复."}
  每页约 12-20 条
"""
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

import aiohttp

from .config import CrawlerConfig, DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class AnovaAPIClient:
    """tb.anova.me 异步 API 客户端"""

    def __init__(self, config: Optional[CrawlerConfig] = None):
        self.config = config or DEFAULT_CONFIG
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "AnovaAPIClient":
        timeout = aiohttp.ClientTimeout(total=self.config.anova_request_timeout)
        headers = {"Accept-Encoding": "gzip, deflate"}
        self._session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    async def fetch_page(
        self,
        username: str,
        page: int = 1,
    ) -> Tuple[List[Dict[str, Any]], bool, Optional[Dict[str, Any]]]:
        """
        获取指定页的用户发言

        Args:
            username: 用户名
            page: 页码（从 1 开始）

        Returns:
            (posts_list, has_next, user_info)
            - posts_list: 帖子字典列表 [{"title": ..., "content": ..., "href": ...}, ...]
            - has_next: 是否有下一页
            - user_info: 用户信息字典（仅首页返回有意义数据）或 None
        """
        if self._session is None:
            raise RuntimeError("AnovaAPIClient 未初始化，请使用 async with 上下文管理器")

        params = {"fname": "", "username": username, "page": str(page)}

        for attempt in range(1, self.config.anova_max_retries + 1):
            try:
                async with self._session.get(
                    self.config.anova_base_url, params=params
                ) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"[anova] 第{page}页 HTTP {resp.status} "
                            f"({attempt}/{self.config.anova_max_retries})"
                        )
                        if attempt < self.config.anova_max_retries:
                            await asyncio.sleep(self.config.retry_delay * attempt)
                        continue

                    data = await resp.json(content_type=None)

                    # 空结果
                    msg = data.get("msg", "")
                    if "没有查询到" in msg or msg != "Success.":
                        return [], False, None

                    posts = data.get("posts", [])
                    has_next = data.get("hasNext", 0) == 1
                    user_info = data.get("user")

                    return posts, has_next, user_info

            except asyncio.TimeoutError:
                logger.warning(
                    f"[anova] 第{page}页超时 "
                    f"({attempt}/{self.config.anova_max_retries})"
                )
            except aiohttp.ClientError as e:
                logger.warning(
                    f"[anova] 第{page}页网络错误 "
                    f"({attempt}/{self.config.anova_max_retries}): {e}"
                )
            except Exception as e:
                logger.warning(
                    f"[anova] 第{page}页异常 "
                    f"({attempt}/{self.config.anova_max_retries}): {e}"
                )

            if attempt < self.config.anova_max_retries:
                await asyncio.sleep(self.config.retry_delay * attempt)

        logger.error(
            f"[anova] 第{page}页获取失败，已重试 {self.config.anova_max_retries} 次"
        )
        return [], False, None

    async def fetch_all_posts(
        self,
        username: str,
        on_page: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取用户的所有发言（自动翻页）

        Args:
            username: 用户名
            on_page: 可选回调 (page_num, page_posts_count)

        Returns:
            所有帖子字典列表
        """
        all_posts: List[Dict[str, Any]] = []
        page = 1

        while True:
            posts, has_next, _user_info = await self.fetch_page(username, page)

            if not posts:
                break

            all_posts.extend(posts)

            if on_page:
                on_page(page, len(posts))

            if not has_next:
                break

            page += 1
            await asyncio.sleep(self.config.anova_page_delay)

        return all_posts
