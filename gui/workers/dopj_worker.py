"""
DoPJ 后台工作器

在后台线程中运行 DoPJ 爬虫，通过回调更新 UI。
"""
import json
import os
import threading
from typing import Callable, Optional, List, Dict, Any
import flet as ft

from DoPJ.cli import DoPJRunner, TaskStatus
from ..state import app_state, CrawlState, DoPJProgress


class DoPJWorker:
    """
    DoPJ 爬虫后台工作器
    
    在单独的线程中运行 DoPJ，通过 Flet 的 run_thread_safe 更新 UI。
    """
    
    def __init__(
        self,
        page: ft.Page,
        on_log: Optional[Callable[[str, str], None]] = None,
        on_complete: Optional[Callable[[bool, str], None]] = None,
        on_task_update: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        初始化工作器
        
        Args:
            page: Flet 页面对象
            on_log: 日志回调 (message, level)
            on_complete: 完成回调 (success, message)
            on_task_update: 任务状态更新回调 (stats_dict)
        """
        self.page = page
        self.on_log = on_log
        self.on_complete = on_complete
        self.on_task_update = on_task_update
        
        self._runner: Optional[DoPJRunner] = None
        self._thread: Optional[threading.Thread] = None
        self._executor = None
        self._is_running = False
        self._stop_event = threading.Event()
    
    def _update_ui(self, func: Callable[[], None]) -> None:
        """线程安全地更新 UI（Flet 0.80 支持跨线程直接调用）"""
        try:
            func()
        except Exception:
            pass
    
    def _log(self, message: str, level: str = "info") -> None:
        """记录日志"""
        if self.on_log:
            self._update_ui(lambda: self.on_log(message, level))
    
    def _update_progress(self, **kwargs) -> None:
        """更新进度状态"""
        def do_update():
            app_state.update_dopj_progress(**kwargs)
        self._update_ui(do_update)
    
    def start(
        self,
        input_json: str,
        accounts: List[Dict[str, str]],
        output_dir: str,
        threads: int = 3,
        max_retries: int = 3,
        min_interval: float = 2.0,
        max_fails: int = 5,
        incremental: bool = True,
    ) -> None:
        """
        启动爬取任务
        
        Args:
            input_json: 输入的 posts.json 文件路径
            accounts: 账户列表 [{"name": "...", "bduss": "..."}]
            output_dir: 输出目录（用户目录的父目录）
            threads: 并发线程数
            max_retries: 最大重试次数
            min_interval: 最小请求间隔
            max_fails: 最大失败次数后禁用账户
            incremental: 是否增量模式（跳过已存档的帖子）
        """
        if self._is_running:
            self._log("任务已在运行中", "warning")
            return
        
        if not accounts:
            self._log("没有配置账户", "error")
            return
        
        self._is_running = True
        self._stop_event.clear()
        
        # 提取用户名
        username = os.path.basename(os.path.dirname(input_json))
        
        # 初始化进度
        self._update_progress(
            state=CrawlState.RUNNING,
            username=username,
            success_count=0,
            failed_count=0,
            skipped_count=0,
            current=0,
            total=0,
            message="正在初始化...",
        )
        
        # 在后台线程中运行
        self._thread = threading.Thread(
            target=self._run_dopj,
            args=(
                input_json, accounts, output_dir, threads,
                max_retries, min_interval, max_fails, incremental
            ),
            daemon=True,
        )
        self._thread.start()
    
    def _run_dopj(
        self,
        input_json: str,
        accounts: List[Dict[str, str]],
        output_dir: str,
        threads: int,
        max_retries: int,
        min_interval: float,
        max_fails: int,
        incremental: bool,
    ) -> None:
        """在后台线程中执行 DoPJ"""
        success = False
        message = ""

        try:
            self._log(f"开始爬取帖子详情: {input_json}")

            # 直接传递配置字典，无需临时文件
            config_dict = {
                "accounts": accounts,
                "min_interval": min_interval,
                "max_fails": max_fails,
            }

            self._runner = DoPJRunner(
                input_json=input_json,
                config_dict=config_dict,
                output_dir=output_dir,
                threads=threads,
                max_retries=max_retries,
                cli=None,
            )
            
            # 加载任务
            self._runner.load_tasks(incremental=incremental)
            
            total_tasks = len(self._runner.task_manager.tasks)
            self._update_progress(total=total_tasks, message=f"共 {total_tasks} 个任务")
            self._log(f"共 {total_tasks} 个任务")
            
            # 统计跳过的任务
            stats = self._runner.task_manager.get_stats()
            if stats.get("skipped", 0) > 0:
                self._log(f"跳过 {stats['skipped']} 个已存档的帖子", "info")
            
            # 运行爬取（使用自定义处理逻辑以支持进度更新）
            self._run_with_progress()
            
            # 获取最终统计
            final_stats = self._runner.task_manager.get_stats()

            if self._stop_event.is_set():
                success = False
                message = (
                    f"已停止。成功: {final_stats['success']}, "
                    f"失败: {final_stats['failed']}, "
                    f"跳过: {final_stats.get('skipped', 0)}"
                )
                self._log(message, "warning")
                self._update_progress(
                    state=CrawlState.FAILED,
                    success_count=final_stats["success"],
                    failed_count=final_stats["failed"],
                    skipped_count=final_stats.get("skipped", 0),
                    message=message,
                )
            else:
                success = True
                message = (
                    f"完成！成功: {final_stats['success']}, "
                    f"失败: {final_stats['failed']}, "
                    f"跳过: {final_stats.get('skipped', 0)}"
                )
                self._log(message, "success")
                self._update_progress(
                    state=CrawlState.COMPLETED,
                    success_count=final_stats["success"],
                    failed_count=final_stats["failed"],
                    skipped_count=final_stats.get("skipped", 0),
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
            self._runner = None

            # 通知完成
            if self.on_complete:
                self._update_ui(lambda: self.on_complete(success, message))
            
            # 刷新用户缓存
            app_state.invalidate_users_cache()
    
    def _run_with_progress(self) -> None:
        """运行爬取并更新进度"""
        import time
        from concurrent.futures import ThreadPoolExecutor, Future

        runner = self._runner
        if not runner:
            return

        runner.start_time = time.time()
        pending_futures: list[Future] = []

        self._executor = ThreadPoolExecutor(max_workers=runner.threads)
        try:
            while not self._stop_event.is_set():
                task = runner.task_manager.get_next_task()
                if task is None:
                    break

                future = self._executor.submit(self._process_task_with_progress, task)
                pending_futures.append(future)
                time.sleep(0.5)

            # 等待已提交的任务完成（或被取消）
            for f in pending_futures:
                if self._stop_event.is_set():
                    f.cancel()
                else:
                    try:
                        f.result(timeout=300)
                    except Exception:
                        pass
        finally:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

        # 保存索引文件
        runner.task_manager.save_index()
    
    def _process_task_with_progress(self, task) -> None:
        """处理单个任务并更新进度"""
        if self._stop_event.is_set():
            return

        runner = self._runner
        if not runner:
            return

        # 获取账户
        account = runner.account_manager.get_account()
        if not account:
            self._log(f"[{task.index}] 所有账户不可用，跳过", "warning")
            runner.task_manager.mark_failed(task, "所有账户都不可用")
            return
        
        title_preview = task.title[:30] + "..." if len(task.title) > 30 else task.title
        self._log(f"[{task.index}] 正在爬取: {title_preview}")
        
        self._update_progress(
            current_tid=task.tid,
            current_title=title_preview,
            message=f"[{task.index}] {title_preview}",
        )
        
        try:
            import asyncio
            from DoPJ.scraper import scrape_thread
            
            success_result, error_msg = asyncio.run(
                scrape_thread(
                    tid=task.tid,
                    bduss=account["bduss"],
                    output_dir=task.output_dir,
                    on_log=self._log,
                    stop_event=self._stop_event,
                )
            )
            
            if success_result:
                self._log(f"[{task.index}] 成功: {title_preview}", "success")
                runner.task_manager.mark_success(task)
                runner.account_manager.report_success(account)
            else:
                self._log(f"[{task.index}] 失败: {error_msg}", "error")
                is_auth_error = any(k in error_msg for k in ["BDUSS", "认证", "权限"])
                runner.task_manager.mark_failed(task, error_msg)
                runner.account_manager.report_failure(account, is_auth_error)
                
        except Exception as e:
            self._log(f"[{task.index}] 异常: {e}", "error")
            runner.task_manager.mark_failed(task, str(e))
            runner.account_manager.report_failure(account, False)
        
        # 更新统计
        stats = runner.task_manager.get_stats()
        self._update_progress(
            current=stats["success"] + stats["failed"],
            success_count=stats["success"],
            failed_count=stats["failed"],
            skipped_count=stats.get("skipped", 0),
        )
        
        if self.on_task_update:
            self._update_ui(lambda: self.on_task_update(stats))
    
    def stop(self) -> None:
        """请求停止爬取"""
        self._stop_event.set()
        self._log("正在停止...", "warning")
        self._update_progress(message="正在停止...")
        # 立即关闭线程池，取消排队的任务
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=True)
    
    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._is_running
    
    def get_account_status(self) -> Optional[Dict[str, Any]]:
        """获取账户状态"""
        if self._runner:
            return self._runner.account_manager.get_status()
        return None
