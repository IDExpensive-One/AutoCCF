# Electron 迁移设计规格

> **日期**: 2026-03-22
> **状态**: 设计中
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

### 2.2 安全模型

| 配置项 | 值 | 原因 |
|--------|-----|------|
| `contextIsolation` | `true` | 隔离 renderer 和 Node.js 上下文 |
| `nodeIntegration` | `false` | 禁止 renderer 直接访问 Node API |
| `sandbox` | `true` | 沙箱化 renderer 进程 |
| `webSecurity` | `true` | 启用同源策略 |

所有 Renderer → Main 通信必须通过 `contextBridge` 暴露的 `window.api` 对象。

## 3. IPC 契约

### 3.1 请求格式 (Electron → Python stdin)

```json
{"action": "<namespace>:<method>", "payload": {<参数>}}
```

### 3.2 完整 Action 列表

| Action | Payload | 说明 | 返回类型 |
|--------|---------|------|----------|
| `config:load` | `{}` | 加载配置文件 | `result` |
| `config:save` | `{accounts, apou, dopj, database_dir}` | 保存配置 | `result` |
| `apou:crawl` | `{username}` | 爬取用户发言列表 | `progress` + `result` |
| `dopj:crawl` | `{user_file, threads}` | 爬取帖子详情 | `progress` + `result` |
| `users:list` | `{}` | 列出已爬取的用户 | `result` |
| `users:detail` | `{username}` | 获取用户详情 | `result` |

### 3.3 响应格式 (Python stdout → Electron)

每行一个 JSON 对象（NDJSON）：

```json
{"type": "progress", "data": {"current": 5, "total": 20, "message": "正在爬取第5页..."}}
{"type": "result", "data": {"success": true, "posts_count": 142, "output_file": "path/to/file.json"}}
{"type": "error", "data": {"code": "NETWORK_ERROR", "message": "请求超时"}}
{"type": "log", "data": {"level": "info", "message": "开始爬取..."}}
```

### 3.4 生命周期

1. Main process 通过 `child_process.spawn('python', ['bridge.py'])` 启动 Python
2. 写入一行 JSON 到 stdin
3. 读取 stdout 逐行解析 JSON（progress/log 事件实时推送到 renderer）
4. 收到 `result` 或 `error` 表示任务完成
5. Python 进程自然退出（每次任务一个进程，无长驻）

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

1. 从 stdin 读取一行 JSON
2. 解析 `action` 字段路由到对应处理函数
3. 调用现有的 APoU/DoPJ/Config API
4. 将结果/进度以 NDJSON 写入 stdout
5. 任务完成后进程退出

### 6.2 依赖关系

```python
# bridge.py 依赖图
bridge.py
├── AutoCCF.config.ConfigManager    # 配置管理
├── AutoCCF.config.UnifiedConfig    # 配置数据类
├── AutoCCF.utils.UserPaths         # 用户数据路径
├── APoU.UserPostsCrawler           # APoU 爬虫
├── DoPJ.cli.DoPJRunner             # DoPJ 运行器
└── DoPJ.cli.TaskManager            # 任务管理
```

### 6.3 进度回调

APoU 和 DoPJ 的现有爬虫支持回调函数。bridge.py 将回调绑定到 stdout 输出：

```python
def progress_callback(current: int, total: int, message: str) -> None:
    emit("progress", {"current": current, "total": total, "message": message})
```

其中 `emit()` 将 JSON 写入 stdout 并 flush。

## 7. 测试策略

### 7.1 Python Bridge 单元测试

- 测试 JSON 请求解析（有效/无效格式）
- 测试每个 action 的路由
- 测试响应序列化
- 测试错误处理（未知 action、无效 payload）

### 7.2 IPC 集成测试

- Electron spawn Python bridge，发送请求，验证响应格式
- 测试 progress 事件流式传输
- 测试进程超时和异常退出处理

### 7.3 E2E Payload 测试

使用用户已有的 BDUSS 配置，对 `团子传说` 执行完整流程：

1. **APoU 爬取测试**：
   - 输入：`{"action": "apou:crawl", "payload": {"username": "团子传说"}}`
   - 验证：输出 JSON 文件存在、包含 `posts` 数组、每个 post 有必要字段
2. **DoPJ 爬取测试**：
   - 输入：`{"action": "dopj:crawl", "payload": {"user_file": "<apou输出文件>", "threads": 1}}`
   - 验证：帖子详情文件存在、内容完整

### 7.4 UI 冒烟测试

- 使用 Playwright 验证 6 个视图可渲染
- 验证侧边栏导航切换正常
- 验证表单输入和按钮交互

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
| Python 环境依赖 | 用户需安装 Python | 文档说明，后续可考虑 PyInstaller 打包 |
| 中文路径兼容 | Windows 中文路径问题 | 统一使用 UTF-8 编码，路径处理使用 pathlib |
