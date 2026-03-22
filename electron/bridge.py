"""
AutoCCF Python Bridge

Electron 与 Python 业务逻辑之间的通信桥接层。
从 stdin 读取 JSON 请求，将结果/进度以 NDJSON 写入 stdout。
"""
import io
import json
import sys
import os
import asyncio
from typing import Any, TextIO

# 将项目根目录加入 sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ── stdout 重定向：防止裸 print() 污染 NDJSON 通道 ──
_real_stdout: TextIO = sys.stdout


class _NdjsonStdoutWrapper(io.TextIOBase):
    """拦截所有 print() 调用，将其包装为 NDJSON log 事件"""

    def __init__(self, real_stdout: TextIO) -> None:
        self._real = real_stdout

    def write(self, s: str) -> int:
        text = s.strip()
        if text:  # 忽略空行和纯换行
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
    """输出一行 NDJSON 到真实 stdout"""
    line = json.dumps({"type": msg_type, "data": data}, ensure_ascii=False)
    _real_stdout.write(line + "\n")
    _real_stdout.flush()


def handle_config_load(payload: dict) -> None:
    """加载配置文件，返回完整 BDUSS（掩码在 renderer 端处理）"""
    from AutoCCF.config import ConfigManager
    cm = ConfigManager()
    try:
        config = cm.load()  # 始终返回 UnifiedConfig（不返回 None）
        emit("result", {
            "success": True,
            "config": {
                "database_dir": config.database_dir,
                "accounts": [{"name": a.name, "bduss": a.bduss} for a in config.accounts],
                "apou": {"page_delay": config.apou.page_delay, "max_retries": config.apou.max_retries},
                "dopj": {
                    "threads": config.dopj.threads,
                    "max_retries": config.dopj.max_retries,
                    "min_interval": config.dopj.min_interval,
                    "max_fails": config.dopj.max_fails,
                },
            },
        })
    except Exception as e:
        emit("error", {"code": "CONFIG_ERROR", "message": str(e)})


def handle_config_save(payload: dict) -> None:
    """保存配置 — load-mutate-save 模式，保留 config_path"""
    from AutoCCF.config import ConfigManager, UnifiedConfig
    try:
        # 1. Load：先加载现有配置以获取 config_path
        cm = ConfigManager()
        existing = cm.load()
        original_path = existing.config_path

        # 2. Mutate：用 payload 创建新配置，但保留原始 config_path
        new_config = UnifiedConfig.from_dict(payload, config_path=original_path)

        # 3. Save：保存到原始路径
        saved_path = new_config.save()
        emit("result", {"success": True, "path": saved_path})
    except Exception as e:
        emit("error", {"code": "CONFIG_SAVE_ERROR", "message": str(e)})


def handle_apou_crawl(payload: dict) -> None:
    """执行 APoU 爬取"""
    from APoU.crawler import UserPostsCrawler
    from APoU.config import CrawlerConfig
    from AutoCCF.config import ConfigManager

    username = payload.get("username", "")
    if not username:
        emit("error", {"code": "INVALID_PAYLOAD", "message": "缺少 username 参数"})
        return

    # 加载配置获取 BDUSS 和其他参数
    cm = ConfigManager()
    config = cm.load()
    bduss = ""
    output_dir = config.database_dir
    page_delay = config.apou.page_delay
    max_retries = config.apou.max_retries

    # 选取第一个有效 BDUSS（非空且非全空格），而非盲目取 accounts[0]
    for account in config.accounts:
        if account.bduss and account.bduss.strip():
            bduss = account.bduss
            break

    crawler_config = CrawlerConfig(
        page_delay=page_delay,
        max_retries=max_retries,
        bduss=bduss,
    )

    def on_page_complete(page_num: int, posts_count: int) -> None:
        """每页完成回调 — posts_count 是当页获取的帖子数（非累计值），renderer 负责累加"""
        emit("progress", {
            "page": page_num,
            "posts_count": posts_count,
            "message": f"第 {page_num} 页: 本页 {posts_count} 条",
        })

    def on_log(message: str, level: str) -> None:
        emit("log", {"level": level, "message": message})

    # 创建 dummy cli 对象：阻止 _print() 在 cli=None 时 fallthrough 到 print()
    # 这样 on_log 回调是唯一的日志通道，避免日志重复
    class _DummyCli:
        """桩对象 — 接收 _print() 的 cli 分支调用，但不输出任何内容"""
        def info(self, msg: str) -> None: pass
        def warning(self, msg: str) -> None: pass
        def error(self, msg: str) -> None: pass
        def success(self, msg: str) -> None: pass

    crawler = UserPostsCrawler(
        config=crawler_config,
        on_page_complete=on_page_complete,
        on_log=on_log,
        cli=_DummyCli(),  # 传 dummy cli 防止 _print() fallthrough 到 print()
    )

    from AutoCCF.utils import UserPaths
    user_paths = UserPaths(output_dir, username)
    apou_dir = str(user_paths.apou_dir)

    try:
        posts = asyncio.run(crawler.crawl(
            username=username,
            output_dir=apou_dir,
        ))
        emit("result", {
            "success": True,
            "posts_count": len(posts),
            "output_file": str(user_paths.posts_file),
        })
    except Exception as e:
        emit("error", {"code": "APOU_ERROR", "message": str(e)})


def handle_dopj_crawl(payload: dict) -> None:
    """执行 DoPJ 爬取 — 在 worker 线程运行 runner.run()，主线程轮询 get_stats() 推送进度"""
    import threading
    import time as _time
    from DoPJ.cli import DoPJRunner
    from AutoCCF.config import ConfigManager
    from AutoCCF.utils import UserPaths

    input_json = payload.get("input_json", "")
    threads_override = payload.get("threads")  # 可选：从 payload 传入线程数

    if not input_json:
        emit("error", {"code": "INVALID_PAYLOAD", "message": "缺少 input_json 参数"})
        return

    cm = ConfigManager()
    config = cm.load()
    if not config.accounts:
        emit("error", {"code": "NO_ACCOUNTS", "message": "未配置账户"})
        return

    # 优先使用 payload 传入的 threads，否则回退到已保存配置
    threads = threads_override if threads_override is not None else config.dopj.threads

    # 从 input_json 路径推导 dopj 输出目录
    # input_json 格式: database_dir/username/apou/posts.json
    # 目标: database_dir/username/dopj/
    input_path = os.path.abspath(input_json)
    apou_dir = os.path.dirname(input_path)      # .../username/apou
    user_dir = os.path.dirname(apou_dir)         # .../username
    username = os.path.basename(user_dir)
    user_paths = UserPaths(config.database_dir, username)
    output_dir = str(user_paths.dopj_dir)

    # 构建 config_dict 格式（与 DoPJ/cli.py:707-711 一致）
    config_dict = {
        "accounts": [{"name": a.name, "bduss": a.bduss} for a in config.accounts],
        "min_interval": config.dopj.min_interval,
        "max_fails": config.dopj.max_fails,
    }

    try:
        # _BridgeCli 桩：将 DoPJRunner 的 CLI 调用转发为 NDJSON log 事件
        class _BridgeCli:
            """将 CLI 方法调用转发为 NDJSON log 事件"""
            def info(self, msg: str) -> None: emit("log", {"level": "info", "message": msg})
            def warning(self, msg: str) -> None: emit("log", {"level": "warning", "message": msg})
            def error(self, msg: str) -> None: emit("log", {"level": "error", "message": msg})
            def success(self, msg: str) -> None: emit("log", {"level": "info", "message": msg})
            def progress(self, msg: str) -> None: emit("log", {"level": "info", "message": msg})
            def print_section(self, title: str) -> None: pass
            def print_config(self, items: list[tuple[str, str]]) -> None: pass
            def print_task(self, **kw: object) -> None: pass
            def print_progress_bar(self, **kw: object) -> None: pass
            def clear_line(self) -> None: pass
            def format_duration(self, seconds: float) -> str: return f"{seconds:.1f}s"
            def print_stats_box(self, stats: list[tuple[str, str, str]]) -> None: pass
            def print_footer(self, message: str = "") -> None: pass

        runner = DoPJRunner(
            input_json=input_json,
            output_dir=output_dir,
            threads=min(threads, len(config.accounts)),
            max_retries=config.dopj.max_retries,
            config_dict=config_dict,
            cli=_BridgeCli(),
        )
        runner.load_tasks()

        # 在 worker 线程中运行 runner.run()（阻塞调用）
        worker_error: list[Exception] = []

        def _run_worker() -> None:
            try:
                runner.run()
            except Exception as exc:
                worker_error.append(exc)

        worker = threading.Thread(target=_run_worker, daemon=True)
        worker.start()

        # 主线程每 2 秒轮询 get_stats() 推送进度
        while worker.is_alive():
            worker.join(timeout=2.0)
            stats = runner.task_manager.get_stats()
            done = stats.get("success", 0) + stats.get("failed", 0) + stats.get("skipped", 0)
            emit("progress", {
                "success": stats.get("success", 0),
                "failed": stats.get("failed", 0),
                "pending": stats.get("pending", 0),
                "skipped": stats.get("skipped", 0),
                "total": stats.get("total", 0),
                "message": f"已完成 {done}/{stats.get('total', 0)}（成功 {stats.get('success', 0)}, 失败 {stats.get('failed', 0)}）",
            })

        # worker 结束后检查错误
        if worker_error:
            raise worker_error[0]

        stats = runner.task_manager.get_stats()
        emit("result", {
            "success": True,
            "stats": stats,
        })
    except Exception as e:
        emit("error", {"code": "DOPJ_ERROR", "message": str(e)})


def handle_users_list(payload: dict) -> None:
    """列出已爬取的用户"""
    from AutoCCF.config import ConfigManager
    import os
    cm = ConfigManager()
    cm.load()
    try:
        users = cm.list_users()
        for user in users:
            user_path = user.get("path", "")
            if user_path and os.path.isdir(user_path):
                try:
                    mtime = os.path.getmtime(user_path)
                    user["last_activity"] = mtime
                except OSError:
                    user["last_activity"] = None
            else:
                user["last_activity"] = None
        emit("result", {"success": True, "users": users})
    except Exception as e:
        emit("error", {"code": "USERS_LIST_ERROR", "message": str(e)})


def handle_users_detail(payload: dict) -> None:
    """获取用户详情"""
    username = payload.get("username", "")
    if not username:
        emit("error", {"code": "INVALID_PAYLOAD", "message": "缺少 username 参数"})
        return

    from AutoCCF.config import ConfigManager
    from AutoCCF.utils import UserPaths
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

    # 1. 加载 posts
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

    # 2. 加载 threads
    index_file = user_dir / "dopj" / "index.json"
    if not index_file.exists():
        index_file = user_dir / "index.json"
    if index_file.exists():
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            for entry in index_data.get("entries", []):
                result["threads"].append({
                    "tid": entry.get("tid"),
                    "title": entry.get("title", ""),
                    "status": entry.get("status", "unknown"),
                })
        except (json.JSONDecodeError, OSError):
            pass
    else:
        scan_dirs = [user_dir / "dopj", user_dir / "threads"]
        for scan_dir in scan_dirs:
            if scan_dir.exists():
                for sub in sorted(scan_dir.iterdir()):
                    if sub.is_dir() and sub.name.isdigit():
                        tid = int(sub.name)
                        title = ""
                        thread_json = sub / "thread.json"
                        if not thread_json.exists():
                            thread_json = sub / "threads" / sub.name / "thread.json"
                        if thread_json.exists():
                            try:
                                with open(thread_json, "r", encoding="utf-8") as f:
                                    t = json.load(f)
                                    title = t.get("title", "")
                            except Exception:
                                pass
                        result["threads"].append({"tid": tid, "title": title, "status": "unknown"})
                if result["threads"]:
                    break

    # 3. 列出 user_dir 根目录的文件和子目录
    try:
        for entry in sorted(user_dir.iterdir()):
            is_dir = entry.is_dir()
            if is_dir:
                size_text = f"{sum(1 for _ in entry.iterdir())} 项"
            else:
                size_bytes = entry.stat().st_size
                if size_bytes < 1024:
                    size_text = f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    size_text = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_text = f"{size_bytes / 1024 / 1024:.1f} MB"
            result["files"].append({
                "name": entry.name,
                "is_dir": is_dir,
                "size_text": size_text,
            })
    except OSError:
        pass

    emit("result", {"success": True, **result})


def handle_apou_outputs(payload: dict) -> None:
    """查找所有 APoU 输出文件"""
    from AutoCCF.config import ConfigManager
    cm = ConfigManager()
    cm.load()
    try:
        outputs = cm.find_apou_outputs()
        emit("result", {"success": True, "outputs": outputs})
    except Exception as e:
        emit("error", {"code": "APOU_OUTPUTS_ERROR", "message": str(e)})


# Action 路由表
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
    """主入口：读取 stdin JSON，路由到处理函数"""
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
