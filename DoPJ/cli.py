"""
DoPJ 命令行界面

提供美化的 CLI 接口。
"""
import asyncio
import argparse
import json
import os
import sys
import time
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

# 添加父目录到路径以导入 autoccf
sys.path.insert(0, str(Path(__file__).parent.parent))

from AutoCCF.cli import CLI, Colors
from DoPJ.scraper import scrape_thread


VERSION = "2.0.0"


class TaskStatus:
    """任务状态"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class Task:
    """爬取任务"""

    def __init__(
        self,
        index: int,
        tid: int,
        title: str,
        output_dir: str,
        href: str = "",
        pid: Optional[int] = None,
        json_id: Optional[int] = None,
    ):
        self.index = index
        self.tid = tid
        self.title = title
        self.output_dir = output_dir
        self.href = href
        self.pid = pid
        self.json_id = json_id  # JSON 中的原始 id
        self.status = TaskStatus.PENDING
        self.error_msg = ""
        self.retry_count = 0


class TaskManager:
    """任务管理器"""

    def __init__(self, progress_file: str = "progress.json", max_retries: int = 3):
        self.progress_file = progress_file
        self.max_retries = max_retries
        self.tasks: list[Task] = []
        self._lock = threading.Lock()
        self._current_index = 0
        self.source_file = ""  # 源文件名
        self.user_name = ""    # 用户名（从文件名提取）
        self.user_output_dir = ""  # 用户输出目录

    def load_from_json(self, json_path: str, output_dir: str) -> None:
        """
        从 APoU JSON 文件加载任务

        Args:
            json_path: JSON 文件路径
            output_dir: 输出目录
        """
        # 提取用户名（从文件名或目录名）
        self.source_file = os.path.basename(json_path)
        
        # 如果输入文件是 posts.json（统一架构），从目录名提取用户名
        if self.source_file == "posts.json":
            # 输入路径格式: database/用户名/posts.json
            # 输出目录已经是用户目录，直接使用
            self.user_name = os.path.basename(os.path.dirname(json_path))
            self.user_output_dir = output_dir
        else:
            # 传统格式: 用户名_posts.json
            self.user_name = self._extract_user_name(self.source_file)
            # 创建用户输出目录
            self.user_output_dir = os.path.join(output_dir, self.user_name)
        
        os.makedirs(self.user_output_dir, exist_ok=True)
        
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        posts = data.get("posts", data) if isinstance(data, dict) else data

        # 使用 set 跟踪已添加的 tid，避免重复任务导致并发写入同一数据库
        seen_tids: set[int] = set()
        task_index = 0

        for post in posts:
            tid = self._extract_tid(post)
            if tid and tid not in seen_tids:
                seen_tids.add(tid)
                task_index += 1
                task = Task(
                    index=task_index,
                    tid=tid,
                    title=post.get("title", f"帖子 {tid}"),
                    output_dir=self.user_output_dir,  # 使用用户目录
                    href=post.get("href", ""),
                    pid=post.get("pid"),
                    json_id=post.get("id"),  # 保存 JSON 中的原始 id
                )
                self.tasks.append(task)

    def _extract_user_name(self, filename: str) -> str:
        """从文件名提取用户名"""
        # 去掉扩展名
        name = os.path.splitext(filename)[0]
        # 去掉常见后缀如 _posts
        for suffix in ["_posts", "_post", "_帖子"]:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break
        return name or "default"

    def _extract_tid(self, post: dict) -> Optional[int]:
        """从帖子数据中提取 tid"""
        if "tid" in post:
            return int(post["tid"])

        href = post.get("href", "")
        if "/p/" in href:
            try:
                tid_str = href.split("/p/")[1].split("?")[0].split("#")[0]
                return int(tid_str)
            except (IndexError, ValueError):
                pass

        return None

    def get_next_task(self) -> Optional[Task]:
        """获取下一个待处理的任务"""
        with self._lock:
            while self._current_index < len(self.tasks):
                task = self.tasks[self._current_index]
                self._current_index += 1

                if task.status == TaskStatus.PENDING:
                    return task
                elif task.status == TaskStatus.FAILED and task.retry_count < self.max_retries:
                    task.retry_count += 1
                    return task

            return None

    def mark_success(self, task: Task) -> None:
        """标记任务成功"""
        with self._lock:
            task.status = TaskStatus.SUCCESS
            self.save_progress()

    def mark_failed(self, task: Task, error_msg: str) -> None:
        """标记任务失败"""
        with self._lock:
            task.status = TaskStatus.FAILED
            task.error_msg = error_msg
            self.save_progress()

    def get_stats(self) -> dict:
        """获取统计信息"""
        with self._lock:
            total = len(self.tasks)
            success = sum(1 for t in self.tasks if t.status == TaskStatus.SUCCESS)
            failed = sum(1 for t in self.tasks if t.status == TaskStatus.FAILED)
            pending = sum(1 for t in self.tasks if t.status == TaskStatus.PENDING)
            skipped = sum(1 for t in self.tasks if t.status == TaskStatus.SKIPPED)

            return {
                "total": total,
                "success": success,
                "failed": failed,
                "pending": pending,
                "skipped": skipped,
            }

    def save_progress(self) -> None:
        """保存进度"""
        progress = {
            "tasks": [
                {
                    "tid": t.tid,
                    "status": t.status,
                    "retry_count": t.retry_count,
                    "error_msg": t.error_msg,
                }
                for t in self.tasks
            ]
        }

        # 确保进度文件所在目录存在
        progress_dir = os.path.dirname(self.progress_file)
        if progress_dir:
            os.makedirs(progress_dir, exist_ok=True)

        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def load_progress(self) -> bool:
        """加载进度，返回是否成功加载"""
        if not os.path.exists(self.progress_file):
            return False

        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                progress = json.load(f)

            tid_to_progress = {p["tid"]: p for p in progress.get("tasks", [])}

            for task in self.tasks:
                if task.tid in tid_to_progress:
                    p = tid_to_progress[task.tid]
                    task.status = p.get("status", TaskStatus.PENDING)
                    task.retry_count = p.get("retry_count", 0)
                    task.error_msg = p.get("error_msg", "")

            return True

        except Exception:
            return False
    
    def skip_existing_threads(self) -> int:
        """
        跳过已经存档的帖子（threads/tid 目录已存在）
        
        Returns:
            跳过的任务数
        """
        skipped = 0
        threads_dir = os.path.join(self.user_output_dir, "threads")
        
        for task in self.tasks:
            if task.status != TaskStatus.PENDING:
                continue
                
            thread_dir = os.path.join(threads_dir, str(task.tid))
            # 检查是否有 thread.json（表示已成功爬取）
            thread_file = os.path.join(thread_dir, "thread.json")
            
            if os.path.exists(thread_file):
                task.status = TaskStatus.SKIPPED
                skipped += 1
        
        return skipped

    def save_index(self) -> str:
        """
        保存 index.json 索引文件
        
        Returns:
            index.json 文件路径
        """
        from datetime import datetime
        
        index_data = {
            "source_file": self.source_file,
            "user_name": self.user_name,
            "created_at": datetime.now().isoformat(),
            "total_entries": len(self.tasks),
            "success_count": sum(1 for t in self.tasks if t.status == TaskStatus.SUCCESS),
            "failed_count": sum(1 for t in self.tasks if t.status == TaskStatus.FAILED),
            "entries": []
        }
        
        for task in self.tasks:
            entry = {
                "id": task.json_id,
                "tid": task.tid,
                "title": task.title,
                "status": task.status,
            }
            
            if task.status == TaskStatus.SUCCESS:
                entry["folder"] = str(task.tid)
            elif task.status == TaskStatus.FAILED:
                entry["error"] = task.error_msg
            
            index_data["entries"].append(entry)
        
        index_path = os.path.join(self.user_output_dir, "index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
        
        return index_path


class AccountManager:
    """账户管理器"""

    def __init__(self, accounts: list[dict], min_interval: float = 2.0, max_fails: int = 5):
        self.accounts = accounts
        self.min_interval = min_interval
        self.max_fails = max_fails

        self._index = 0
        self._lock = threading.Lock()
        self._fail_counts = [0] * len(accounts)
        self._banned = [False] * len(accounts)
        self._last_use = [0.0] * len(accounts)

    def get_account(self) -> Optional[dict]:
        """获取下一个可用账户"""
        with self._lock:
            for _ in range(len(self.accounts)):
                idx = self._index
                self._index = (self._index + 1) % len(self.accounts)

                if self._banned[idx]:
                    continue

                # 检查间隔
                elapsed = time.time() - self._last_use[idx]
                if elapsed < self.min_interval:
                    time.sleep(self.min_interval - elapsed)

                self._last_use[idx] = time.time()
                return {
                    "index": idx,
                    "name": self.accounts[idx].get("name", f"账户 {idx + 1}"),
                    "bduss": self.accounts[idx]["bduss"],
                }

            return None

    def report_success(self, account: dict) -> None:
        """报告成功"""
        with self._lock:
            idx = account["index"]
            self._fail_counts[idx] = max(0, self._fail_counts[idx] - 1)

    def report_failure(self, account: dict, is_auth_error: bool = False) -> None:
        """报告失败"""
        with self._lock:
            idx = account["index"]
            self._fail_counts[idx] += 1

            if is_auth_error or self._fail_counts[idx] >= self.max_fails:
                self._banned[idx] = True

    def get_status(self) -> dict:
        """获取账户状态"""
        with self._lock:
            return {
                "total": len(self.accounts),
                "available": sum(1 for b in self._banned if not b),
                "accounts": [
                    {
                        "name": self.accounts[i].get("name", f"账户 {i + 1}"),
                        "is_banned": self._banned[i],
                        "fail_count": self._fail_counts[i],
                    }
                    for i in range(len(self.accounts))
                ],
            }


class DoPJRunner:
    """DoPJ 运行器"""

    def __init__(
        self,
        input_json: str,
        config_file: str,
        output_dir: str = "posts",
        threads: int = 3,
        max_retries: int = 3,
        progress_file: str = "progress.json",
        cli: Optional[CLI] = None,
    ):
        self.input_json = input_json
        self.output_dir = output_dir
        self.threads = threads
        self.max_retries = max_retries
        self.cli = cli

        # 加载配置
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)

        accounts = config.get("accounts", [])
        if not accounts:
            raise ValueError("配置文件中没有账户信息")

        self.account_manager = AccountManager(
            accounts=accounts,
            min_interval=config.get("min_interval", 2.0),
            max_fails=config.get("max_fails", 5),
        )

        self.task_manager = TaskManager(
            progress_file=progress_file,
            max_retries=max_retries,
        )

        self.start_time: float = 0.0
        self._lock = threading.Lock()

    def load_tasks(self, incremental: bool = True) -> None:
        """
        加载任务
        
        Args:
            incremental: 是否启用增量模式（跳过已存档的帖子）
        """
        self.task_manager.load_from_json(self.input_json, self.output_dir)
        
        # 更新 progress_file 路径到用户目录
        self.task_manager.progress_file = os.path.join(
            self.task_manager.user_output_dir, "progress.json"
        )
        
        if self.cli:
            self.cli.print_section("任务配置")
            self.cli.print_config([
                ("输入文件", self.input_json),
                ("用户名", self.task_manager.user_name),
                ("输出目录", self.task_manager.user_output_dir),
                ("并发线程", str(self.threads)),
                ("最大重试", str(self.max_retries)),
            ])

        if self.task_manager.load_progress():
            if self.cli:
                self.cli.info("检测到上次未完成的任务，将继续执行")
        
        # 增量模式：跳过已存档的帖子
        if incremental:
            skipped = self.task_manager.skip_existing_threads()
            if skipped > 0 and self.cli:
                self.cli.info(f"增量模式: 跳过 {skipped} 个已存档的帖子")

        self._print_account_status()

    def _print_account_status(self) -> None:
        """打印账户状态"""
        status = self.account_manager.get_status()

        if self.cli:
            self.cli.print_section("账户状态")
            print(f"  {Colors.GRAY}可用账户:{Colors.RESET} "
                  f"{Colors.GREEN}{status['available']}{Colors.RESET}/"
                  f"{status['total']}")
            print()

            for acc in status["accounts"]:
                if acc["is_banned"]:
                    icon = f"{Colors.RED}x{Colors.RESET}"
                    state = f"{Colors.RED}已禁用{Colors.RESET}"
                else:
                    icon = f"{Colors.GREEN}+{Colors.RESET}"
                    state = f"{Colors.GREEN}可用{Colors.RESET}"
                print(f"    {icon} {acc['name']}: {state}")

    def process_task(self, task: Task) -> None:
        """处理单个任务"""
        account = self.account_manager.get_account()
        if not account:
            if self.cli:
                self.cli.warning(f"[{task.index:04d}] 所有账户都不可用，跳过任务")
            self.task_manager.mark_failed(task, "所有账户都不可用")
            return

        title_preview = task.title[:35] + "..." if len(task.title) > 35 else task.title

        if self.cli:
            self.cli.print_task(
                index=task.index,
                total=self.task_manager.get_stats()["total"],
                title=title_preview,
                status="processing",
                details=[
                    f"tid={task.tid}",
                    f"账户: {account['name']}",
                ],
            )

        # 异步爬取
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            success, error_msg = loop.run_until_complete(
                scrape_thread(
                    tid=task.tid,
                    bduss=account["bduss"],
                    output_dir=task.output_dir,
                )
            )

            if success:
                if self.cli:
                    print(f"  {Colors.GREEN}+ 爬取成功{Colors.RESET}")
                self.task_manager.mark_success(task)
                self.account_manager.report_success(account)
            else:
                if self.cli:
                    print(f"  {Colors.RED}x 爬取失败: {error_msg}{Colors.RESET}")
                is_auth_error = any(k in error_msg for k in ["BDUSS", "认证", "权限"])
                self.task_manager.mark_failed(task, error_msg)
                self.account_manager.report_failure(account, is_auth_error)

        except Exception as e:
            if self.cli:
                print(f"  {Colors.RED}x 处理异常: {e}{Colors.RESET}")
            self.task_manager.mark_failed(task, str(e))
            self.account_manager.report_failure(account, False)

        finally:
            loop.close()

        self._print_progress()

    def _print_progress(self) -> None:
        """打印进度"""
        stats = self.task_manager.get_stats()
        elapsed = time.time() - self.start_time

        if self.cli:
            self.cli.clear_line()
            self.cli.print_progress_bar(
                current=stats["success"] + stats["failed"],
                total=stats["total"],
                suffix=f"成功: {stats['success']} | 失败: {stats['failed']} | 耗时: {self.cli.format_duration(elapsed)}",
            )
            print()

    def run(self) -> None:
        """运行主程序"""
        self.start_time = time.time()

        if self.cli:
            self.cli.print_section("开始爬取")

        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            while True:
                task = self.task_manager.get_next_task()
                if task is None:
                    break

                executor.submit(self.process_task, task)
                time.sleep(0.5)

        # 保存 index.json 索引文件
        index_path = self.task_manager.save_index()
        if self.cli:
            self.cli.info(f"索引文件已保存: {index_path}")

        self._print_final_stats()

    def _print_final_stats(self) -> None:
        """打印最终统计"""
        stats = self.task_manager.get_stats()
        elapsed = time.time() - self.start_time
        account_status = self.account_manager.get_status()

        if self.cli:
            self.cli.print_section("爬取完成")

            stats_items = [
                ("总任务数", str(stats["total"]), "white"),
                ("成功", str(stats["success"]), "green"),
                ("失败", str(stats["failed"]), "red" if stats["failed"] > 0 else "gray"),
            ]
            
            # 如果有跳过的任务，显示跳过数量
            if stats.get("skipped", 0) > 0:
                stats_items.append(
                    ("已跳过", str(stats["skipped"]), "yellow")
                )
            
            stats_items.extend([
                ("总耗时", self.cli.format_duration(elapsed), "yellow"),
                ("输出目录", self.task_manager.user_output_dir, "cyan"),
            ])
            
            self.cli.print_stats_box(stats_items)

            print()
            print(f"  {Colors.GRAY}账户状态:{Colors.RESET}")
            for acc in account_status["accounts"]:
                if acc["is_banned"]:
                    status_color = Colors.RED
                    status_text = "已禁用"
                else:
                    status_color = Colors.GREEN
                    status_text = "正常"
                print(f"    * {acc['name']}: "
                      f"{status_color}{status_text}{Colors.RESET} "
                      f"{Colors.DIM}(失败: {acc['fail_count']}){Colors.RESET}")

            self.cli.print_footer("爬取任务完成！")


def main():
    """主函数"""
    cli = CLI("DoPJ - Detail of Posts JSON", VERSION)

    parser = argparse.ArgumentParser(
        description="DoPJ - 从 APoU JSON 获取帖子详细内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python DoPJ.py -i posts.json -c config.json
  python DoPJ.py -i posts.json -c config.json -o output -t 5
        """,
    )

    parser.add_argument("-i", "--input", help="APoU 输出的 JSON 文件")
    parser.add_argument("-c", "--config", help="配置文件（包含账户信息）")
    parser.add_argument("-o", "--output", default="posts", help="输出目录（默认: posts）")
    parser.add_argument("-t", "--threads", type=int, default=3, help="并发线程数（默认: 3）")
    parser.add_argument("-r", "--retries", type=int, default=3, help="最大重试次数（默认: 3）")
    parser.add_argument("-p", "--progress", default=None, help="进度文件（默认: <输出目录>/progress.json）")

    args = parser.parse_args()
    
    # 如果未指定进度文件，则默认放在输出目录中
    if args.progress is None:
        args.progress = os.path.join(args.output, "progress.json")

    # 打印横幅
    cli.print_banner("百度贴吧帖子详情爬虫")

    # 交互式获取必填参数
    input_file = get_input_file(args, cli)
    config_file = get_config_file(args, cli)

    # 显示配置
    cli.print_section("爬取配置")
    cli.print_config([
        ("输入文件", input_file),
        ("配置文件", config_file),
        ("输出目录", args.output),
        ("并发线程", str(args.threads)),
        ("最大重试", str(args.retries)),
    ])

    runner: Optional[DoPJRunner] = None

    try:
        runner = DoPJRunner(
            input_json=input_file,
            config_file=config_file,
            output_dir=args.output,
            threads=args.threads,
            max_retries=args.retries,
            progress_file=args.progress,
            cli=cli,
        )

        runner.load_tasks()
        runner.run()

    except ValueError as e:
        cli.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print()
        cli.warning("收到中断信号，正在保存进度...")
        if runner is not None:
            runner.task_manager.save_progress()
            cli.info("进度已保存，下次运行时将继续")
        cli.print_footer()
        sys.exit(0)
    except Exception as e:
        cli.error(f"发生错误: {e}")
        sys.exit(1)


def get_input_file(args: argparse.Namespace, cli: CLI) -> str:
    """获取输入文件（命令行参数或交互输入）"""
    if args.input:
        if not os.path.exists(args.input):
            cli.error(f"输入文件不存在: {args.input}")
            sys.exit(1)
        return args.input

    try:
        while True:
            input_file = input(f"{Colors.CYAN}? 请输入 APoU JSON 文件路径: {Colors.RESET}").strip()
            # 移除用户可能输入的引号
            input_file = input_file.strip('"').strip("'")
            if not input_file:
                cli.error("必须提供输入文件")
                print(f"  {Colors.DIM}使用示例：python DoPJ.py -i posts.json -c config.json{Colors.RESET}")
                continue
            if not os.path.exists(input_file):
                cli.error(f"文件不存在: {input_file}")
                continue
            return input_file
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def get_config_file(args: argparse.Namespace, cli: CLI) -> str:
    """获取配置文件（命令行参数或交互输入）"""
    if args.config:
        if not os.path.exists(args.config):
            cli.error(f"配置文件不存在: {args.config}")
            sys.exit(1)
        return args.config

    # 尝试自动查找配置文件
    default_configs = ["config.json", "DoPJ/config/config.json", "accounts.json"]
    for default in default_configs:
        if os.path.exists(default):
            use_default = input(
                f"{Colors.CYAN}? 找到配置文件 {default}，是否使用？[Y/n]: {Colors.RESET}"
            ).strip().lower()
            if use_default in ("", "y", "yes"):
                return default

    try:
        while True:
            config_file = input(f"{Colors.CYAN}? 请输入配置文件路径: {Colors.RESET}").strip()
            # 移除用户可能输入的引号
            config_file = config_file.strip('"').strip("'")
            if not config_file:
                cli.error("必须提供配置文件")
                print(f"  {Colors.DIM}配置文件应包含账户 BDUSS 信息{Colors.RESET}")
                continue
            if not os.path.exists(config_file):
                cli.error(f"文件不存在: {config_file}")
                continue
            return config_file
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
