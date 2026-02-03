"""
数据存储
处理原始数据和结果数据的保存
"""
import json
import os
from typing import Any, Dict, List, Optional

from .parser import Post


class Storage:
    """数据存储管理器"""

    def __init__(self, raw_data_dir: str = "raw_data"):
        """
        初始化存储管理器

        Args:
            raw_data_dir: 原始数据保存目录
        """
        self.raw_data_dir = raw_data_dir
        self._ensure_dir(raw_data_dir)

    def _ensure_dir(self, path: str) -> None:
        """确保目录存在"""
        if path and not os.path.exists(path):
            os.makedirs(path)

    def save_raw_page(
        self,
        data: Dict[str, Any],
        username: str,
        page: int,
        retry_count: int = 0,
    ) -> str:
        """
        保存原始页面数据

        Args:
            data: 原始 API 响应数据
            username: 用户名
            page: 页码
            retry_count: 重试次数（用于区分重试后的数据）

        Returns:
            保存的文件路径
        """
        if retry_count > 0:
            filename = f"{username}_page_{page}_retry_{retry_count}.json"
        else:
            filename = f"{username}_page_{page}.json"

        filepath = os.path.join(self.raw_data_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filepath

    def save_posts(
        self,
        posts: List[Post],
        filename: str,
    ) -> str:
        """
        保存处理后的帖子数据

        Args:
            posts: 帖子列表
            filename: 输出文件名

        Returns:
            保存的文件路径
        """
        if not posts:
            return ""

        data = [post.to_dict() for post in posts]

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename

    def load_posts(self, filename: str) -> List[Dict[str, Any]]:
        """
        加载已保存的帖子数据

        Args:
            filename: 文件名

        Returns:
            帖子数据列表
        """
        if not os.path.exists(filename):
            return []

        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_output_filename(self, username: str) -> str:
        """
        获取输出文件名

        Args:
            username: 用户名

        Returns:
            输出文件路径
        """
        return f"{username}_posts.json"
