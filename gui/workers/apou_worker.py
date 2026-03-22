"""
APoU 后台工作器

在后台线程中运行 APoU 爬虫，通过回调更新 UI。
"""
import asyncio
import threading
from typing import Callable, Optional
import flet as ft

from APoU.crawler import UserPostsCrawler
from APoU.config import CrawlerConfig
from ..state import app_state, CrawlState, APoUProgress


class APoUWorker:
    """
    APoU 爬虫后台工作器

    在单独的线程中运行爬虫，通过 Flet 的 run_thread_safe 更新 UI。
    """

    def __init__(
        self,
        page: ft.Page,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_complete: Optional[Callable[[bool, str], None]] = None,
    ):
        self.page = page
        self.on_log = on_log
        self.on_complete = on_complete

        self._crawler: Optional[UserPostsCrawler] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False

    def _update_ui(self, func: Callable[[], None]) -> None:
        """线程安全地更新 UI"""
        try:
            func()
        except Exception:
            pass

    def _log(self, message: str, level: str = "info") -> None:
        if self.on_log:
            self._update_ui(lambda: self.on_log(message, level))

    def _on_crawler_log(self, message: str, level: str = "info") -> None:
        if level == "progress":
            level = "info"
        self._log(message, level)

    def _update_progress(self, **kwargs) -> None:
        def do_update():
            app_state.update_apou_progress(**kwargs)
        self._update_ui(do_update)

    def _on_page_complete(self, page_num: int, posts_count: int) -> None:
        progress = app_state.apou_progress
        if progress:
            total_posts = progress.posts_collected + posts_count
            self._update_progress(
                pages_done=page_num,
                posts_collected=total_posts,
                message=f"第 {page_num} 页: {posts_count} 条",
            )
            self._log(f"第 {page_num} 页: 获取 {posts_count} 条，总计 {total_posts} 条")

    def start(
        self,
        username: str,
        output_dir: str,
        incremental: bool = False,
        page_delay: float = 2.0,
        max_retries: int = 3,
        bduss: str = "",
    ) -> None:
        """
        启动爬取任务

        Args:
            username: 目标用户名
            output_dir: 输出目录
            incremental: 是否增量模式
            page_delay: 页间延迟
            max_retries: 最大重试次数
            bduss: 百度账号的 BDUSS cookie
        """
        if self._is_running:
            self._log("任务已在运行中", "warning")
            return

        # 获取 BDUSS（参数 > 配置文件）
        if not bduss:
            bduss = self._get_bduss_from_config()
        if not bduss:
            self._log("未找到有效的 BDUSS，无法爬取", "error")
            if self.on_complete:
                self._update_ui(lambda: self.on_complete(False, "未配置 BDUSS"))
            return

        self._is_running = True

        self._update_progress(
            state=CrawlState.RUNNING,
            username=username,
            incremental=incremental,
            pages_done=0,
            posts_collected=0,
            message="正在初始化...",
        )

        config = CrawlerConfig(
            bduss=bduss,
            page_delay=page_delay,
            max_retries=max_retries,
        )

        self._thread = threading.Thread(
            target=self._run_crawl,
            args=(username, output_dir, incremental, config),
            daemon=True,
        )
        self._thread.start()

    def _get_bduss_from_config(self) -> str:
        """从配置文件获取第一个有效的 BDUSS"""
        try:
            from AutoCCF.config import config_manager
            from AutoCCF.utils import is_valid_bduss
            config = config_manager.config or config_manager.load()
            for acc in config.accounts:
                if is_valid_bduss(acc.bduss):
                    return acc.bduss
        except Exception:
            pass
        return ""

    def _run_crawl(
        self,
        username: str,
        output_dir: str,
        incremental: bool,
        config: CrawlerConfig,
    ) -> None:
        """在后台线程中执行爬取（通过 asyncio.run 驱动异步爬虫）"""
        success = False
        message = ""

        try:
            self._log(f"开始爬取用户: {username}")

            self._crawler = UserPostsCrawler(
                config=config,
                on_page_complete=self._on_page_complete,
                on_log=self._on_crawler_log,
            )

            # 异步爬虫通过 asyncio.run 在线程内执行
            posts = asyncio.run(self._crawler.crawl(
                username=username,
                output_dir=output_dir,
                incremental=incremental,
            ))

            success = True
            message = f"爬取完成，共 {len(posts)} 条发言"
            self._log(message, "success")

            self._update_progress(
                state=CrawlState.COMPLETED,
                message=message,
            )

        except KeyboardInterrupt:
            message = "用户中断"
            self._log(message, "warning")
            self._update_progress(
                state=CrawlState.COMPLETED,
                message=message,
            )

        except Exception as e:
            message = f"爬取失败: {str(e)}"
            self._log(message, "error")
            self._update_progress(
                state=CrawlState.FAILED,
                message=message,
            )

        finally:
            self._is_running = False
            self._crawler = None

            if self.on_complete:
                self._update_ui(lambda: self.on_complete(success, message))

            app_state.invalidate_users_cache()

    def stop(self) -> None:
        """停止爬取"""
        if self._crawler:
            self._crawler.stop()
            self._log("正在停止...", "warning")

    @property
    def is_running(self) -> bool:
        return self._is_running
