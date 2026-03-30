"""
AutoCCF Python Bridge

Electron 与 Python 业务层之间的通信桥接。
从 stdin 读取 JSON 请求，将结果与进度以 NDJSON 写入 stdout。
"""

import asyncio
import io
import json
import os
import sys
import threading
from typing import Any, TextIO


for stream_name in ("stdout", "stderr", "stdin"):
    stream = getattr(sys, stream_name, None)
    if hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


_real_stdout: TextIO = sys.stdout


class _NdjsonStdoutWrapper(io.TextIOBase):
    """拦截 print 输出，转发为 NDJSON log 事件，避免污染通信通道。"""

    def __init__(self, real_stdout: TextIO) -> None:
        self._real = real_stdout

    def write(self, s: str) -> int:
        text = s.strip()
        if text:
            line = json.dumps(
                {"type": "log", "data": {"level": "debug", "message": text}},
                ensure_ascii=False,
            )
            self._real.write(line + "\n")
            self._real.flush()
        return len(s)

    def flush(self) -> None:
        self._real.flush()


sys.stdout = _NdjsonStdoutWrapper(_real_stdout)


def emit(msg_type: str, data: dict) -> None:
    """输出一行 NDJSON 到真实 stdout。"""
    line = json.dumps({"type": msg_type, "data": data}, ensure_ascii=False)
    _real_stdout.write(line + "\n")
    _real_stdout.flush()


def _load_posts_count(posts_file: str) -> int:
    if not os.path.exists(posts_file):
        return 0
    try:
        with open(posts_file, "r", encoding="utf-8") as f:
            posts_data = json.load(f)
        return len(posts_data) if isinstance(posts_data, list) else 0
    except Exception:
        return 0


def handle_config_load(payload: dict) -> None:
    """加载配置文件，返回完整 BDUSS（掩码由 renderer 处理）。"""
    del payload
    from AutoCCF.config import ConfigManager

    cm = ConfigManager()
    try:
        config = cm.load()
        emit(
            "result",
            {
                "success": True,
                "config": {
                    "database_dir": config.database_dir,
                    "accounts": [{"name": a.name, "bduss": a.bduss} for a in config.accounts],
                    "apou": {
                        "page_delay": config.apou.page_delay,
                        "max_retries": config.apou.max_retries,
                    },
                    "dopj": {
                        "threads": config.dopj.threads,
                        "max_retries": config.dopj.max_retries,
                        "min_interval": config.dopj.min_interval,
                        "max_fails": config.dopj.max_fails,
                    },
                },
            },
        )
    except Exception as e:
        emit("error", {"code": "CONFIG_ERROR", "message": str(e)})


def handle_config_save(payload: dict) -> None:
    """保存配置（load -> mutate -> save，保留原 config_path）。"""
    from AutoCCF.config import ConfigManager, UnifiedConfig

    try:
        cm = ConfigManager()
        existing = cm.load()
        original_path = existing.config_path
        new_config = UnifiedConfig.from_dict(payload, config_path=original_path)
        saved_path = new_config.save()
        emit("result", {"success": True, "path": saved_path})
    except Exception as e:
        emit("error", {"code": "CONFIG_SAVE_ERROR", "message": str(e)})


def handle_apou_crawl(payload: dict) -> None:
    """执行 APoU 抓取。"""
    from APoU.config import CrawlerConfig
    from APoU.crawler import UserPostsCrawler
    from AutoCCF.config import ConfigManager
    from AutoCCF.utils import UserPaths

    username = payload.get("username", "")
    if not username:
        emit("error", {"code": "INVALID_PAYLOAD", "message": "缺少 username 参数"})
        return

    cm = ConfigManager()
    config = cm.load()

    bduss = ""
    for account in config.accounts:
        if account.bduss and account.bduss.strip():
            bduss = account.bduss
            break

    crawler_config = CrawlerConfig(
        page_delay=config.apou.page_delay,
        max_retries=config.apou.max_retries,
        bduss=bduss,
    )

    user_paths = UserPaths(config.database_dir, username)
    apou_dir = str(user_paths.apou_dir)
    output_file = str(user_paths.posts_file)

    base_posts_count = _load_posts_count(output_file)
    progress_step = 0
    progress_new_posts = 0

    def on_page_complete(page_num: int, posts_count: int) -> None:
        nonlocal progress_step, progress_new_posts
        delta_posts_count = max(0, int(posts_count or 0))
        progress_step += 1
        progress_new_posts += delta_posts_count
        total_posts_count = base_posts_count + progress_new_posts
        emit(
            "progress",
            {
                "page": progress_step,
                "source_page": page_num,
                "posts_count": total_posts_count,
                "delta_posts_count": delta_posts_count,
                "new_posts_count": progress_new_posts,
                "base_posts_count": base_posts_count,
                "message": (
                    f"第 {progress_step} 步完成（源页 {page_num}），"
                    f"本步新增 {delta_posts_count} 条，累计 {total_posts_count} 条"
                ),
            },
        )

    def on_log(message: str, level: str) -> None:
        emit("log", {"level": level, "message": message})

    class _DummyCli:
        """占位 CLI：避免 crawler 内部 fallback 到 print。"""

        def info(self, msg: str) -> None:
            del msg
            return

        def warning(self, msg: str) -> None:
            del msg
            return

        def error(self, msg: str) -> None:
            del msg
            return

        def success(self, msg: str) -> None:
            del msg
            return

    crawler = UserPostsCrawler(
        config=crawler_config,
        on_page_complete=on_page_complete,
        on_log=on_log,
        cli=_DummyCli(),
    )

    try:
        posts = asyncio.run(
            crawler.crawl(
                username=username,
                output_dir=apou_dir,
                incremental=True,
            )
        )
        total_posts_count = len(posts)
        new_posts_count = max(0, total_posts_count - base_posts_count)

        emit(
            "progress",
            {
                "page": max(progress_step, 1),
                "source_page": 0,
                "posts_count": total_posts_count,
                "delta_posts_count": 0,
                "new_posts_count": new_posts_count,
                "base_posts_count": base_posts_count,
                "message": (
                    f"抓取完成，累计 {total_posts_count} 条，"
                    f"本次新增 {new_posts_count} 条"
                ),
            },
        )
        emit(
            "result",
            {
                "success": True,
                "posts_count": total_posts_count,
                "new_posts_count": new_posts_count,
                "base_posts_count": base_posts_count,
                "output_file": output_file,
            },
        )
    except Exception as e:
        emit("error", {"code": "APOU_ERROR", "message": str(e)})


def handle_dopj_crawl(payload: dict) -> None:
    """执行 DoPJ 抓取，主线程轮询并推送进度。"""
    from AutoCCF.config import ConfigManager
    from AutoCCF.utils import UserPaths
    from DoPJ.cli import DoPJRunner

    input_json = payload.get("input_json", "")
    threads_override = payload.get("threads")

    if not input_json:
        emit("error", {"code": "INVALID_PAYLOAD", "message": "缺少 input_json 参数"})
        return

    cm = ConfigManager()
    config = cm.load()
    if not config.accounts:
        emit("error", {"code": "NO_ACCOUNTS", "message": "未配置账户"})
        return

    threads = threads_override if threads_override is not None else config.dopj.threads

    input_path = os.path.abspath(input_json)
    apou_dir = os.path.dirname(input_path)
    user_dir = os.path.dirname(apou_dir)
    username = os.path.basename(user_dir)
    user_paths = UserPaths(config.database_dir, username)
    output_dir = str(user_paths.dopj_dir)

    config_dict = {
        "accounts": [{"name": a.name, "bduss": a.bduss} for a in config.accounts],
        "min_interval": config.dopj.min_interval,
        "max_fails": config.dopj.max_fails,
    }

    try:
        class _BridgeCli:
            """将 CLI 日志转发为 bridge:log。"""

            def info(self, msg: str) -> None:
                emit("log", {"level": "info", "message": msg})

            def warning(self, msg: str) -> None:
                emit("log", {"level": "warning", "message": msg})

            def error(self, msg: str) -> None:
                emit("log", {"level": "error", "message": msg})

            def success(self, msg: str) -> None:
                emit("log", {"level": "info", "message": msg})

            def progress(self, msg: str) -> None:
                emit("log", {"level": "info", "message": msg})

            def print_section(self, title: str) -> None:
                del title
                return

            def print_config(self, items: list[tuple[str, str]]) -> None:
                del items
                return

            def print_task(self, **kw: object) -> None:
                del kw
                return

            def print_progress_bar(self, **kw: object) -> None:
                del kw
                return

            def clear_line(self) -> None:
                return

            def format_duration(self, seconds: float) -> str:
                return f"{seconds:.1f}s"

            def print_stats_box(self, stats: list[tuple[str, str, str]]) -> None:
                del stats
                return

            def print_footer(self, message: str = "") -> None:
                del message
                return

        runner = DoPJRunner(
            input_json=input_json,
            output_dir=output_dir,
            threads=min(threads, len(config.accounts)),
            max_retries=config.dopj.max_retries,
            config_dict=config_dict,
            cli=_BridgeCli(),
        )
        runner.load_tasks()

        worker_error: list[Exception] = []

        def _run_worker() -> None:
            try:
                runner.run()
            except Exception as exc:
                worker_error.append(exc)

        worker = threading.Thread(target=_run_worker, daemon=True)
        worker.start()

        while worker.is_alive():
            worker.join(timeout=2.0)
            stats = runner.task_manager.get_stats()
            done = stats.get("success", 0) + stats.get("failed", 0) + stats.get("skipped", 0)
            emit(
                "progress",
                {
                    "success": stats.get("success", 0),
                    "failed": stats.get("failed", 0),
                    "pending": stats.get("pending", 0),
                    "skipped": stats.get("skipped", 0),
                    "total": stats.get("total", 0),
                    "message": (
                        f"已完成 {done}/{stats.get('total', 0)} "
                        f"(成功 {stats.get('success', 0)}, 失败 {stats.get('failed', 0)})"
                    ),
                },
            )

        if worker_error:
            raise worker_error[0]

        stats = runner.task_manager.get_stats()
        emit("result", {"success": True, "stats": stats})
    except Exception as e:
        emit("error", {"code": "DOPJ_ERROR", "message": str(e)})


def handle_users_list(payload: dict) -> None:
    """列出已抓取用户。"""
    del payload
    from AutoCCF.config import ConfigManager

    cm = ConfigManager()
    cm.load()
    try:
        users = cm.list_users()
        for user in users:
            user_path = user.get("path", "")
            if user_path and os.path.isdir(user_path):
                try:
                    user["last_activity"] = os.path.getmtime(user_path)
                except OSError:
                    user["last_activity"] = None
            else:
                user["last_activity"] = None
        emit("result", {"success": True, "users": users})
    except Exception as e:
        emit("error", {"code": "USERS_LIST_ERROR", "message": str(e)})


def handle_users_detail(payload: dict) -> None:
    """获取用户详情。"""
    from AutoCCF.config import ConfigManager
    from AutoCCF.utils import UserPaths

    username = payload.get("username", "")
    if not username:
        emit("error", {"code": "INVALID_PAYLOAD", "message": "缺少 username 参数"})
        return

    cm = ConfigManager()
    config = cm.load()
    user_dir = config.get_user_dir(username)

    result = {
        "username": username,
        "user_dir": str(user_dir),
        "posts": [],
        "threads": [],
        "files": [],
    }

    if not user_dir.exists():
        emit("result", {"success": True, **result})
        return

    user_paths = UserPaths(config.database_dir, username)
    posts_file = user_paths.get_posts_file()
    if posts_file is not None:
        try:
            with open(posts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                result["posts"] = data
            elif isinstance(data, dict):
                result["posts"] = data.get("posts", [])
        except (json.JSONDecodeError, OSError):
            pass

    index_file = user_dir / "dopj" / "index.json"
    if not index_file.exists():
        index_file = user_dir / "index.json"

    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            for entry in index_data.get("entries", []):
                result["threads"].append(
                    {
                        "tid": entry.get("tid"),
                        "title": entry.get("title", ""),
                        "status": entry.get("status", "unknown"),
                    }
                )
        except (json.JSONDecodeError, OSError):
            pass
    else:
        scan_dirs = [user_dir / "dopj", user_dir / "threads"]
        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue
            for sub in sorted(scan_dir.iterdir()):
                if not (sub.is_dir() and sub.name.isdigit()):
                    continue
                tid = int(sub.name)
                title = ""
                thread_json = sub / "thread.json"
                if not thread_json.exists():
                    thread_json = sub / "threads" / sub.name / "thread.json"
                if thread_json.exists():
                    try:
                        with open(thread_json, "r", encoding="utf-8") as f:
                            thread_data = json.load(f)
                        title = thread_data.get("title", "")
                    except Exception:
                        pass
                result["threads"].append({"tid": tid, "title": title, "status": "unknown"})
            if result["threads"]:
                break

    try:
        for entry in sorted(user_dir.iterdir()):
            if entry.is_dir():
                size_text = f"{sum(1 for _ in entry.iterdir())} 项"
            else:
                size_bytes = entry.stat().st_size
                if size_bytes < 1024:
                    size_text = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_text = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_text = f"{size_bytes / 1024 / 1024:.1f} MB"

            result["files"].append(
                {
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "size_text": size_text,
                }
            )
    except OSError:
        pass

    emit("result", {"success": True, **result})


def handle_apou_outputs(payload: dict) -> None:
    """查找所有 APoU 输出文件。"""
    del payload
    from AutoCCF.config import ConfigManager

    cm = ConfigManager()
    cm.load()
    try:
        outputs = cm.find_apou_outputs()
        emit("result", {"success": True, "outputs": outputs})
    except Exception as e:
        emit("error", {"code": "APOU_OUTPUTS_ERROR", "message": str(e)})


ACTION_HANDLERS = {
    "config:load": handle_config_load,
    "config:save": handle_config_save,
    "apou:crawl": handle_apou_crawl,
    "apou:outputs": handle_apou_outputs,
    "dopj:crawl": handle_dopj_crawl,
    "users:list": handle_users_list,
    "users:detail": handle_users_detail,
}


def main() -> None:
    """入口：读取 stdin JSON 并路由到处理函数。"""
    try:
        raw_input = sys.stdin.read().strip()
        if not raw_input:
            emit("error", {"code": "EMPTY_INPUT", "message": "未收到输入"})
            return

        try:
            request = json.loads(raw_input)
        except json.JSONDecodeError as e:
            emit("error", {"code": "INVALID_JSON", "message": f"JSON 解析失败: {e}"})
            return

        action = request.get("action", "")
        payload = request.get("payload", {})

        handler = ACTION_HANDLERS.get(action)
        if handler is None:
            emit("error", {"code": "UNKNOWN_ACTION", "message": f"未知操作: {action}"})
            return

        handler(payload)
    except Exception as e:
        emit("error", {"code": "INTERNAL_ERROR", "message": f"内部错误: {e}"})


if __name__ == "__main__":
    main()
