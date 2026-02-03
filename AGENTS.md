# AGENTS.md

本文件为 AI 编程代理（如 Claude、Copilot、Cursor、Aider 等）提供项目指导。

## 项目概述

AutoCCF 是一个百度贴吧爬虫工具集，采用两步式设计：

1. **APoU (All Posts of User)** - `APoU/`: 通过 tb.anova.me API 快速获取用户发言列表
2. **DoPJ (Detail of Posts JSON)** - `DoPJ/`: 基于 APoU 输出，获取每个帖子的完整详细内容

技术栈：Python 3.10+, asyncio, aiohttp, aiotieba, requests

## 构建和运行命令

### 环境设置

```bash
# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/macOS

# 安装依赖
pip install -r requirements.txt

# 使用镜像源（国内推荐）
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

### 运行程序

```bash
# APoU - 获取用户发言列表
python APoU.py -u <用户名>

# DoPJ - 获取帖子详细内容
cd DoPJ
python DoPJ.py -i ../用户名_posts.json -c config/config.json -t 3
```

### 代码检查 (Linting)

```bash
# 安装 lint 工具
pip install flake8 black isort

# 语法检查（严格模式 - 只检查错误和未定义名称）
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# 代码质量检查（宽松模式）
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# 格式化代码
black *.py DoPJ/

# 排序导入
isort *.py DoPJ/
```

### 测试命令

```bash
# APoU 模块测试
python -c "from APoU import UserPostsCrawler; print('APoU module OK')"
python -c "from APoU.exceptions import APoUError, NetworkError; print('Exceptions OK')"
python -c "from APoU.config import CrawlerConfig; c = CrawlerConfig(); print(f'Config OK: {c.base_url}')"

# DoPJ 单元测试 - URL 解析器
cd DoPJ
python -c "from utils.url_parser import parse_tieba_url; result = parse_tieba_url('https://tieba.baidu.com/p/123?pid=456'); assert result == (123, 456)"

# DoPJ 单元测试 - 账户管理器
python -c "from core.account_manager import AccountManager; am = AccountManager([{'name': 'test', 'bduss': 'test123'}]); acc = am.get_account(); assert acc.name == 'test'"

# DoPJ 单元测试 - 任务管理器
python -c "from core.task_manager import TaskManager; tm = TaskManager(); assert tm.get_stats()['total'] == 0"

# 运行单个模块测试（带 __main__ 块的模块）
python DoPJ/utils/url_parser.py
```

## 代码风格指南

### 导入顺序

按以下顺序组织导入，每组之间空一行：

```python
# 1. 标准库
import asyncio
import json
import os
import sys
import time
from typing import List, Dict, Optional, Tuple

# 2. 第三方库
import requests
import aiohttp

# 3. 本地模块
from core.account_manager import AccountManager
from utils.url_parser import parse_tieba_url
```

### 格式化规范

- **行长度**: 最大 127 字符
- **缩进**: 4 个空格（禁止使用 Tab）
- **引号**: 字符串使用双引号 `"`，文档字符串使用三双引号 `"""`
- **编码**: 所有 Python 文件使用 UTF-8 编码
- **尾逗号**: 多行列表/字典最后一项加逗号

### 类型注解

所有公开函数必须有类型注解：

```python
from typing import List, Dict, Optional, Tuple

def parse_tieba_url(url: str) -> Optional[Tuple[int, Optional[int]]]:
    """解析贴吧 URL"""
    pass

async def scrape_thread(
    self,
    tid: int,
    bduss: str,
    output_dir: str,
) -> tuple[bool, str]:
    """爬取单个帖子，返回 (是否成功, 错误信息)"""
    pass
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 类 | PascalCase | `AccountManager`, `TaskStatus` |
| 函数/方法 | snake_case | `get_next_task`, `parse_posts` |
| 变量 | snake_case | `max_retries`, `output_dir` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES`, `BASE_URL` |
| 私有成员 | 前导下划线 | `_update_stats`, `_internal_cache` |
| 模块 | snake_case | `account_manager.py`, `url_parser.py` |

### 文档字符串

使用 Google 风格的中文文档字符串：

```python
def crawl_user_posts(self, username: str) -> List[dict]:
    """
    爬取指定用户的所有发言

    Args:
        username: 目标用户名

    Returns:
        所有爬取到的发言列表，每个元素包含 id, title, content, href, forum 字段

    Raises:
        ValueError: 如果用户名为空
        requests.RequestException: 如果网络请求失败
    """
    pass
```

### 注释语言

- **代码注释**: 使用中文
- **函数名/变量名**: 使用英文
- **文档字符串**: 使用中文
- **Git commit**: 可使用中文或英文（遵循 Conventional Commits）

```python
# 正确示例
def get_account(self) -> Optional[Account]:
    """获取一个可用的账户（轮换策略）"""
    # 检查账户是否可用
    if account.is_banned:
        return None
    # 更新使用时间
    account.last_used = time.time()
    return account
```

### 错误处理

1. **捕获具体异常**，避免裸露的 `except:`
2. **提供有意义的错误信息**
3. **使用日志记录而非 print（生产环境）**

```python
try:
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    data = response.json()
except requests.Timeout:
    print(f"请求超时: {url}")
    return None
except requests.RequestException as e:
    print(f"网络请求失败: {e}")
    return None
except json.JSONDecodeError:
    print(f"JSON 解析失败: {response.text[:100]}...")
    return None
```

### 异步编程

DoPJ 模块使用 asyncio，遵循以下规范：

```python
# 正确：使用 async/await
async def scrape_thread(self, tid: int) -> tuple[bool, str]:
    result = await get_posts(tid)
    return True, ""

# 正确：并发执行多个任务
await asyncio.gather(
    thread_service.save_forum_info(fid),
    thread_service.save_thread_info(thread),
)

# 正确：在同步代码中运行异步
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    result = loop.run_until_complete(async_function())
finally:
    loop.close()
```

### 数据类

使用 `@dataclass` 定义数据结构：

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Task:
    """爬取任务"""
    index: int
    tid: int
    pid: Optional[int]
    title: str
    status: TaskStatus = TaskStatus.PENDING
    retry_count: int = 0
```

## 项目结构

```
AutoCCF/
├── APoU.py                    # APoU 主入口
├── APoU/                      # 用户发言列表爬虫模块
│   ├── __init__.py           # 模块导出
│   ├── api_client.py         # API 请求封装（含重试逻辑）
│   ├── config.py             # 配置常量类
│   ├── crawler.py            # 主爬虫逻辑
│   ├── exceptions.py         # 自定义异常类
│   ├── parser.py             # 数据解析器
│   └── storage.py            # 数据存储
├── DoPJ/                      # 帖子详情爬虫模块
│   ├── DoPJ.py               # 主入口
│   ├── core/                 # 核心模块
│   │   ├── account_manager.py
│   │   ├── task_manager.py
│   │   └── scraper.py
│   ├── utils/                # 工具模块
│   │   └── url_parser.py
│   └── config/               # 配置目录
├── example/                   # 示例和参考代码
│   └── TiebaArchiver-1.3.1/  # DoPJ 依赖的第三方库
├── requirements.txt           # 依赖列表
├── AGENTS.md                  # 本文件
└── CONTRIBUTING.md            # 贡献指南
```

## 安全注意事项

**绝对不要提交以下文件：**
- `DoPJ/config/config.json` - 包含 BDUSS
- `**/bduss.txt` - BDUSS 文件
- `**/tieba_auth.json` - 认证信息
- `*_posts.json` - 爬取的数据（示例除外）

## 常见修改场景

### APoU 模块

#### 修改 API 请求逻辑
修改 `APoU/api_client.py` 中的 `fetch_page()` 或 `fetch_page_with_retry()` 方法

#### 调整重试策略
修改 `APoU/config.py` 中的 `CrawlerConfig` 类

#### 添加新的数据字段
修改 `APoU/parser.py` 中的 `Post` 数据类和 `_parse_single_post()` 方法

#### 自定义错误处理
在 `APoU/exceptions.py` 中添加新的异常类

### DoPJ 模块

#### 添加新的 URL 解析逻辑
修改 `DoPJ/utils/url_parser.py`

#### 调整账户轮换策略
修改 `DoPJ/core/account_manager.py` 中的 `get_account()` 方法

#### 修改爬取配置
修改 `DoPJ/core/scraper.py` 中的 `scrape_thread()` 方法

#### 添加新的任务过滤条件
修改 `DoPJ/core/task_manager.py` 中的 `load_from_json()` 方法

## Git Commit 规范

使用 Conventional Commits 格式：

```
feat: 添加多进程支持
fix: 修复 SimplePath 缺少方法的问题
docs: 更新安装说明
refactor: 重构账户管理器
test: 添加 URL 解析测试
chore: 更新依赖版本
```
