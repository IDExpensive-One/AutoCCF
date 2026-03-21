# Electron 迁移实现计划（修订版 v3.3）

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 AutoCCF 的 Flet GUI 替换为 Electron 桌面应用，保持 Python 业务逻辑不变，实现扁平化 Light 主题 UI，并完成 `团子传说` 用户 ID 的全流程 payload 测试。

**架构：** Electron Main Process 管理窗口和 Python 子进程（child_process.spawn），通过 JSON-over-stdio 协议通信。Renderer 使用原生 HTML/CSS/JS，通过 contextBridge 暴露的 window.api 调用后端。

**技术栈：** Electron 33+, Node.js 20+, Python 3.10+, Electron Forge

**规格文档：** `docs/superpowers/specs/2026-03-22-electron-migration-design.md`（v3）

**工作目录：** `.worktrees/electron-migration/`

---

## 文件结构

以下是将要创建或修改的文件及其职责：

| 文件 | 操作 | 职责 |
|------|------|------|
| `electron/package.json` | 创建 | Node.js 项目配置、Electron 依赖 |
| `electron/forge.config.js` | 创建 | Electron Forge 打包配置 |
| `electron/main.js` | 创建 | Electron 主进程：窗口管理、IPC、Python 子进程 |
| `electron/preload.js` | 创建 | contextBridge 安全桥接，暴露 window.api |
| `electron/bridge.py` | 创建 | Python CLI bridge：JSON stdin/stdout 协议 |
| `electron/renderer/index.html` | 创建 | 单页应用 HTML 入口 |
| `electron/renderer/styles/reset.css` | 创建 | CSS Reset |
| `electron/renderer/styles/variables.css` | 创建 | CSS 变量（颜色/间距/字体） |
| `electron/renderer/styles/layout.css` | 创建 | 侧边栏/内容区布局 |
| `electron/renderer/styles/components.css` | 创建 | 卡片/按钮/表单/表格/进度条 |
| `electron/renderer/js/app.js` | 创建 | 路由、视图切换、全局状态 |
| `electron/renderer/js/api.js` | 创建 | window.api 封装层 |
| `electron/renderer/js/views/home.js` | 创建 | 首页视图 |
| `electron/renderer/js/views/apou.js` | 创建 | APoU 爬取视图 |
| `electron/renderer/js/views/dopj.js` | 创建 | DoPJ 爬取视图 |
| `electron/renderer/js/views/users.js` | 创建 | 用户列表视图 |
| `electron/renderer/js/views/user-detail.js` | 创建 | 用户详情视图 |
| `electron/renderer/js/views/settings.js` | 创建 | 设置视图 |
| `tests/test_bridge/test_bridge.py` | 创建 | bridge.py 单元测试 |
| `tests/test_bridge/__init__.py` | 创建 | 测试包初始化 |
| `tests/test_e2e/test_payload.py` | 创建 | E2E payload 测试（团子传说） |
| `tests/test_e2e/__init__.py` | 创建 | 测试包初始化 |
| `tests/test_ipc/__init__.py` | 创建 | IPC 集成测试包初始化 |
| `tests/test_ipc/test_ipc_integration.py` | 创建 | IPC 集成测试（NDJSON 协议验证） |
| `tests/test_ui/__init__.py` | 创建 | UI 冒烟测试包初始化 |
| `tests/test_ui/test_smoke.js` | 创建 | Playwright UI 冒烟测试 |

---

## 任务 1：Electron 项目脚手架

**文件：**
- 创建：`electron/package.json`
- 创建：`electron/forge.config.js`
- 创建：`electron/main.js`（最小版本）
- 创建：`electron/preload.js`（最小版本）
- 创建：`electron/renderer/index.html`（最小版本）

- [ ] **步骤 1：创建 package.json**

```json
{
  "name": "autoccf",
  "version": "1.0.0",
  "description": "AutoCCF - 百度贴吧爬虫工具集",
  "main": "main.js",
  "scripts": {
    "start": "electron-forge start",
    "package": "electron-forge package",
    "make": "electron-forge make"
  },
  "devDependencies": {
    "@electron-forge/cli": "^7.0.0",
    "@electron-forge/maker-squirrel": "^7.0.0",
    "@electron-forge/maker-zip": "^7.0.0",
    "electron": "^33.0.0"
  },
  "dependencies": {}
}
```

- [ ] **步骤 2：创建 forge.config.js**

```javascript
module.exports = {
  packagerConfig: {
    asar: true,
    ignore: [
      /\.git/,
      /node_modules\/\.cache/,
    ],
    extraResource: [
      // Python bridge 和业务模块必须打包到 resources/ 下（asar 外），
      // 否则 child_process.spawn 无法访问
      '../bridge.py',
      '../APoU',
      '../DoPJ',
      '../AutoCCF',
      '../requirements.txt',
    ],
  },
  makers: [
    { name: '@electron-forge/maker-squirrel', config: {} },
    { name: '@electron-forge/maker-zip', platforms: ['darwin', 'linux'] },
  ],
};
```

- [ ] **步骤 3：创建最小 main.js**

创建 `electron/main.js`，包含：
- `BrowserWindow` 创建（1200x800）
- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`
- 加载 `preload.js`
- 加载 `renderer/index.html`
- `app.on('ready')` 和 `app.on('window-all-closed')` 处理

- [ ] **步骤 4：创建最小 preload.js**

创建 `electron/preload.js`，包含：
- `contextBridge.exposeInMainWorld('api', {})` 占位

- [ ] **步骤 5：创建最小 index.html**

创建 `electron/renderer/index.html`，包含：
- `<!DOCTYPE html>` 基本结构
- `<h1>AutoCCF</h1>` 占位内容
- Content-Security-Policy meta 标签

- [ ] **步骤 6：安装依赖并验证启动**

```bash
cd electron && npm install
npx electron .
```

预期：Electron 窗口打开，显示 "AutoCCF" 标题

- [ ] **步骤 7：Commit**

```bash
git add electron/
git commit -m "feat: 初始化 Electron 项目脚手架"
```

---

## 任务 2：Python Bridge（核心通信层）

**文件：**
- 创建：`electron/bridge.py`
- 创建：`tests/test_bridge/__init__.py`
- 创建：`tests/test_bridge/test_bridge.py`

- [ ] **步骤 1：编写 bridge.py 测试 — JSON 解析和路由**

```python
# tests/test_bridge/test_bridge.py
import json
import subprocess
import sys
import os

def run_bridge(action: str, payload: dict) -> list[dict]:
    """启动 bridge.py 子进程，发送请求，收集所有响应行"""
    bridge_path = os.path.join(os.path.dirname(__file__), '..', '..', 'electron', 'bridge.py')
    request = json.dumps({"action": action, "payload": payload})
    proc = subprocess.run(
        [sys.executable, bridge_path],
        input=request,
        capture_output=True,
        text=True,
        timeout=30,
    )
    responses = []
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            responses.append(json.loads(line))
    return responses

def test_unknown_action_returns_error():
    results = run_bridge("unknown:action", {})
    assert len(results) == 1
    assert results[0]["type"] == "error"
    assert "unknown" in results[0]["data"]["message"].lower()

def test_config_load_returns_result():
    results = run_bridge("config:load", {})
    assert len(results) >= 1
    last = results[-1]
    assert last["type"] in ("result", "error")

def test_invalid_json_handled():
    bridge_path = os.path.join(os.path.dirname(__file__), '..', '..', 'electron', 'bridge.py')
    proc = subprocess.run(
        [sys.executable, bridge_path],
        input="not valid json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    responses = []
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            responses.append(json.loads(line))
    assert len(responses) >= 1
    assert responses[0]["type"] == "error"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd .worktrees/electron-migration
python -m pytest tests/test_bridge/test_bridge.py -v
```

预期：FAIL，ModuleNotFoundError 或 FileNotFoundError

- [ ] **步骤 3：实现 bridge.py**

创建 `electron/bridge.py`，包含：

**关键 API 约束（必须遵循）：**
- `DoPJRunner.__init__` 使用 `input_json`（非 `input_file`），需要 `config_dict`（非 `accounts`/`on_log`）
- `DoPJRunner` 没有 `on_log` 回调；传 `cli=None` 即可避免 print 污染
- `ConfigManager` 没有 `save()` 方法；保存通过 `UnifiedConfig.save(path)` 实现
- `ConfigManager.load()` 始终返回 `UnifiedConfig`（从不返回 None）
- `ConfigManager.list_users()` 返回字段为 `"name"`（不是 `"username"`）
- `UserPaths` 已存在于 `AutoCCF/utils.py:90`，`from AutoCCF.utils import UserPaths` 可直接使用
- `config:load` 返回**完整 BDUSS**（掩码仅在 renderer 端处理）
- `UserPostsCrawler._print()` 即使传了 `on_log`，在 `cli=None` 时仍会 fallthrough 到 `print()`
- APoU 输出是**顶级 JSON 数组** `[post1, post2, ...]`

```python
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

    if not input_json:
        emit("error", {"code": "INVALID_PAYLOAD", "message": "缺少 input_json 参数"})
        return

    cm = ConfigManager()
    config = cm.load()
    if not config.accounts:
        emit("error", {"code": "NO_ACCOUNTS", "message": "未配置账户"})
        return

    threads = config.dopj.threads  # 从已保存设置读取线程数

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
        runner = DoPJRunner(
            input_json=input_json,  # 注意：参数名是 input_json 不是 input_file
            output_dir=output_dir,  # 使用 UserPaths.dopj_dir，不是 dirname(input_json)
            threads=min(threads, len(config.accounts)),
            max_retries=config.dopj.max_retries,
            config_dict=config_dict,  # 注意：使用 config_dict 不是 accounts
            cli=None,  # cli=None 防止 print 污染（DoPJRunner 内部有 if self.cli: 守卫）
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
            # 注意：get_stats() 返回 success/failed/pending/skipped/total（没有 completed）
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
    """列出已爬取的用户 — 使用 ConfigManager.list_users()，返回 'name' 字段（非 'username'）"""
    from AutoCCF.config import ConfigManager
    import os
    cm = ConfigManager()
    cm.load()
    try:
        users = cm.list_users()  # 返回 [{"name": ..., "path": ..., ...}]，注意字段是 "name" 不是 "username"
        # 为首页"最近活动时间"卡片补充 last_activity 字段
        # ConfigManager.list_users() 不返回时间戳，通过用户目录的 mtime 派生
        for user in users:
            user_path = user.get("path", "")
            if user_path and os.path.isdir(user_path):
                try:
                    mtime = os.path.getmtime(user_path)
                    user["last_activity"] = mtime  # Unix timestamp，renderer 端格式化
                except OSError:
                    user["last_activity"] = None
            else:
                user["last_activity"] = None
        emit("result", {"success": True, "users": users})
    except Exception as e:
        emit("error", {"code": "USERS_LIST_ERROR", "message": str(e)})


def handle_users_detail(payload: dict) -> None:
    """获取用户详情 — 返回 posts, threads, files 三个维度的数据"""
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

    # 1. 加载 posts（优先新路径 apou/posts.json，回退旧路径 posts.json）
    user_paths = UserPaths(config.database_dir, username)
    posts_file = user_paths.get_posts_file()  # 返回实际存在的路径，不存在返回 None
    if posts_file is not None:
        try:
            with open(posts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 兼容两种格式：顶级数组 或 {"posts": [...]}
                if isinstance(data, list):
                    result["posts"] = data
                elif isinstance(data, dict):
                    result["posts"] = data.get("posts", [])
        except (json.JSONDecodeError, OSError):
            pass

    # 2. 加载 threads（优先 dopj/index.json → 扫描 dopj/ → 扫描旧版 threads/）
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
        # 扫描 dopj/ 或旧版 threads/ 目录
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
                    break  # 找到数据就不再扫描旧版目录

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
    """查找所有 APoU 输出文件 — 使用 ConfigManager.find_apou_outputs()"""
    from AutoCCF.config import ConfigManager
    cm = ConfigManager()
    cm.load()
    try:
        outputs = cm.find_apou_outputs()
        # 返回格式: [{"username": "团子传说", "path": "/abs/path/posts.json", "posts_count": 142, "has_index": true}, ...]
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
```

- [ ] **步骤 4：运行测试验证通过**

```bash
python -m pytest tests/test_bridge/test_bridge.py -v
```

预期：3/3 PASS

- [ ] **步骤 5：Commit**

```bash
git add electron/bridge.py tests/test_bridge/
git commit -m "feat: 实现 Python bridge 通信层"
```

---

## 任务 3：Electron IPC 集成

**文件：**
- 修改：`electron/main.js`
- 修改：`electron/preload.js`

- [ ] **步骤 1：在 main.js 中添加 IPC handler**

在 `main.js` 中添加 `ipcMain.handle('bridge:invoke', ...)` 处理函数：

**Python 解释器发现（在 `app.whenReady()` 后执行）：**
- Windows：依次尝试 `py -3`、`python`
- POSIX (macOS/Linux)：依次尝试 `python3`、`python`
- 使用 `child_process.execFile` 运行 `--version` 验证候选解释器可用性
- 如果所有候选都失败，创建窗口后通过 `webContents.send('python:unavailable')` 通知 renderer 显示安装引导页面
- 将找到的解释器路径缓存为 `pythonCommand` 变量

**bridge.py 路径解析：**
- 开发模式：`path.join(__dirname, '..', 'electron', 'bridge.py')`（基于 `__dirname`）
- 生产模式：`path.join(process.resourcesPath, 'bridge.py')`（bridge.py 作为 `extraResources` 打包）
- 判断方式：`app.isPackaged`

**工作目录：**
- Python bridge 进程的 `cwd` 设为项目根目录：
  - 开发模式：`path.join(__dirname, '..')`（electron/ 的上级目录即项目根）
  - 生产模式：`process.resourcesPath`（extraResource 复制到此目录下，Python 模块目录 `APoU/`、`DoPJ/`、`AutoCCF/` 都在此）
  - 判断方式：`app.isPackaged`
- 确保 `sys.path.insert(0, PROJECT_ROOT)` 能正确找到 `APoU/`、`DoPJ/`、`AutoCCF/` 模块

**IPC handler 逻辑：**
- 接收 `{ action, payload }` 参数
- `child_process.spawn(pythonCommand, [bridgePath], { cwd: projectRoot })` 启动 Python
- 将 JSON 写入 stdin
- 逐行读取 stdout，解析 NDJSON
- `progress` 和 `log` 事件通过 `webContents.send()` 推送到 renderer
- `result` 或 `error` 作为 Promise 返回值
- **超时设置（与 spec 一致）：** APoU 操作（`apou:crawl`）设置 300 秒超时；DoPJ 操作（`dopj:crawl`）不设超时（取决于任务量）；非爬取操作（`config:load`、`config:save`、`users:list`、`users:detail`、`apou:outputs`）设置 30 秒超时
- **stderr 缓冲：** 逐行收集 `child.stderr` 内容到数组中缓冲。当进程非零退出时，将缓冲的 stderr 内容包含在 Promise reject 的错误信息中，便于 renderer 显示 Python traceback 等诊断信息
- 处理进程异常退出（非零退出码 → reject Promise with error，附带 stderr 缓冲内容）
- **不实现取消功能**（V1 规格明确不做取消，见 spec 2.1 功能清单）

- [ ] **步骤 2：在 preload.js 中暴露 API**

```javascript
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  invoke: (action, payload) => ipcRenderer.invoke('bridge:invoke', { action, payload }),
  onProgress: (callback) => {
    ipcRenderer.on('bridge:progress', (_event, data) => callback(data));
  },
  onLog: (callback) => {
    ipcRenderer.on('bridge:log', (_event, data) => callback(data));
  },
  onPythonUnavailable: (callback) => {
    ipcRenderer.on('python:unavailable', (_event) => callback());
  },
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  },
});
```

- [ ] **步骤 3：手动验证 IPC 通信**

在 `renderer/index.html` 中添加临时测试按钮：
```html
<button onclick="testBridge()">测试 Bridge</button>
<pre id="output"></pre>
<script>
async function testBridge() {
  const result = await window.api.invoke('config:load', {});
  document.getElementById('output').textContent = JSON.stringify(result, null, 2);
}
</script>
```

```bash
cd electron && npx electron .
```

预期：点击按钮后显示 config:load 的 JSON 响应

- [ ] **步骤 4：Commit**

```bash
git add electron/main.js electron/preload.js electron/renderer/index.html
git commit -m "feat: 实现 Electron IPC bridge 通信"
```

---

## 任务 4：CSS 样式系统

**文件：**
- 创建：`electron/renderer/styles/reset.css`
- 创建：`electron/renderer/styles/variables.css`
- 创建：`electron/renderer/styles/layout.css`
- 创建：`electron/renderer/styles/components.css`

**注意：** CSS 文件创建后可通过 `index.html` 引入验证语法正确性，但完整的视觉验证需要在任务 5（路由/HTML 结构）完成后进行。此任务的验收标准是 CSS 文件正确加载、无语法错误。

- [ ] **步骤 1：创建 reset.css**

使用标准 CSS reset（box-sizing, margin/padding reset, 字体 smoothing）。

- [ ] **步骤 2：创建 variables.css**

定义 CSS 自定义属性（规格 4.2 节的配色方案）：

```css
:root {
  /* 主色 */
  --color-primary: #2563EB;
  --color-primary-hover: #1D4ED8;
  /* 背景 */
  --color-bg: #F8FAFC;
  --color-card: #FFFFFF;
  /* 文字 */
  --color-text: #1E293B;
  --color-text-secondary: #64748B;
  /* 状态 */
  --color-success: #16A34A;
  --color-warning: #D97706;
  --color-error: #DC2626;
  /* 边框 */
  --color-border: #E2E8F0;
  /* 侧边栏 */
  --color-sidebar-bg: #1E293B;
  --color-sidebar-text: #CBD5E1;
  --color-sidebar-active: #FFFFFF;
  /* 间距 */
  --space-xs: 4px;
  --space-sm: 8px;
  --space-md: 16px;
  --space-lg: 24px;
  --space-xl: 32px;
  /* 圆角 */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  /* 阴影 */
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.1);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
  /* 字体 */
  --font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
  --font-size-sm: 13px;
  --font-size-md: 14px;
  --font-size-lg: 16px;
  --font-size-xl: 20px;
  --font-size-2xl: 24px;
}
```

- [ ] **步骤 3：创建 layout.css**

实现侧边栏 + 内容区布局：
- `body`: `display: flex; height: 100vh;`
- `.sidebar`: `width: 200px; background: var(--color-sidebar-bg);`
- `.main-content`: `flex: 1; overflow-y: auto; background: var(--color-bg);`
- 侧边栏导航项样式（未选中/选中/悬停）
- 页面标题区
- 状态栏

- [ ] **步骤 4：创建 components.css**

实现组件样式：
- `.card`: 卡片容器（背景白、圆角 8px、阴影）
- `.btn`, `.btn-primary`, `.btn-danger`: 按钮（扁平化、无边框、圆角）
- `.input`, `.select`: 输入框/下拉框
- `.slider`: 滑块
- `.table`: 表格（斑马纹、hover 效果）
- `.progress-bar`: 进度条
- `.badge`: 状态标签（成功/警告/错误）
- `.log-viewer`: 日志显示区（等宽字体、深色背景）
- `.tab-bar`, `.tab-item`: 标签页

- [ ] **步骤 5：更新 index.html 引入样式表**

```html
<link rel="stylesheet" href="styles/reset.css">
<link rel="stylesheet" href="styles/variables.css">
<link rel="stylesheet" href="styles/layout.css">
<link rel="stylesheet" href="styles/components.css">
```

- [ ] **步骤 6：验证样式渲染**

```bash
cd electron && npx electron .
```

预期：窗口显示侧边栏 + 内容区布局，样式扁平化

- [ ] **步骤 7：Commit**

```bash
git add electron/renderer/styles/
git commit -m "feat: 实现扁平化 CSS 样式系统"
```

---

## 任务 5：应用路由和 API 封装

**文件：**
- 创建：`electron/renderer/js/app.js`
- 创建：`electron/renderer/js/api.js`
- 修改：`electron/renderer/index.html`

- [ ] **步骤 1：创建 api.js**

封装 `window.api` 调用：

```javascript
// api.js - window.api 封装层
export const api = {
  config: {
    load: () => window.api.invoke('config:load', {}),
    save: (config) => window.api.invoke('config:save', config),
  },
  apou: {
    crawl: (username) => window.api.invoke('apou:crawl', { username }),  // 配置参数从已保存设置读取
    outputs: () => window.api.invoke('apou:outputs', {}),  // 查找所有 APoU 输出文件
  },
  dopj: {
    crawl: (inputJson) => window.api.invoke('dopj:crawl', { input_json: inputJson }),  // threads 等参数从已保存设置读取
  },
  users: {
    list: () => window.api.invoke('users:list', {}),
    detail: (username) => window.api.invoke('users:detail', { username }),
  },
  onProgress: (callback) => window.api.onProgress(callback),
  onLog: (callback) => window.api.onLog(callback),
  onPythonUnavailable: (callback) => window.api.onPythonUnavailable(callback),
};
```

- [ ] **步骤 2：创建 app.js**

实现单页路由：
- `Router` 类：管理视图切换
- `registerView(name, renderFn)`: 注册视图
- `navigate(name, params)`: 导航到视图
- 侧边栏点击事件绑定
- 初始加载首页
- **Python 不可用处理：** 注册 `api.onPythonUnavailable()` 监听器，收到事件后在 content 区域显示安装引导页面（提示用户安装 Python 3.10+，包含官方下载链接 `https://www.python.org/downloads/`），替换当前视图内容

```javascript
// app.js - 应用入口
class Router {
  constructor() {
    this.views = {};
    this.currentView = null;
    this.container = document.getElementById('content');
  }

  register(name, viewModule) {
    this.views[name] = viewModule;
  }

  async navigate(name, params = {}) {
    // 清理当前视图
    if (this.currentView && this.views[this.currentView]?.unmount) {
      this.views[this.currentView].unmount();
    }
    // 更新侧边栏选中状态
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.view === name);
    });
    // 渲染新视图
    this.container.innerHTML = '';
    this.currentView = name;
    if (this.views[name]?.mount) {
      await this.views[name].mount(this.container, params);
    }
  }
}
```

- [ ] **步骤 3：更新 index.html 结构**

完善 HTML 结构，包含：
- 侧边栏导航（首页/APoU/DoPJ/用户/设置）
- `<div id="content">` 内容容器
- 状态栏
- `<script type="module" src="js/app.js">` 入口

- [ ] **步骤 4：验证路由切换**

```bash
cd electron && npx electron .
```

预期：侧边栏点击切换视图，选中状态高亮

- [ ] **步骤 5：Commit**

```bash
git add electron/renderer/js/ electron/renderer/index.html
git commit -m "feat: 实现应用路由和 API 封装层"
```

---

## 任务 6：首页视图

**文件：**
- 创建：`electron/renderer/js/views/home.js`

- [ ] **步骤 1：实现首页**

首页包含：
- 页面标题："首页"
- 统计卡片行（3 列）：已爬取用户数、帖子总数、最近活动时间（从 `users:list` 响应中各用户的 `last_activity` 字段取最大值，格式化为相对时间如"2小时前"）
- 快捷操作区：两个大按钮卡片（开始 APoU、开始 DoPJ），点击后导航到对应视图
- 通过 `api.users.list()` 获取统计数据（响应包含 `last_activity` Unix 时间戳）

```javascript
export function mount(container, params) {
  // 渲染统计卡片
  // 绑定快捷操作按钮事件
}
export function unmount() {
  // 清理事件监听
}
```

- [ ] **步骤 2：验证首页渲染**

```bash
cd electron && npx electron .
```

预期：首页显示统计卡片和快捷操作按钮

- [ ] **步骤 3：Commit**

```bash
git add electron/renderer/js/views/home.js
git commit -m "feat: 实现首页视图"
```

---

## 任务 7：APoU 视图

**文件：**
- 创建：`electron/renderer/js/views/apou.js`

- [ ] **步骤 1：实现 APoU 视图**

APoU 视图包含：
- 页面标题："用户发言列表爬取 (APoU)"
- 用户名输入框 + "开始爬取" 按钮
- **不包含配置滑块** — 页面延迟、重试次数等参数统一在"设置"页面配置，爬取时直接读取已保存的配置
- 进度区卡片：进度条 + 状态文字（初始隐藏，爬取时显示）
- 实时日志区卡片：`.log-viewer` 滚动区域

功能：
- 点击"开始爬取"→ 调用 `api.apou.crawl(username)`
- 监听 `api.onProgress()` 更新进度条
- 监听 `api.onLog()` 追加日志
- 爬取完成后显示结果统计
- 爬取中禁用按钮，完成后恢复
- 进度条使用 indeterminate 模式（总页数未知），显示 "已爬取 X 条帖子" 实时计数

- [ ] **步骤 2：验证 APoU 视图**

```bash
cd electron && npx electron .
```

预期：APoU 视图显示所有控件，输入用户名可触发爬取

- [ ] **步骤 3：Commit**

```bash
git add electron/renderer/js/views/apou.js
git commit -m "feat: 实现 APoU 爬取视图"
```

---

## 任务 8：DoPJ 视图

**文件：**
- 创建：`electron/renderer/js/views/dopj.js`

- [ ] **步骤 1：实现 DoPJ 视图**

DoPJ 视图包含：
- 页面标题："帖子详情爬取 (DoPJ)"
- 用户选择下拉框（从 `api.apou.outputs()` 填充有 APoU 输出的用户，其中 `path` 字段直接作为 `dopj:crawl` 的 `input_json` 参数）
- **不包含配置滑块** — 线程数、重试次数、最小间隔等参数统一在"设置"页面配置，爬取时直接读取已保存的配置
- 账户状态表：显示每个 BDUSS 账户名 + 状态标签
- 进度区卡片：进度条 + 成功/失败/跳过统计
- 实时日志区

功能：
- 下拉框显示 `apou:outputs` 返回的用户列表（`username` + `posts_count`），选中后保存对应 `path` 值
- 点击"开始爬取"→ 调用 `api.dopj.crawl(selectedPath)`（`path` 来自 `apou:outputs` 的返回值，不在 renderer 中拼路径）
- 监听进度和日志事件
- 账户状态表从 `api.config.load()` 获取账户列表

- [ ] **步骤 2：验证 DoPJ 视图**

```bash
cd electron && npx electron .
```

预期：DoPJ 视图显示用户下拉框和配置控件

- [ ] **步骤 3：Commit**

```bash
git add electron/renderer/js/views/dopj.js
git commit -m "feat: 实现 DoPJ 爬取视图"
```

---

## 任务 9：用户列表和详情视图

**文件：**
- 创建：`electron/renderer/js/views/users.js`
- 创建：`electron/renderer/js/views/user-detail.js`

- [ ] **步骤 1：实现用户列表视图**

用户列表包含：
- 页面标题："用户管理"
- 搜索框（即时过滤表格）
- 用户表格：用户名 | 帖子数 | DoPJ 状态 | 操作
- 操作列："查看详情" 按钮 → 导航到 user-detail 视图
- 通过 `api.users.list()` 加载数据

- [ ] **步骤 2：实现用户详情视图**

用户详情包含：
- 返回按钮 → 回到用户列表
- 用户信息头部：用户名、帖子数统计、用户目录路径
- 标签页切换：帖子列表 / 主题列表 / 文件浏览（三个标签页）
- **帖子标签页**：帖子表格 — 标题 | 贴吧 | 时间 | 链接
- **主题标签页**：主题表格 — TID | 标题 | 状态（从 `detail.threads` 渲染）
- **文件标签页**：文件/目录列表 — 名称 | 类型 | 大小（从 `detail.files` 渲染）
- 通过 `api.users.detail(username)` 加载数据
- 返回数据包含 `username`、`user_dir`、`posts`、`threads`、`files` 五个字段

- [ ] **步骤 3：验证用户视图**

```bash
cd electron && npx electron .
```

预期：用户列表显示表格，点击查看详情能导航并显示帖子列表

- [ ] **步骤 4：Commit**

```bash
git add electron/renderer/js/views/users.js electron/renderer/js/views/user-detail.js
git commit -m "feat: 实现用户列表和详情视图"
```

---

## 任务 10：设置视图

**文件：**
- 创建：`electron/renderer/js/views/settings.js`

- [ ] **步骤 1：实现设置视图**

设置视图包含：
- 页面标题："设置"
- 数据库目录配置卡片：路径显示 + "选择目录" 按钮
- 账户管理卡片：
  - 账户列表表格（名称 | BDUSS 预览 | 操作）
  - "添加账户" 按钮 → 展开表单（名称、BDUSS 输入框）
  - 编辑/删除按钮
- APoU 配置卡片：页面延迟滑块、最大重试次数滑块
- DoPJ 配置卡片：线程数、最大重试、最小间隔、最大失败数 滑块
- 底部操作栏："保存设置" / "重置" 按钮

功能：
- 页面加载时调用 `api.config.load()` 填充所有字段
- "保存设置" → 调用 `api.config.save(formData)`
- 显示保存成功/失败提示

注意：目录选择器需要通过 IPC 调用 Electron 的 `dialog.showOpenDialog()`，需要在 main.js 中添加 `ipcMain.handle('dialog:openDirectory')` 并在 preload.js 中暴露。

- [ ] **步骤 2：更新 main.js 和 preload.js 添加目录选择器**

main.js 添加：
```javascript
ipcMain.handle('dialog:openDirectory', async () => {
  const result = await dialog.showOpenDialog({ properties: ['openDirectory'] });
  return result.filePaths[0] || null;
});
```

preload.js 添加：
```javascript
selectDirectory: () => ipcRenderer.invoke('dialog:openDirectory'),
```

- [ ] **步骤 3：验证设置视图**

```bash
cd electron && npx electron .
```

预期：设置页面加载配置，修改后可保存

- [ ] **步骤 4：Commit**

```bash
git add electron/renderer/js/views/settings.js electron/main.js electron/preload.js
git commit -m "feat: 实现设置视图和目录选择器"
```

---

## 任务 11：E2E Payload 集成测试

> **注意**：此任务包含**集成测试**，需要有效的网络连接和 BDUSS 配置才能运行。
> 这些测试会实际发起网络请求到百度贴吧 API，不适合 CI 自动运行。
> DoPJ 测试会触发完整爬取（非仅 1 个线程），耗时可能较长。
> 需要安装 pytest-timeout 插件：`pip install pytest-timeout`

**文件：**
- 创建：`tests/test_e2e/__init__.py`
- 创建：`tests/test_e2e/conftest.py`
- 创建：`tests/test_e2e/test_payload.py`

- [ ] **步骤 1：创建 conftest.py 和编写 payload 测试**

```python
# tests/test_e2e/conftest.py
"""E2E 集成测试配置 — 注册自定义 marker"""
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: 需要网络连接和有效 BDUSS 配置的集成测试"
    )
```

```python
# tests/test_e2e/test_payload.py
"""
E2E Payload 集成测试 — 使用用户 ID '团子传说' 验证完整流程

⚠️ 这是集成测试，需要：
  1. 有效的 config.json 配置（包含 BDUSS 账户）
  2. 可访问百度贴吧 API 的网络连接
  3. pytest-timeout 插件（pip install pytest-timeout）

如果配置不存在、BDUSS 无效或网络不可达，测试将被跳过。
运行方式：python -m pytest tests/test_e2e/test_payload.py -v -m integration
"""
import json
import os
import socket
import subprocess
import sys
import pytest

BRIDGE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'electron', 'bridge.py')
TARGET_USERNAME = "团子传说"


def _network_available(host: str = "tieba.baidu.com", port: int = 443, timeout: float = 3.0) -> bool:
    """检查是否有网络连接到百度贴吧"""
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def run_bridge(action: str, payload: dict, timeout: int = 120) -> list[dict]:
    """运行 bridge.py 并收集响应"""
    request = json.dumps({"action": action, "payload": payload})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    responses = []
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            responses.append(json.loads(line))
    return responses


def has_valid_config() -> bool:
    """检查是否有有效配置"""
    try:
        results = run_bridge("config:load", {}, timeout=10)
        if results and results[-1].get("type") == "result":
            data = results[-1].get("data", {})
            return data.get("success", False) and len(data.get("config", {}).get("accounts", [])) > 0
    except Exception:
        pass
    return False


_skip_no_config = pytest.mark.skipif(not has_valid_config(), reason="需要有效的 config.json 配置（含 BDUSS）")
_skip_no_network = pytest.mark.skipif(not _network_available(), reason="无法连接到 tieba.baidu.com，跳过集成测试")


@pytest.mark.integration
@_skip_no_config
@_skip_no_network
class TestAPoUPayload:
    """APoU 爬取 payload 集成测试"""

    def test_apou_crawl_returns_posts(self):
        """测试 APoU 爬取 '团子传说' 用户的发言"""
        results = run_bridge("apou:crawl", {"username": TARGET_USERNAME}, timeout=120)

        # 应该有 progress 事件（使用 page/posts_count 字段，与 spec 契约一致）
        progress_events = [r for r in results if r["type"] == "progress"]
        assert len(progress_events) > 0, "应该收到 progress 事件"
        # 验证 progress 事件格式
        for p in progress_events:
            assert "page" in p["data"], "progress 应包含 page 字段"
            assert "posts_count" in p["data"], "progress 应包含 posts_count 字段（每页帖子数）"

        # 最后一条应该是 result
        last = results[-1]
        assert last["type"] == "result", f"最后一条应该是 result，实际为: {last}"
        assert last["data"]["success"] is True
        assert last["data"]["posts_count"] > 0, "应该爬取到帖子"
        assert "output_file" in last["data"]

        # 验证输出文件是顶级 JSON 数组格式
        output_file = last["data"]["output_file"]
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list), f"APoU 输出应为顶级 JSON 数组，实际类型: {type(data)}"
            if len(data) > 0:
                assert "tid" in data[0], "每条帖子应包含 tid 字段"
                assert "title" in data[0], "每条帖子应包含 title 字段"
                assert "href" in data[0], "每条帖子应包含 href 字段"


@pytest.mark.integration
@_skip_no_config
@_skip_no_network
class TestDoPJPayload:
    """DoPJ 爬取 payload 集成测试（在 APoU 爬取后运行）

    注意：此测试会触发 DoPJ 的完整爬取流程（所有线程），耗时可能较长。
    """

    def test_dopj_crawl_succeeds(self):
        """测试 DoPJ 爬取帖子详情"""
        # 首先获取 APoU 输出文件路径
        users_results = run_bridge("users:list", {}, timeout=10)
        last = users_results[-1]
        if last["type"] != "result":
            pytest.skip("无法获取用户列表")
        users = last["data"].get("users", [])
        target_user = None
        for u in users:
            if u.get("name") == TARGET_USERNAME:  # 注意：list_users() 返回 "name" 字段
                target_user = u
                break
        if target_user is None:
            pytest.skip(f"数据库中没有用户 '{TARGET_USERNAME}'，需先运行 APoU 测试")

        # 获取 input_json 路径 — 使用 get_posts_file() 兼容新旧路径
        from AutoCCF.config import ConfigManager
        from AutoCCF.utils import UserPaths
        cm = ConfigManager()
        config = cm.load()
        user_paths = UserPaths(config.database_dir, TARGET_USERNAME)
        posts_file = user_paths.get_posts_file()  # 返回实际存在的路径（新或旧），不存在返回 None

        if posts_file is None:
            pytest.skip(f"APoU 输出文件不存在（已检查新旧路径）")

        input_json = str(posts_file)

        results = run_bridge(
            "dopj:crawl",
            {"input_json": input_json},  # threads 从已保存配置读取
            timeout=300,
        )

        last = results[-1]
        assert last["type"] == "result", f"最后一条应该是 result，实际为: {last}"
        assert last["data"]["success"] is True
        stats = last["data"]["stats"]
        assert stats.get("total", 0) > 0, "应该有任务"


@pytest.mark.integration
@_skip_no_config
@_skip_no_network
class TestUsersPayload:
    """用户列表 payload 集成测试（在 APoU 爬取后运行）"""

    def test_users_list_contains_target(self):
        """测试用户列表包含目标用户"""
        results = run_bridge("users:list", {})
        last = results[-1]
        assert last["type"] == "result"
        users = last["data"]["users"]
        names = [u["name"] for u in users]  # 注意：字段是 "name" 不是 "username"
        # 注意：此测试假设 APoU 测试已先运行
        if TARGET_USERNAME not in names:
            pytest.skip(f"数据库中没有用户 '{TARGET_USERNAME}'")

    def test_user_detail_has_posts(self):
        """测试用户详情包含帖子数据"""
        results = run_bridge("users:detail", {"username": TARGET_USERNAME})
        last = results[-1]
        if last["type"] == "error":
            pytest.skip("用户数据不存在")
        assert last["type"] == "result"
        # users:detail 返回顶级字段（与 spec schema 一致），不包裹在 "detail" 中
        data = last["data"]
        assert data["username"] == TARGET_USERNAME
        # 验证帖子是列表格式
        assert isinstance(data["posts"], list), "帖子应为列表格式"
```

- [ ] **步骤 2：运行 E2E 集成测试**

```bash
cd .worktrees/electron-migration
pip install pytest-timeout  # 如未安装
python -m pytest tests/test_e2e/test_payload.py -v -m integration --timeout=300
```

预期：如果有有效 config.json 且网络可达，APoU 爬取成功并返回帖子；否则测试被跳过

- [ ] **步骤 3：Commit**

```bash
git add tests/test_e2e/
git commit -m "test: 添加 E2E payload 测试（团子传说）"
```

---

## 任务 12：IPC 集成测试

**文件：**
- 创建：`tests/test_ipc/__init__.py`
- 创建：`tests/test_ipc/test_ipc_integration.py`

- [ ] **步骤 1：编写 IPC 集成测试**

测试 Electron spawn Python bridge 的完整通信链路：

```python
# tests/test_ipc/test_ipc_integration.py
"""
IPC 集成测试 — 验证 bridge.py 的 NDJSON 协议和进程生命周期

不需要 Electron 环境，直接通过 subprocess 模拟 main.js 的行为。
"""
import json
import os
import subprocess
import sys
import time
import pytest

BRIDGE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'electron', 'bridge.py')

def test_ndjson_format_validity():
    """验证所有输出行都是有效的 NDJSON"""
    request = json.dumps({"action": "config:load", "payload": {}})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=10,
    )
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            parsed = json.loads(line)  # 如果不是有效 JSON 会抛异常
            assert "type" in parsed, "每行必须包含 type 字段"
            assert "data" in parsed, "每行必须包含 data 字段"
            assert parsed["type"] in ("result", "error", "progress", "log")

def test_process_exits_cleanly():
    """验证 bridge.py 处理完请求后正常退出"""
    request = json.dumps({"action": "config:load", "payload": {}})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, f"进程应正常退出，实际退出码: {proc.returncode}"

def test_stderr_does_not_contain_ndjson():
    """验证 stderr 不包含 NDJSON（stdout 专用）"""
    request = json.dumps({"action": "config:load", "payload": {}})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=10,
    )
    for line in proc.stderr.strip().splitlines():
        if line.strip():
            # stderr 行不应该是 NDJSON 格式
            try:
                parsed = json.loads(line)
                if "type" in parsed and "data" in parsed:
                    pytest.fail(f"stderr 不应包含 NDJSON: {line}")
            except json.JSONDecodeError:
                pass  # stderr 可以包含非 JSON 内容（如 Python warnings）

def test_stdout_not_polluted_by_print():
    """验证 stdout 拦截器将裸 print() 包装为 log 事件"""
    request = json.dumps({"action": "config:load", "payload": {}})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=10,
    )
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            # 所有 stdout 行必须是有效 JSON
            try:
                json.loads(line)
            except json.JSONDecodeError:
                pytest.fail(f"stdout 中发现非 JSON 行（stdout 污染）: {line[:100]}")

def test_timeout_handling():
    """验证进程在收到空输入时快速退出"""
    start = time.time()
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input="",
        capture_output=True,
        text=True,
        timeout=10,
    )
    elapsed = time.time() - start
    assert elapsed < 5, f"空输入应快速退出，实际耗时: {elapsed:.1f}s"
    responses = [json.loads(line) for line in proc.stdout.strip().splitlines() if line.strip()]
    assert len(responses) >= 1
    assert responses[0]["type"] == "error"
```

- [ ] **步骤 2：运行 IPC 集成测试**

```bash
cd .worktrees/electron-migration
python -m pytest tests/test_ipc/test_ipc_integration.py -v
```

预期：所有测试通过

- [ ] **步骤 3：Commit**

```bash
git add tests/test_ipc/
git commit -m "test: 添加 IPC 集成测试"
```

---

## 任务 13：UI 冒烟测试（Playwright）

**文件：**
- 创建：`tests/test_ui/__init__.py`
- 创建：`tests/test_ui/test_smoke.js`

**注意：** 此任务需要 Playwright 和 electron 同时安装。如果 Playwright 环境不可用，此任务标记为 `[blocked]`，不阻塞其他任务。

- [ ] **步骤 1：编写 Playwright 冒烟测试**

创建 `tests/test_ui/test_smoke.js`（使用 Playwright Electron 支持）：

```javascript
// tests/test_ui/test_smoke.js
const { test, expect, _electron: electron } = require('@playwright/test');
const path = require('path');

let app;

test.beforeAll(async () => {
  app = await electron.launch({
    args: [path.join(__dirname, '..', '..', 'electron', 'main.js')],
  });
});

test.afterAll(async () => {
  await app.close();
});

test('窗口标题包含 AutoCCF', async () => {
  const page = await app.firstWindow();
  const title = await page.title();
  expect(title).toContain('AutoCCF');
});

test('侧边栏包含所有导航项', async () => {
  const page = await app.firstWindow();
  const navItems = await page.locator('.nav-item').allTextContents();
  expect(navItems).toContain('首页');
  expect(navItems).toContain('APoU');
  expect(navItems).toContain('DoPJ');
  expect(navItems).toContain('用户');
  expect(navItems).toContain('设置');
});

test('导航切换到 APoU 视图', async () => {
  const page = await app.firstWindow();
  await page.click('[data-view="apou"]');
  await expect(page.locator('#content')).toContainText('APoU');
});

test('导航切换到设置视图', async () => {
  const page = await app.firstWindow();
  await page.click('[data-view="settings"]');
  await expect(page.locator('#content')).toContainText('设置');
});

test('APoU 视图有用户名输入框', async () => {
  const page = await app.firstWindow();
  await page.click('[data-view="apou"]');
  const input = page.locator('input[placeholder*="用户名"]');
  await expect(input).toBeVisible();
});

test('所有 5 个视图可渲染', async () => {
  const page = await app.firstWindow();
  const views = ['home', 'apou', 'dopj', 'users', 'settings'];
  for (const view of views) {
    await page.click(`[data-view="${view}"]`);
    // 确保内容区不为空
    const content = await page.locator('#content').textContent();
    expect(content.trim().length).toBeGreaterThan(0);
  }
});

test('user-detail 视图可通过导航渲染', async () => {
  // user-detail 不在 sidebar 中，通过 users 列表项点击导航到达
  const page = await app.firstWindow();
  await page.click('[data-view="users"]');
  // 如果有用户条目则点击进入详情；否则仅验证 users 视图已渲染
  const userItem = page.locator('.user-item').first();
  if (await userItem.isVisible({ timeout: 2000 }).catch(() => false)) {
    await userItem.click();
    await expect(page.locator('#content')).toContainText('帖子');  // user-detail 有"帖子"标签页
  }
});

test('APoU 视图有 indeterminate 进度条', async () => {
  // spec 要求验证 APoU indeterminate 进度条正确显示
  const page = await app.firstWindow();
  await page.click('[data-view="apou"]');
  // 进度条初始应存在但隐藏（爬取未开始时）
  const progressBar = page.locator('.progress-bar, progress');
  // 验证进度元素存在于 DOM 中
  await expect(progressBar.first()).toHaveCount(1);
});
```

- [ ] **步骤 2：安装 Playwright 依赖**

```bash
cd electron
npm install --save-dev @playwright/test
npx playwright install
```

- [ ] **步骤 3：运行冒烟测试**

```bash
cd electron
npx playwright test ../tests/test_ui/test_smoke.js
```

预期：所有 5 个侧边栏视图冒烟测试通过，user-detail 可选通过（取决于是否有用户数据），APoU 进度条元素存在

- [ ] **步骤 4：Commit**

```bash
git add tests/test_ui/ electron/package.json
git commit -m "test: 添加 Playwright UI 冒烟测试"
```

---

## 任务 14：集成验证和清理

**文件：**
- 修改：`electron/renderer/index.html`（移除临时测试代码）
- 可能修改：所有视图文件（修复集成问题）

- [ ] **步骤 1：移除临时测试代码**

从 `index.html` 中移除任务 3 的临时测试按钮和脚本。

- [ ] **步骤 2：完整启动测试**

```bash
cd electron && npx electron .
```

预期：
- 首页显示统计数据（包含最近活动时间）
- 侧边栏导航切换 5 个视图（首页、APoU、DoPJ、用户、设置）
- 用户列表点击可导航到 user-detail 视图（第 6 个视图）
- APoU 视图可输入用户名并触发爬取
- DoPJ 视图可选择用户并触发爬取
- 用户列表显示已爬取用户
- 设置页面可加载/保存配置

- [ ] **步骤 3：运行所有测试（逐文件串行执行）**

```bash
# Bridge 单元测试
python -m pytest tests/test_bridge/test_bridge.py -v

# IPC 集成测试
python -m pytest tests/test_ipc/test_ipc_integration.py -v

# E2E payload 集成测试（需要有效配置和网络，可能跳过）
python -m pytest tests/test_e2e/test_payload.py -v -m integration --timeout=300

# Playwright UI 冒烟测试（需要 Playwright 环境，可能跳过）
cd electron && npx playwright test ../tests/test_ui/test_smoke.js
```

注意：严格逐文件串行运行，禁止使用目录级 `pytest tests/` 命令。

预期：bridge 和 IPC 测试全部通过，E2E 测试通过（或因缺少配置被跳过），Playwright 冒烟测试通过（或因环境不可用被跳过）

- [ ] **步骤 4：Commit**

```bash
git add -A
git commit -m "chore: 集成验证和清理临时测试代码"
```

---

## 依赖关系

```
任务 1 (脚手架)
  └→ 任务 2 (Bridge)
  └→ 任务 3 (IPC) ← 依赖任务 2
  └→ 任务 4 (CSS)
  └→ 任务 5 (路由/API) ← 依赖任务 3, 4
      └→ 任务 6 (首页) ← 依赖任务 5
      └→ 任务 7 (APoU) ← 依赖任务 5
      └→ 任务 8 (DoPJ) ← 依赖任务 5
      └→ 任务 9 (用户) ← 依赖任务 5
      └→ 任务 10 (设置) ← 依赖任务 5
  └→ 任务 11 (E2E 测试) ← 依赖任务 2
  └→ 任务 12 (IPC 集成测试) ← 依赖任务 2
  └→ 任务 13 (Playwright 冒烟测试) ← 依赖任务 5-10
  └→ 任务 14 (集成验证) ← 依赖所有
```

注意：任务 1/2/4 可以并行执行（无依赖）。任务 6-10 必须在任务 5 之后，但它们之间可以串行（共享 UI 框架）。任务 11 和 12 只依赖任务 2（bridge.py），可以与 UI 任务并行。任务 13 需要所有 UI 视图就位后才能运行。
