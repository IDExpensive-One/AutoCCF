"""
数据存储
处理结果数据的保存与加载
"""
import json
import os
from typing import Any, Dict, List

from .parser import Post


class Storage:
    """数据存储管理器"""

    def __init__(self, raw_data_dir: str = "raw_data"):
        self.raw_data_dir = raw_data_dir

    def save_posts(
        self,
        posts: List[Post],
        filename: str,
    ) -> str:
        """保存帖子数据"""
        if not posts:
            return ""

        # 确保目录存在
        parent = os.path.dirname(filename)
        if parent:
            os.makedirs(parent, exist_ok=True)

        data = [post.to_dict() for post in posts]

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename

    def load_posts(self, filename: str) -> List[Dict[str, Any]]:
        """加载已保存的帖子数据"""
        if not os.path.exists(filename):
            return []

        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return []

    def get_output_filename(self, username: str) -> str:
        """获取输出文件名"""
        return f"{username}_posts.json"
