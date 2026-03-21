# Electron 迁移设计规格

> **日期**: 2026-03-22
> **状态**: 设计中（修订版 v2）
> **范围**: 将现有 Flet GUI 替换为 Electron 桌面应用，保留 Python 业务逻辑不变

## 1. 背景与目标

AutoCCF 是百度贴吧爬虫工具集，采用两步式设计：APoU（获取用户发言列表）和 DoPJ（获取帖子详情）。当前 GUI 使用 Python Flet 框架（`gui/` 目录，19 个 .py 文件），包含 6 个视图、4 个组件、2 个 worker 线程。

**迁移目标：**
1. 将 Flet GUI 替换为 Electron 桌面应用
2. 实现扁平化、Light 主题的现代 UI
3. 保持 Python 业务逻辑（APoU, DoPJ, AutoCCF）完全不变
4. 支持全流程 payload 测试（用户 ID：`团子传说`）

**不在范围内：**
- 移动端适配
- 自动更新机制
- 多语言国际化
- 云同步
- Python 业务逻辑重构

### 1.1 功能对照表（Flet → Electron）

下表明确列出现有 Flet GUI 的每个功能在 Electron 中的处理方式：

| 现有 Flet 功能 | Electron 中的处理 | 说明 |
|---|---|---|
| APoU 爬取 + 进度 | ✅ 保留 | 保留输入、进度条、日志显示 |
| DoPJ 爬取 + 进度 | ✅ 保留 | 保留用户选择、线程配置、进度 |
| 停止/取消按钮 | ❌ 不实现（V1） | 每任务一进程模型下，取消需杀进程，V1 阶段不实现 |
| 验证/修复模式 | ❌ 不实现（V1） | DoPJ 的增量跳过已覆盖此功能 |
| 用户列表 + 搜索 | ✅ 保留 | 使用 ConfigManager.list_users() |
| 用户详情 + 标签页 | ✅ 保留 | 帖子/主题列表展示 |
| 设置 + 账户管理 | ✅ 保留 | 完整的 CRUD + 目录选择 |
| 首页统计 | ✅ 保留 | 统计卡片 + 快捷操作 |
| 深色侧边栏 | ✅ 保留 | 深色背景 + 浅色文字 |

## 2. 系统架构

```
┌─────────────────────────────────────────────┐
│  Electron Main Process (main.js)            │
│  ├─ 窗口管理 (BrowserWindow)                │
│  ├─ IPC 处理 (ipcMain.handle)               │
│  └─ Python 子进程管理 (child_process.spawn) │
├─────────────────────────────────────────────┤
│  Preload Script (preload.js)                │
│  └─ contextBridge.exposeInMainWorld('api')  │
├─────────────────────────────────────────────┤
│  Renderer Process (HTML/CSS/JS)             │
│  ├─ 侧边栏导航 (6 个视图)                   │
│  ├─ 扁平化 UI (卡片式布局)                   │
│  └─ window.api.invoke('method', payload)    │
├─────────────────────────────────────────────┤
│  Python CLI Bridge (bridge.py)              │
│  ├─ JSON stdin → 解析命令                    │
│  ├─ 调用 APoU/DoPJ/Config 业务逻辑          │
│  └─ JSON stdout → 返回结果/进度              │
└─────────────────────────────────────────────┘
```

### 2.1 进程模型

- **Main Process**: 管理窗口生命周期、处理 IPC 请求、spawn Python 子进程
- **Renderer Process**: 渲染 UI、接收用户输入、通过 `window.api` 调用后端
- **Python Bridge**: 独立进程，通过 stdin/stdout JSON 协议通信，每次任务一个进程实例

### 2.2 Python 进程启动

**解释器发现：**
1. 首先尝试 `python3`（POSIX）/ `python`（Windows）
2. 然后检查 `PATH` 中的可用 Python 解释器
3. 如果失败，在 renderer 中显示友好错误提示，引导用户安装 Python 3.10+

**工作目录：** Python bridge 进程以项目根目录（`app.getAppPath()` 或其上级）为 `cwd`，确保 `sys.path.insert(0, PROJECT_ROOT)` 能正确找到 `APoU/`、`DoPJ/`、`AutoCCF/` 模块。

**打包后路径解析：** 开发模式使用 `__dirname`，生产模式使用 `process.resourcesPath` 作为基础路径，bridge.py 作为 `extraResources` 打包。

**未安装 Python 时的 UX：** main.js 在 `app.whenReady()` 后执行一次 `python --version` 检查。若失败，创建窗口后通过 `webContents.send('python:unavailable')` 通知 renderer 显示安装引导页面（非错误弹窗）。

### 2.2 安全模型

| 配置项 | 值 | 原因 |
|--------|-----|------|
| `contextIsolation` | `true` | 隔离 renderer 和 Node.js 上下文 |
| `nodeIntegration` | `false` | 禁止 renderer 直接访问 Node API |
| `sandbox` | `true` | 沙箱化 renderer 进程 |
| `webSecurity` | `true` | 启用同源策略 |

所有 Renderer → Main 通信必须通过 `contextBridge` 暴露的 `window.api` 对象。

## 3. IPC 契约

### 3.1 Stdout 纯净性保障

**问题：** APoU 的 `UserPostsCrawler._print()` 在 `on_log=None` 且 `cli=None` 时会 fallthrough 到裸 `print()`（见 `APoU/crawler.py:56`），这会污染 NDJSON stdout 通道。DoPJ 的 `DoPJRunner` 也通过 `cli` 对象调用 `print()` 输出进度。

**解决方案：** bridge.py 必须：
1. **始终传递 `on_log` 回调**给 `UserPostsCrawler`，将日志路由到 `emit("log", ...)`
2. 对 DoPJ，bridge.py 不传 `cli` 参数（`cli=None`），DoPJRunner 内部的 `print()` 调用不会执行（因为它有 `if self.cli:` 守卫）
3. **重定向 `sys.stdout`** 为自定义的 NDJSON writer，同时将原始 stdout 保存为 `_real_stdout`，`emit()` 使用 `_real_stdout`。任何意外的 `print()` 调用将被捕获并转换为 `{"type": "log", "data": {"level": "debug", ...}}`

```python
import io
import sys

_real_stdout = sys.stdout
sys.stdout = _NdjsonStdoutWrapper(_real_stdout)  # 拦截裸 print

def emit(msg_type: str, data: dict) -> None:
    """输出一行 NDJSON 到真实 stdout"""
    line = json.dumps({"type": msg_type, "data": data}, ensure_ascii=False)
    _real_stdout.write(line + "\n")
    _real_stdout.flush()
```

### 3.2 请求格式 (Electron → Python stdin)

```json
{"action": "<namespace>:<method>", "payload": {<参数>}}
```

### 3.3 完整 Action 列表

| Action | Payload | 说明 | 返回类型 |
|--------|---------|------|----------|
| `config:load` | `{}` | 加载配置文件 | `result`（含完整 BDUSS） |
| `config:save` | `{accounts, apou, dopj, database_dir}` | 保存配置 | `result` |
| `apou:crawl` | `{username}` | 爬取用户发言列表 | `progress` + `log` + `result` |
| `dopj:crawl` | `{input_json, threads}` | 爬取帖子详情 | `log` + `result` |
| `users:list` | `{}` | 列出已爬取的用户 | `result` |
| `users:detail` | `{username}` | 获取用户详情 | `result` |

**注意：** `config:load` 返回完整 BDUSS 值（非掩码）。BDUSS 掩码仅在 renderer 端展示时处理（`bduss.slice(0, 8) + "..."`），保证 settings 视图的 save round-trip 不会丢失数据。

### 3.4 响应格式 (Python stdout → Electron)

每行一个 JSON 对象（NDJSON）：

```json
{"type": "progress", "data": {"page": 5, "posts_count": 23, "message": "第5页: 23条"}}
{"type": "result", "data": {"success": true, "posts_count": 142, "output_file": "path/to/file.json"}}
{"type": "error", "data": {"code": "NETWORK_ERROR", "message": "请求超时"}}
{"type": "log", "data": {"level": "info", "message": "开始爬取..."}}
```

**APoU 进度模型：** APoU 的 `on_page_complete(page_num: int, posts_count: int)` 回调提供的是**每页完成**通知，而非 `(current, total)` 百分比。bridge.py 将其映射为：
```json
{"type": "progress", "data": {"page": <page_num>, "posts_count": <posts_count>, "message": "第N页: M条"}}
```
Renderer 端进度条使用 indeterminate 模式（因总页数未知），同时显示 `"已爬取 X 条帖子"` 实时计数。

**DoPJ 进度模型：** DoPJ 的 `DoPJRunner` 不提供进度回调。bridge.py 通过 `TaskManager.get_stats()` 在每个任务完成后发送统计更新：
```json
{"type": "progress", "data": {"success": 5, "failed": 1, "total": 100, "message": "5/100 完成"}}
```
这需要在 bridge.py 中自定义 `process_task` 逻辑，或定期查询 stats。

**APoU 输出格式：** APoU 的 `Storage.save_posts()` 写入的是**顶级 JSON 数组**（`[{post1}, {post2}, ...]`），而非 `{"posts": [...]}`。所有读取 APoU 输出的代码（bridge.py、E2E 测试、users:detail handler）必须处理此格式。`TaskManager.load_from_json()` 已兼容两种格式（line 113: `data.get("posts", data) if isinstance(data, dict) else data`）。

### 3.5 IPC 通信模型（Electron 侧）

**问题：** `ipcMain.handle()` 是请求-响应模式，返回单个 Promise。但 APoU/DoPJ 任务是长时间运行的，需要在执行过程中实时推送 progress/log 事件。

**解决方案：** 使用事件流模型：

```
Renderer                    Main Process              Python bridge
   │                            │                          │
   ├─ invoke('bridge:invoke')──►│                          │
   │                            ├─ spawn python bridge.py──►│
   │                            │                          ├─ stdout: {"type":"log",...}
   │  ◄──webContents.send()─────┤◄─ readline ──────────────┤
   │  ◄──webContents.send()─────┤◄─ readline ──────────────┤  (progress/log 事件)
   │  ◄──webContents.send()─────┤◄─ readline ──────────────┤
   │                            │                          ├─ stdout: {"type":"result",...}
   │  ◄── Promise.resolve() ────┤◄─ readline ──────────────┤  (final result)
   │                            │  process exits           │
```

main.js 的 `ipcMain.handle('bridge:invoke')` 实现：
1. `spawn('python', ['bridge.py'], {cwd: projectRoot})`
2. 将 `JSON.stringify(request)` 写入 stdin 后关闭 stdin
3. 逐行读取 stdout（使用 `readline` 模块）
4. 每行 JSON 解析后：
   - `type === "progress"` → `win.webContents.send('bridge:progress', data)`
   - `type === "log"` → `win.webContents.send('bridge:log', data)`
   - `type === "result"` 或 `type === "error"` → 作为 Promise 的 resolve/reject 值
5. 处理进程异常退出（`child.on('error')`, `child.on('exit')` 非零退出码）
6. 超时设置：APoU 300 秒，DoPJ 无超时（取决于任务量）

## 4. UI 设计

### 4.1 设计原则

- **扁平化**：无渐变、无立体效果、纯色背景
- **Light 主题**：白色/浅灰背景，深色文字
- **卡片布局**：信息区域使用卡片容器，圆角 8px，轻阴影 `0 1px 3px rgba(0,0,0,0.1)`
- **一致间距**：基于 8px 网格系统
- **中文优先**：UI 文本全部使用中文

### 4.2 配色方案

| 用途 | 颜色 | 说明 |
|------|------|------|
| 主色 | `#2563EB` (蓝) | 按钮、链接、选中状态 |
| 背景 | `#F8FAFC` | 页面背景 |
| 卡片背景 | `#FFFFFF` | 卡片容器 |
| 文字主色 | `#1E293B` | 标题、正文 |
| 文字次色 | `#64748B` | 描述、辅助文字 |
| 成功 | `#16A34A` | 成功状态 |
| 警告 | `#D97706` | 警告状态 |
| 错误 | `#DC2626` | 错误状态 |
| 边框 | `#E2E8F0` | 分割线、边框 |
| 侧边栏背景 | `#1E293B` | 深色侧边栏 |
| 侧边栏文字 | `#CBD5E1` | 侧边栏未选中 |
| 侧边栏选中 | `#FFFFFF` | 侧边栏选中项 |

### 4.3 布局结构

```
┌──────────────────────────────────────────────┐
│  标题栏 (系统标题栏，显示 "AutoCCF")          │
├─────────┬────────────────────────────────────┤
│         │  页面标题 + 描述                    │
│  侧边栏  │────────────────────────────────────│
│  (固定)  │                                    │
│         │  内容区（卡片布局）                  │
│  🏠 首页 │                                    │
│  📋 APoU │                                    │
│  📦 DoPJ │                                    │
│  👥 用户 │                                    │
│  ⚙️ 设置 │                                    │
│         │                                    │
│         ├────────────────────────────────────│
│         │  状态栏 (连接状态/版本信息)          │
└─────────┴────────────────────────────────────┘
```

侧边栏宽度：200px（固定），使用图标 + 文字。

### 4.4 视图详细设计

#### 4.4.1 首页 (Home)

- 统计卡片行：已爬取用户数、帖子总数、最近活动时间
- 快捷操作卡片：开始 APoU 爬取、开始 DoPJ 爬取
- 最近操作日志列表

#### 4.4.2 APoU 视图

- 用户名输入框 + "开始爬取"按钮
- 配置区：页面延迟滑块、最大重试次数滑块
- 进度区：进度条 + 百分比 + 当前状态文字
- 实时日志区：滚动文本区域，显示爬取日志

#### 4.4.3 DoPJ 视图

- 用户选择下拉框（从已爬取用户中选择）
- 配置区：线程数滑块、最大重试次数、最小间隔
- 账户状态表：显示每个 BDUSS 账户的状态（可用/被封）
- 进度区：进度条 + 任务统计（完成/失败/跳过）

#### 4.4.4 用户列表视图

- 搜索框（即时过滤）
- 表格：用户名、帖子数、爬取时间、操作按钮
- 点击行 → 进入用户详情视图

#### 4.4.5 用户详情视图

- 用户信息头部：用户名、帖子统计
- 标签页切换：帖子列表 / 主题列表 / 文件列表
- 每个标签页内使用表格展示

#### 4.4.6 设置视图

- 数据库目录配置（路径选择器）
- 账户管理：添加/编辑/删除 BDUSS 账户
- APoU 配置：页面延迟、最大重试次数
- DoPJ 配置：线程数、最大重试、最小间隔、最大失败数
- 保存/重置按钮

## 5. 文件结构

```
electron/
├── main.js              # Electron 主进程入口
├── preload.js           # contextBridge 安全桥接
├── bridge.py            # Python CLI bridge (JSON stdin/stdout)
├── renderer/
│   ├── index.html       # 单页应用入口
│   ├── styles/
│   │   ├── reset.css    # CSS Reset (normalize)
│   │   ├── variables.css # CSS 变量 (颜色/间距/字体)
│   │   ├── layout.css   # 侧边栏/内容区布局
│   │   └── components.css # 卡片/按钮/表单/表格/进度条
│   ├── js/
│   │   ├── app.js       # 应用入口：路由、视图切换、状态管理
│   │   ├── api.js       # window.api 封装层
│   │   └── views/
│   │       ├── home.js      # 首页视图
│   │       ├── apou.js      # APoU 视图
│   │       ├── dopj.js      # DoPJ 视图
│   │       ├── users.js     # 用户列表视图
│   │       ├── user-detail.js # 用户详情视图
│   │       └── settings.js  # 设置视图
│   └── assets/
│       └── icons/       # 侧边栏图标 (SVG)
├── package.json         # Node.js 依赖配置
└── forge.config.js      # Electron Forge 打包配置
```

## 6. Python Bridge 设计

### 6.1 bridge.py 职责

`bridge.py` 是 Electron 和 Python 业务逻辑之间的薄适配层：

1. 保存原始 `sys.stdout` 为 `_real_stdout`，替换 `sys.stdout` 为 NDJSON 拦截器
2. 从 stdin 读取一行 JSON
3. 解析 `action` 字段路由到对应处理函数
4. 调用现有的 APoU/DoPJ/Config API
5. 将结果/进度以 NDJSON 写入 `_real_stdout`
6. 任务完成后进程退出

### 6.2 依赖关系与实际 API 签名

```python
# bridge.py 依赖图
bridge.py
├── AutoCCF.config.ConfigManager          # load() → UnifiedConfig
│   └── .list_users() → List[Dict]        # 用户列表
│   └── .find_apou_outputs() → List[Dict] # APoU 输出查找
├── AutoCCF.config.UnifiedConfig          # .save(path) → str
│   └── .from_dict(data, path) → cls      # 从字典创建
│   └── .to_dict() → Dict                 # 序列化
├── AutoCCF.utils.UserPaths               # 用户数据路径
├── APoU.crawler.UserPostsCrawler         # APoU 爬虫
│   └── __init__(config, on_page_complete, on_log, cli)
│   └── on_page_complete: Callable[[int, int], None]  # (page_num, posts_count)
│   └── on_log: Callable[[str, str], None]            # (message, level)
│   └── async crawl(username, ...) → List[Post]
├── DoPJ.cli.DoPJRunner                   # DoPJ 运行器
│   └── __init__(input_json, output_dir, threads, max_retries,
│   │            progress_file, cli, config_file, config_dict)
│   └── load_tasks(incremental=True)
│   └── run()
│   └── task_manager.get_stats() → Dict[str, int]
└── DoPJ.cli.TaskManager                  # 任务管理
```

**关键 API 注意事项：**
- `DoPJRunner.__init__` 使用 `input_json`（非 `input_file`），需要 `config_file` 或 `config_dict`
- `DoPJRunner` 没有 `on_log` 回调，它通过 `cli` 对象输出。bridge.py 传 `cli=None` 防止 print
- `ConfigManager` 没有 `save()` 方法，保存通过 `UnifiedConfig.save(path)` 实现
- `APoU` 输出是**顶级列表**格式 `[post1, post2, ...]`
- `UserPostsCrawler._print()` 即使传了 `on_log`，在 `cli=None` 时仍会 fallthrough 到 `print()`。所以必须同时重定向 stdout

### 6.3 进度回调

**APoU 进度** — 使用 `on_page_complete` 回调：

```python
def on_page_complete(page_num: int, posts_count: int) -> None:
    """每页爬取完成后触发"""
    emit("progress", {"page": page_num, "posts_count": posts_count,
                       "message": f"第 {page_num} 页: {posts_count} 条"})
```

**DoPJ 进度** — 无内置回调，bridge.py 需要：
1. 调用 `runner.load_tasks()` 获取总任务数
2. 覆写 `runner.process_task()` 或在 `run()` 后读取 `task_manager.get_stats()`
3. 由于 DoPJ 使用多线程 + ThreadPoolExecutor，bridge.py 可通过定期轮询 stats 发送进度

```python
# 简化方案：在 run() 完成后一次性报告结果
runner.load_tasks()
runner.run()
stats = runner.task_manager.get_stats()
emit("result", {"success": True, "stats": stats})
```

### 6.4 config:save 实现

```python
def handle_config_save(payload: dict) -> None:
    config = UnifiedConfig.from_dict(payload)
    saved_path = config.save()  # 调用 UnifiedConfig.save()，非 ConfigManager.save()
    emit("result", {"success": True, "path": saved_path})
```

### 6.5 users:list 实现

bridge.py 必须使用 `ConfigManager.list_users()`（`AutoCCF/config.py:283`）而非重新实现文件系统扫描：

```python
def handle_users_list(payload: dict) -> None:
    cm = ConfigManager()
    cm.load()
    users = cm.list_users()
    emit("result", {"success": True, "users": users})
```

## 7. 测试策略

### 7.1 Python Bridge 单元测试

- 测试 JSON 请求解析（有效/无效格式）
- 测试每个 action 的路由
- 测试响应序列化
- 测试错误处理（未知 action、无效 payload）
- 测试 stdout 拦截器不污染 NDJSON 通道

### 7.2 IPC 集成测试

- Electron spawn Python bridge，发送请求，验证响应格式
- 测试 progress 事件流式传输到 renderer
- 测试进程超时和异常退出处理
- 测试 Python 不可用时的错误路径

### 7.3 E2E Payload 测试

使用用户已有的 BDUSS 配置，对 `团子传说` 执行完整流程：

1. **APoU 爬取测试**：
   - 输入：`{"action": "apou:crawl", "payload": {"username": "团子传说"}}`
   - 验证：输出 JSON 文件存在、文件内容是**顶级 JSON 数组**（非 `{posts: [...]}`）
   - 验证：数组中每个元素包含 `tid`, `title`, `href` 字段
   - 验证：收到至少一个 `progress` 事件和一个 `result` 事件

2. **DoPJ 爬取测试**：
   - 输入：`{"action": "dopj:crawl", "payload": {"input_json": "<apou输出文件>", "threads": 1}}`
   - 验证：`result` 的 `stats` 中 `success > 0`
   - 验证：DoPJ 输出目录存在且包含 `thread.json` 文件

3. **用户列表验证**：
   - 在 APoU + DoPJ 爬取后，`users:list` 应返回包含 `团子传说` 的用户
   - `users:detail` 应返回该用户的帖子数据

### 7.4 UI 冒烟测试

- 使用 Playwright 验证 6 个视图可渲染（sidebar 导航切换）
- 验证表单输入和按钮交互
- 验证 APoU 视图的 indeterminate 进度条正确显示

## 8. 技术决策记录

| 决策 | 选择 | 备选方案 | 理由 |
|------|------|---------|------|
| Renderer 框架 | 原生 HTML/CSS/JS | React, Vue | 6 个视图复杂度中等，无需框架开销 |
| Python 通信 | child_process.spawn + JSON stdio | WebSocket, HTTP API | 最简单、最安全，无需额外端口 |
| 进程模型 | 每任务一进程 | 长驻进程 | 避免状态管理复杂性，简化错误恢复 |
| 打包工具 | Electron Forge | electron-builder | 官方推荐，社区活跃 |
| CSS 方案 | 原生 CSS 变量 | Tailwind, SCSS | 减少构建步骤，变量系统已足够 |

## 9. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Python 进程启动延迟 | 用户体验卡顿 | 首次加载时预热，显示加载动画 |
| BDUSS 安全存储 | 凭证泄露 | config.json 不打包进 asar，.gitignore 排除 |
| Electron 包体积大 | 安装包 >100MB | 使用 asar 打包，排除不必要文件 |
| Python 环境依赖 | 用户需安装 Python | 启动时检测 Python 可用性，显示安装引导页面 |
| 中文路径兼容 | Windows 中文路径问题 | 统一使用 UTF-8 编码，路径处理使用 pathlib |
| stdout 污染 | NDJSON 解析失败 | 重定向 sys.stdout + 始终传 on_log 回调 |
| 意外 print 输出 | 第三方库 print | stdout 拦截器将非 JSON 行包装为 log 事件 |
