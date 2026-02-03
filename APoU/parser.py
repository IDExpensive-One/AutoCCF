"""
数据解析器
解析 API 返回的原始数据，提取帖子信息
"""
import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Post:
    """帖子数据结构"""
    id: int  # 序号
    title: str  # 标题
    content: str  # 内容
    href: str  # 链接
    forum: str  # 贴吧名

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class PostParser:
    """帖子数据解析器"""

    # 每页帖子数（API 固定值）
    PAGE_SIZE = 20

    def parse_response(
        self,
        data: Dict[str, Any],
        page: int,
        start_id: int = 0,
    ) -> List[Post]:
        """
        解析 API 响应数据

        Args:
            data: API 返回的 JSON 数据
            page: 当前页码
            start_id: 起始序号（用于跨页连续编号）

        Returns:
            帖子列表
        """
        posts: List[Post] = []

        # 提取 posts 数组
        raw_posts = self._extract_posts(data)

        for i, raw_post in enumerate(raw_posts):
            post = self._parse_single_post(raw_post, start_id + i + 1)
            if post:
                posts.append(post)

        return posts

    def _extract_posts(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从响应数据中提取帖子列表

        Args:
            data: API 响应数据

        Returns:
            原始帖子列表
        """
        if not isinstance(data, dict):
            return []

        return data.get("posts", [])

    def _parse_single_post(
        self,
        raw_post: Dict[str, Any],
        post_id: int,
    ) -> Optional[Post]:
        """
        解析单个帖子

        Args:
            raw_post: 原始帖子数据
            post_id: 帖子序号

        Returns:
            Post 对象，解析失败返回 None
        """
        if not isinstance(raw_post, dict):
            return None

        href = raw_post.get("href", "")

        return Post(
            id=post_id,
            title=raw_post.get("title", ""),
            content=raw_post.get("content", ""),
            href=href,
            forum=self._extract_forum_name(href),
        )

    def _extract_forum_name(self, href: str) -> str:
        """
        从链接中提取贴吧名

        Args:
            href: 帖子链接

        Returns:
            贴吧名（当前 API 不提供此信息，返回占位符）

        Note:
            tb.anova.me API 返回的数据中不包含贴吧名，
            如需获取真实贴吧名，需要额外请求帖子详情页
        """
        # TODO: 如需真实贴吧名，可在此实现额外请求
        if not href:
            return ""
        return "贴吧"

    def has_more_data(self, data: Dict[str, Any]) -> bool:
        """
        检查是否还有更多数据

        Args:
            data: API 响应数据

        Returns:
            是否还有更多数据
        """
        posts = self._extract_posts(data)
        return len(posts) > 0

    def get_posts_count(self, data: Dict[str, Any]) -> int:
        """
        获取当前页帖子数量

        Args:
            data: API 响应数据

        Returns:
            帖子数量
        """
        return len(self._extract_posts(data))
