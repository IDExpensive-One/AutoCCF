"""
主爬虫逻辑
通过 aiotieba 获取用户主题帖和回复，合并为统一的发言列表
"""
import asyncio
import json
import os
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from .api_client import TiebaAPIClient
from .config import CrawlerConfig, DEFAULT_CONFIG
from .parser import Post, PostParser
from .storage import Storage

if TYPE_CHECKING:
    from AutoCCF.cli import CLI

from AutoCCF.logging import get_apou_logger

logger = get_apou_logger()


class UserPostsCrawler:
    """用户发言列表爬虫（异步）"""

    def __init__(
        self,
        config: Optional[CrawlerConfig] = None,
        on_page_complete: Optional[Callable[[int, int], None]] = None,
        on_log: Optional[Callable[[str, str], None]] = None,
        cli: Optional["CLI"] = None,
    ):
        self.config = config or DEFAULT_CONFIG
        self.on_page_complete = on_page_complete
        self.on_log = on_log
        self.cli = cli

        self._storage = Storage(self.config.raw_data_dir)

        # 爬取状态
        self._posts: List[Post] = []
        self._current_page = 0
        self._is_running = False

    def _print(self, message: str, level: str = "info") -> None:
        if self.on_log:
            try:
                self.on_log(message, level)
            except Exception:
                pass

        if self.cli:
            printer = getattr(self.cli, level, self.cli.info)
            printer(message)
        else:
            print(message)

    @property
    def posts(self) -> List[Post]:
        return self._posts.copy()

    @property
    def total_count(self) -> int:
        return len(self._posts)

    async def crawl(
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
            forum: 贴吧名筛选（留空表示所有贴吧）
            save_raw: 是否保存原始数据（此选项保留但不再使用）
            save_incremental: 是否增量保存
            output_dir: 输出目录
            incremental: 是否增量更新

        Returns:
            所有帖子列表
        """
        self._print(f"目标用户: {username}", "progress")
        self._posts.clear()
        self._current_page = 0
        self._is_running = True

        # 确定输出文件路径
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            output_file = os.path.join(output_dir, "posts.json")
            self._storage = Storage(os.path.join(output_dir, "raw_data"))
        else:
            output_file = self._storage.get_output_filename(username)

        # 增量更新：加载已有数据
        existing_posts: List[Post] = []
        existing_pids: Set[int] = set()

        if incremental:
            existing_data = self._storage.load_posts(output_file)
            if existing_data:
                for post_dict in existing_data:
                    post = PostParser.from_dict(post_dict)
                    existing_posts.append(post)
                    if post.pid:
                        existing_pids.add(post.pid)
                self._print(f"增量模式: 已有 {len(existing_posts)} 条发言", "info")
            else:
                self._print("增量模式: 无历史数据，将获取全部", "info")

        try:
            async with TiebaAPIClient(self.config) as client:
                # 阶段 1: 获取用户主题帖
                self._print("正在获取用户主题帖...", "progress")
                thread_posts = await self._fetch_user_threads(
                    client, username, existing_pids, incremental
                )

                # 将主题帖的 fid→fname 映射预填充到缓存
                for p in thread_posts:
                    if p.fid and p.forum:
                        client.seed_forum_cache(p.fid, p.forum)

                # 阶段 2: 获取用户回复
                self._print("正在获取用户回复...", "progress")
                reply_posts = await self._fetch_user_posts(
                    client, username, existing_pids, incremental
                )

                # 阶段 3: 解析回复的贴吧名
                fids_to_resolve = {
                    p.fid for p in reply_posts if p.fid and not p.forum
                }
                if fids_to_resolve:
                    self._print(
                        f"正在解析 {len(fids_to_resolve)} 个贴吧名...", "progress"
                    )
                    for fid in fids_to_resolve:
                        fname = await client.resolve_forum_name(fid)
                        if fname:
                            for p in reply_posts:
                                if p.fid == fid and not p.forum:
                                    p.forum = fname

                # 合并主题帖和回复
                self._posts = thread_posts + reply_posts

                # 按论坛名筛选
                if forum:
                    self._posts = [p for p in self._posts if p.forum == forum]

        except KeyboardInterrupt:
            self._print("收到中断信号，保存当前进度...", "warning")
            raise
        finally:
            self._is_running = False

        # 合并新旧数据
        merged = self._merge_posts(self._posts, existing_posts)

        # 保存
        self._storage.save_posts(merged, output_file)

        new_count = len(self._posts)
        self._print(f"共获取到 {new_count} 条新发言", "success")
        if existing_posts:
            self._print(f"合并后总计: {len(merged)} 条发言", "info")
        self._print(f"数据已保存到: {output_file}", "info")

        return merged if incremental else self._posts

    async def _fetch_user_threads(
        self,
        client: TiebaAPIClient,
        username: str,
        existing_pids: Set[int],
        incremental: bool,
    ) -> List[Post]:
        """获取用户主题帖"""
        posts: List[Post] = []
        pn = 1
        reached_existing = False

        while self._is_running:
            result = await client.fetch_user_threads(username, pn)
            if result is None:
                self._print(f"[主题帖 第{pn}页] 获取失败，停止", "warning")
                break

            page_items = list(result)
            if not page_items:
                break

            page_posts = []
            for uthread in page_items:
                post = PostParser.from_user_thread(uthread)

                if incremental and post.pid in existing_pids:
                    reached_existing = True
                    self._print(
                        f"遇到已有主题帖 (pid={post.pid})，停止获取", "info"
                    )
                    break

                page_posts.append(post)

            posts.extend(page_posts)
            self._print(
                f"[主题帖 第{pn}页] 获取到 {len(page_posts)} 条"
                f" (总计: {len(posts)})",
                "info",
            )

            if self.on_page_complete:
                self.on_page_complete(pn, len(page_posts))

            if reached_existing or len(page_items) == 0:
                break

            pn += 1
            await asyncio.sleep(self.config.page_delay)

        self._print(f"主题帖获取完成: {len(posts)} 条", "success")
        return posts

    async def _fetch_user_posts(
        self,
        client: TiebaAPIClient,
        username: str,
        existing_pids: Set[int],
        incremental: bool,
    ) -> List[Post]:
        """获取用户回复"""
        posts: List[Post] = []
        pn = 1
        reached_existing = False

        while self._is_running:
            result = await client.fetch_user_posts(
                username, pn, rn=self.config.page_size
            )
            if result is None:
                self._print(f"[回复 第{pn}页] 获取失败，停止", "warning")
                break

            # UserPostss → 遍历 UserPosts 分组 → 遍历 UserPost
            page_posts = []
            has_items = False
            for uposts_group in result:
                has_items = True
                for upost in uposts_group:
                    post = PostParser.from_user_post(upost)

                    if incremental and post.pid in existing_pids:
                        reached_existing = True
                        self._print(
                            f"遇到已有回复 (pid={post.pid})，停止获取", "info"
                        )
                        break

                    page_posts.append(post)

                if reached_existing:
                    break

            posts.extend(page_posts)
            self._print(
                f"[回复 第{pn}页] 获取到 {len(page_posts)} 条"
                f" (总计: {len(posts)})",
                "info",
            )

            if self.on_page_complete:
                self._current_page += 1
                self.on_page_complete(self._current_page, len(page_posts))

            if reached_existing or not has_items:
                break

            pn += 1
            await asyncio.sleep(self.config.page_delay)

        self._print(f"回复获取完成: {len(posts)} 条", "success")
        return posts

    def _merge_posts(
        self,
        new_posts: List[Post],
        existing_posts: List[Post],
    ) -> List[Post]:
        """
        合并新旧帖子列表

        去重（按 pid），按时间倒序排列，重新编号。
        """
        seen_pids: Set[int] = set()
        merged: List[Post] = []

        # 新帖子优先
        for post in new_posts:
            if post.pid and post.pid in seen_pids:
                continue
            if post.pid:
                seen_pids.add(post.pid)
            merged.append(post)

        # 旧帖子补充
        for post in existing_posts:
            if post.pid and post.pid in seen_pids:
                continue
            if post.pid:
                seen_pids.add(post.pid)
            merged.append(post)

        # 按 create_time 倒序（新的在前）
        merged.sort(key=lambda p: p.create_time, reverse=True)

        # 重新编号
        for i, post in enumerate(merged):
            post.id = i + 1

        return merged

    def stop(self) -> None:
        """停止爬取"""
        self._is_running = False

    def get_statistics(self) -> Dict[str, Any]:
        """获取爬取统计信息"""
        forum_stats: Dict[str, int] = {}
        for post in self._posts:
            forum = post.forum or "(未知)"
            forum_stats[forum] = forum_stats.get(forum, 0) + 1

        thread_count = sum(1 for p in self._posts if p.is_thread)
        reply_count = sum(1 for p in self._posts if not p.is_thread)

        return {
            "total_posts": len(self._posts),
            "thread_count": thread_count,
            "reply_count": reply_count,
            "forum_distribution": forum_stats,
        }
