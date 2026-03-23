"""
主爬虫逻辑
通过 aiotieba 获取用户主题帖和回复，合并为统一的发言列表
"""
import asyncio
import json
import os
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

from .api_client import TiebaAPIClient
from .anova_client import AnovaAPIClient
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
            # 双引擎策略: aiotieba 主引擎 + tb.anova.me 补充引擎
            # 始终先用 aiotieba（数据质量高：有 fid, forum, create_time）
            # 然后用 anova 补充缺失的数据（针对隐私保护用户）
            aiotieba_posts = await self._try_aiotieba_engine(
                username, forum, existing_pids, incremental
            )

            if aiotieba_posts is None:
                aiotieba_posts = []

            # 阶段 2: 使用 anova 补充
            # 条件：aiotieba 获取到的回复数量少（可能是隐私保护）
            aiotieba_reply_count = sum(
                1 for p in aiotieba_posts if not p.is_thread
            )

            if aiotieba_reply_count == 0:
                # 没有回复数据 — 很可能是隐私保护，用 anova 补充
                self._print(
                    f"aiotieba 获取到 {len(aiotieba_posts)} 条"
                    f"（回复 0 条），使用 tb.anova.me 补充...",
                    "warning",
                )
                anova_posts = await self._try_anova_engine(username)

                if anova_posts:
                    # 合并两个引擎的结果（去重）
                    self._posts = self._merge_engine_results(
                        aiotieba_posts, anova_posts,
                    )
                    self._print(
                        f"双引擎合并: aiotieba {len(aiotieba_posts)} 条 "
                        f"+ anova {len(anova_posts)} 条 "
                        f"→ 去重后 {len(self._posts)} 条",
                        "success",
                    )
                else:
                    self._posts = aiotieba_posts
                    if not self._posts:
                        self._print(
                            "两个引擎均未获取到数据，"
                            "用户可能确实没有公开发言",
                            "warning",
                        )
            else:
                # aiotieba 正常返回回复数据 — 无需 anova 补充
                self._posts = aiotieba_posts
                self._print(
                    f"引擎: aiotieba (protobuf API)，"
                    f"共 {len(self._posts)} 条",
                    "info",
                )

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

    async def _try_aiotieba_engine(
        self,
        username: str,
        forum: str,
        existing_pids: Set[int],
        incremental: bool,
    ) -> Optional[List[Post]]:
        """
        尝试使用 aiotieba 引擎获取数据

        Returns:
            帖子列表（可能为空列表表示用户确实无帖），
            或 None 表示引擎不可用（隐私保护导致 0 条结果）
        """
        try:
            async with TiebaAPIClient(self.config) as client:
                # 先试探第 1 页
                self._print("正在尝试 aiotieba 引擎...", "progress")

                threads_result = await client.fetch_user_threads(username, pn=1)
                posts_result = await client.fetch_user_posts(
                    username, pn=1, rn=20,
                )

                # 统计第 1 页结果数
                thread_count = 0
                if threads_result is not None:
                    thread_count = len(list(threads_result))

                post_count = 0
                if posts_result is not None:
                    for group in posts_result:
                        for _upost in group:
                            post_count += 1

                if thread_count == 0 and post_count == 0:
                    # 隐私保护用户 — 返回 None 表示引擎不可用
                    return None

            # 有数据 — 重新建立连接进行完整爬取
            # （因为上面的 result 迭代器已被消耗）
            self._print("aiotieba 引擎可用，开始完整爬取...", "progress")

            async with TiebaAPIClient(self.config) as client:
                # 获取主题帖
                self._print("正在获取用户主题帖...", "progress")
                thread_posts = await self._fetch_user_threads(
                    client, username, existing_pids, incremental
                )

                # 预填充贴吧名缓存
                for p in thread_posts:
                    if p.fid and p.forum:
                        client.seed_forum_cache(p.fid, p.forum)

                # 获取回复
                self._print("正在获取用户回复...", "progress")
                reply_posts = await self._fetch_user_posts(
                    client, username, existing_pids, incremental
                )

                # 解析贴吧名
                fids_to_resolve = {
                    p.fid for p in reply_posts if p.fid and not p.forum
                }
                if fids_to_resolve:
                    self._print(
                        f"正在解析 {len(fids_to_resolve)} 个贴吧名...",
                        "progress",
                    )
                    for fid in fids_to_resolve:
                        fname = await client.resolve_forum_name(fid)
                        if fname:
                            for p in reply_posts:
                                if p.fid == fid and not p.forum:
                                    p.forum = fname

                return thread_posts + reply_posts

        except Exception as e:
            self._print(f"aiotieba 引擎异常: {e}", "warning")
            return None

    async def _try_anova_engine(
        self,
        username: str,
    ) -> List[Post]:
        """
        使用 tb.anova.me 回退引擎获取数据

        Returns:
            帖子列表（可能为空）
        """
        try:
            async with AnovaAPIClient(self.config) as anova:
                def on_page(page_num: int, count: int) -> None:
                    self._print(
                        f"[anova 第{page_num}页] 获取到 {count} 条",
                        "info",
                    )
                    if self.on_page_complete:
                        self.on_page_complete(page_num, count)

                raw_posts = await anova.fetch_all_posts(
                    username, on_page=on_page
                )

                # 转换为 Post 对象
                posts = []
                for i, raw in enumerate(raw_posts):
                    post = PostParser.from_anova_post(raw, post_id=i + 1)
                    posts.append(post)

                self._print(
                    f"tb.anova.me 获取完成: {len(posts)} 条", "success"
                )
                return posts

        except Exception as e:
            self._print(f"tb.anova.me 引擎异常: {e}", "warning")
            return []

    def _merge_engine_results(
        self,
        aiotieba_posts: List[Post],
        anova_posts: List[Post],
    ) -> List[Post]:
        """
        合并两个引擎的结果

        aiotieba 数据质量高（有 fid, forum, create_time），优先保留。
        anova 数据按 tid+pid 去重后补充缺失的帖子。
        """
        # 构建 aiotieba 已有的 tid+pid 集合
        seen_keys: Set[tuple[int, int]] = set()
        merged: List[Post] = []

        for post in aiotieba_posts:
            key = (post.tid, post.pid)
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append(post)

        # anova 帖子补充（仅添加 aiotieba 没有的）
        anova_added = 0
        for post in anova_posts:
            key = (post.tid, post.pid)
            if key not in seen_keys:
                seen_keys.add(key)
                merged.append(post)
                anova_added += 1

        if anova_added > 0:
            self._print(
                f"anova 补充了 {anova_added} 条新帖子",
                "info",
            )

        return merged

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
