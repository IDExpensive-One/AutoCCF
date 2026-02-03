"""
主爬虫逻辑
协调各模块完成用户发言列表的爬取
"""
import time
from typing import Callable, List, Optional, TYPE_CHECKING

from .api_client import APIClient
from .config import CrawlerConfig, DEFAULT_CONFIG
from .exceptions import (
    APoUError,
    EmptyPageError,
    MaxRetriesExceededError,
)
from .parser import Post, PostParser
from .storage import Storage

# 类型检查时导入，避免循环依赖
if TYPE_CHECKING:
    from AutoCCF.cli import CLI


class UserPostsCrawler:
    """用户发言列表爬虫"""

    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        on_page_complete: Optional[Callable[[int, int], None]] = None,
        cli: Optional["CLI"] = None,
    ):
        """
        初始化爬虫

        Args:
            config: 爬虫配置，为空时使用默认配置
            on_page_complete: 每页完成时的回调函数 (page, posts_count)
            cli: CLI 工具实例，用于美化输出
        """
        self.config = config or DEFAULT_CONFIG
        self.on_page_complete = on_page_complete
        self.cli = cli

        self._api_client = APIClient(self.config)
        self._parser = PostParser()
        self._storage = Storage(self.config.raw_data_dir)

        # 爬取状态
        self._posts: List[Post] = []
        self._current_page = 0
        self._is_running = False

    def _print(self, message: str, level: str = "info") -> None:
        """
        打印消息，使用 CLI 或普通 print

        Args:
            message: 消息内容
            level: 消息级别 (info/success/warning/error/progress)
        """
        if self.cli:
            printer = getattr(self.cli, level, self.cli.info)
            printer(message)
        else:
            print(message)

    @property
    def posts(self) -> List[Post]:
        """获取已爬取的帖子列表"""
        return self._posts.copy()

    @property
    def total_count(self) -> int:
        """获取已爬取的帖子总数"""
        return len(self._posts)

    def crawl(
        self,
        username: str,
        forum: str = "",
        save_raw: bool = True,
        save_incremental: bool = True,
        output_dir: Optional[str] = None,
        incremental: bool = False,
    ) -> List[Post]:
        """
        爬取指定用户的所有发言

        Args:
            username: 目标用户名
            forum: 贴吧名（留空表示所有贴吧）
            save_raw: 是否保存原始数据
            save_incremental: 是否增量保存（每页保存一次）
            output_dir: 输出目录（默认当前目录）
            incremental: 是否增量更新（只获取新发言，遇到已有的就停止）

        Returns:
            所有爬取到的帖子列表

        Raises:
            APoUError: 爬取过程中发生错误
        """
        self._print(f"目标用户: {username}", "progress")

        self._posts.clear()
        self._current_page = 0
        self._is_running = True
        
        # 确定输出文件路径
        if output_dir:
            import os
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, "posts.json")
            # 更新 raw_data 目录到 output_dir 下
            self._storage = Storage(os.path.join(output_dir, "raw_data"))
        else:
            output_file = self._storage.get_output_filename(username)

        # 增量更新：加载已有数据
        existing_posts: List[Post] = []
        existing_tids: set = set()
        
        if incremental:
            existing_data = self._storage.load_posts(output_file)
            if existing_data:
                # 提取已有的 tid
                for post_dict in existing_data:
                    tid = self._extract_tid_from_href(post_dict.get("href", ""))
                    if tid:
                        existing_tids.add(tid)
                    # 重建 Post 对象
                    existing_posts.append(Post(
                        id=post_dict.get("id", 0),
                        title=post_dict.get("title", ""),
                        content=post_dict.get("content", ""),
                        href=post_dict.get("href", ""),
                        forum=post_dict.get("forum", ""),
                    ))
                self._print(f"增量模式: 已有 {len(existing_posts)} 条发言", "info")
            else:
                self._print("增量模式: 无历史数据，将获取全部", "info")
        
        new_posts_count = 0
        reached_existing = False

        try:
            while self._is_running:
                self._current_page += 1
                page = self._current_page

                # 获取当页数据
                try:
                    data = self._fetch_page_with_empty_retry(
                        username, page, forum
                    )
                except MaxRetriesExceededError:
                    self._print(f"[第 {page} 页] 重试次数耗尽，跳过", "warning")
                    continue

                # 保存原始数据
                if save_raw:
                    filepath = self._storage.save_raw_page(data, username, page)
                    if self.config.debug:
                        self._print(f"[第 {page} 页] 原始数据已保存: {filepath}", "info")

                # 解析数据
                page_posts = self._parser.parse_response(
                    data, page, start_id=len(self._posts)
                )
                
                # 增量模式：检查是否遇到已有帖子
                if incremental and existing_tids:
                    new_page_posts = []
                    for post in page_posts:
                        tid = self._extract_tid_from_href(post.href)
                        if tid and tid in existing_tids:
                            # 遇到已有帖子，停止
                            reached_existing = True
                            self._print(
                                f"遇到已有帖子 (tid={tid})，停止获取", 
                                "info"
                            )
                            break
                        new_page_posts.append(post)
                        new_posts_count += 1
                    page_posts = new_page_posts
                else:
                    new_posts_count += len(page_posts)
                
                self._posts.extend(page_posts)

                # 打印进度
                self._print_page_progress(page, page_posts)

                # 回调
                if self.on_page_complete:
                    self.on_page_complete(page, len(page_posts))

                # 增量保存（合并新旧数据）
                if save_incremental:
                    merged = self._merge_posts(self._posts, existing_posts)
                    self._storage.save_posts(merged, output_file)

                # 检查是否结束
                if reached_existing:
                    self._print(
                        f"增量更新完成: 新增 {new_posts_count} 条发言", 
                        "success"
                    )
                    break
                    
                if not self._parser.has_more_data(data):
                    self._print("已获取所有数据", "success")
                    break

                # 页间延迟
                time.sleep(self.config.page_delay)

        except KeyboardInterrupt:
            self._print("收到中断信号，保存当前进度...", "warning")
            raise
        finally:
            self._is_running = False
            # 最终保存（合并新旧数据）
            merged = self._merge_posts(self._posts, existing_posts)
            self._storage.save_posts(merged, output_file)

        self._print(f"共获取到 {len(self._posts)} 条新发言", "success")
        if existing_posts:
            self._print(f"合并后总计: {len(merged)} 条发言", "info")
        self._print(f"数据已保存到: {output_file}", "info")

        return merged if incremental else self._posts
    
    def _extract_tid_from_href(self, href: str) -> Optional[int]:
        """
        从帖子链接中提取 tid
        
        Args:
            href: 帖子链接，如 https://tieba.baidu.com/p/5052759887?pid=xxx
            
        Returns:
            tid 或 None
        """
        import re
        match = re.search(r"/p/(\d+)", href)
        if match:
            return int(match.group(1))
        return None
    
    def _merge_posts(
        self, 
        new_posts: List[Post], 
        existing_posts: List[Post]
    ) -> List[Post]:
        """
        合并新旧帖子列表
        
        新帖子在前，旧帖子在后，按时间倒序排列。
        重新编号 id。
        
        Args:
            new_posts: 新获取的帖子
            existing_posts: 已有的帖子
            
        Returns:
            合并后的帖子列表
        """
        # 新帖子 + 旧帖子（新的在前）
        merged = list(new_posts) + list(existing_posts)
        
        # 重新编号
        for i, post in enumerate(merged):
            post.id = i + 1
            
        return merged

    def _fetch_page_with_empty_retry(
        self,
        username: str,
        page: int,
        forum: str,
    ) -> dict:
        """
        获取页面数据，对空页面进行额外重试

        Args:
            username: 用户名
            page: 页码
            forum: 贴吧名

        Returns:
            API 响应数据

        Raises:
            MaxRetriesExceededError: 超过重试次数仍无数据
        """
        # 首次获取
        data = self._api_client.fetch_page_with_retry(username, page, forum)

        # 检查是否为空页面
        if self._parser.get_posts_count(data) > 0:
            return data

        # 空页面重试（API 有时临时返回空数据）
        for retry in range(self.config.max_empty_page_retries):
            self._print(
                f"[第 {page} 页] 数据为空，"
                f"{self.config.empty_page_retry_delay} 秒后重试 "
                f"({retry + 1}/{self.config.max_empty_page_retries})",
                "warning"
            )

            time.sleep(self.config.empty_page_retry_delay)

            try:
                data = self._api_client.fetch_page_with_retry(
                    username, page, forum
                )
                if self._parser.get_posts_count(data) > 0:
                    self._print(
                        f"[第 {page} 页] 重试成功，"
                        f"获取到 {self._parser.get_posts_count(data)} 条数据",
                        "success"
                    )
                    return data
            except MaxRetriesExceededError:
                continue

        # 所有重试都失败，返回最后的数据（可能为空）
        self._print(f"[第 {page} 页] 所有重试都没有数据，视为已到达末尾", "warning")
        return data

    def _print_page_progress(self, page: int, page_posts: List[Post]) -> None:
        """打印页面进度"""
        if self.cli:
            # 使用 CLI 格式化输出
            details = []
            for post in page_posts[:2]:
                title_preview = post.title[:28] + "..." if len(post.title) > 28 else post.title
                details.append(f"{post.forum} - {title_preview}")

            if len(page_posts) > 2:
                details.append(f"... 还有 {len(page_posts) - 2} 条")

            # 构建任务标题
            title = f"第 {page} 页: {len(page_posts)} 条 (总计: {len(self._posts)})"
            self.cli.print_task(
                index=len(self._posts),
                total=0,  # 未知总数
                title=title,
                status="success",
                details=details if page_posts else None,
            )
        else:
            # 普通输出
            print(f"[第 {page} 页] 获取到 {len(page_posts)} 条数据，"
                  f"总计: {len(self._posts)} 条")

            # 打印前几条的标题
            for post in page_posts[:3]:
                title_preview = post.title[:30] + "..." if len(post.title) > 30 else post.title
                print(f"  [{post.id}] {title_preview}")

            if len(page_posts) > 3:
                print(f"  ... 还有 {len(page_posts) - 3} 条")

    def stop(self) -> None:
        """停止爬取"""
        self._is_running = False

    def get_statistics(self) -> dict:
        """
        获取爬取统计信息

        Returns:
            统计信息字典
        """
        forum_stats: dict = {}
        for post in self._posts:
            forum = post.forum
            forum_stats[forum] = forum_stats.get(forum, 0) + 1

        return {
            "total_posts": len(self._posts),
            "total_pages": self._current_page,
            "forum_distribution": forum_stats,
        }

    def close(self) -> None:
        """关闭爬虫，释放资源"""
        self._api_client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
