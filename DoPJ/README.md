# DoPJ - Detail of Posts JSON

DoPJ 是基于 APoU 的第二步工具，用于获取每个帖子的详细内容。

## 功能特性

- ✅ **多线程并发**：支持多线程同时爬取，提高效率
- ✅ **多账户轮换**：自动轮换使用多个账户，避免风控
- ✅ **即时保存**：每个任务完成后立即保存，避免数据丢失
- ✅ **断点续传**：支持中断后继续，不会重复爬取
- ✅ **失败重试**：自动重试失败的任务，最大化成功率
- ✅ **进度追踪**：实时显示爬取进度和统计信息

## 使用流程

### 1. 准备输入文件

首先使用 APoU.py 爬取用户的所有发言：

```bash
cd ..
python APoU.py -u 用户名
```

这会生成 `用户名_posts.json` 文件。

### 2. 配置账户

复制配置模板并填入你的 BDUSS：

```bash
cd DoPJ
cp config/config.example.json config/config.json
```

编辑 `config/config.json`，填入你的贴吧账户 BDUSS（建议使用 2-5 个账户）：

```json
{
  "accounts": [
    {
      "name": "账户1",
      "bduss": "你的BDUSS_1"
    },
    {
      "name": "账户2",
      "bduss": "你的BDUSS_2"
    }
  ],
  "min_interval": 2.0,
  "max_fails": 5
}
```

**获取 BDUSS 方法：**
1. 在浏览器登录百度贴吧
2. 按 F12 打开开发者工具
3. 进入 Application → Cookies → tieba.baidu.com
4. 找到 BDUSS 字段，复制其值（192 个字符）

### 3. 运行爬取

```bash
python DoPJ.py -i ../用户名_posts.json -c config/config.json
```

**常用参数：**

- `-i, --input`: APoU 输出的 JSON 文件（必需）
- `-c, --config`: 配置文件（必需）
- `-o, --output`: 输出目录（默认：posts）
- `-t, --threads`: 并发线程数（默认：3，建议 3-5）
- `-r, --retries`: 最大重试次数（默认：3）
- `-p, --progress`: 进度文件（默认：progress.json）

**示例：**

```bash
# 使用 5 个线程，输出到 output 目录
python DoPJ.py -i ../用户名_posts.json -c config/config.json -o output -t 5

# 指定重试次数为 5 次
python DoPJ.py -i ../用户名_posts.json -c config/config.json -r 5
```

### 4. 查看结果

爬取完成后，数据保存在输出目录中：

```
posts/
├── 0001_5052759887_105910715857/   # 索引_tid_pid
│   ├── scrape_info.json
│   └── 5052759887/
│       ├── content.db              # SQLite 数据库
│       ├── forum.json              # 贴吧信息
│       ├── thread.json             # 帖子信息
│       ├── user_avatar/            # 用户头像
│       └── post_assets/            # 帖子媒体文件
│           ├── images/
│           ├── videos/
│           └── voices/
├── 0002_5043594059_105666571465/
│   └── ...
└── ...
```

每个文件夹名格式：`索引_tid_pid`，方便与输入 JSON 关联。

## 断点续传

如果爬取过程中断（Ctrl+C 或异常退出），下次运行时会自动继续：

```bash
# 直接再次运行，会从上次中断的地方继续
python DoPJ.py -i ../用户名_posts.json -c config/config.json
```

进度保存在 `progress.json` 文件中。

## 配置说明

### accounts

账户列表，每个账户包括：
- `name`: 账户名称（用于识别，可自定义）
- `bduss`: 账户的 BDUSS 值

### min_interval

同一账户两次使用的最小间隔（秒），默认 2.0 秒。建议值：
- 2-3 个账户：2.0 秒
- 4-5 个账户：1.5 秒
- 6 个以上账户：1.0 秒

### max_fails

账户最大失败次数，超过后自动禁用该账户，默认 5 次。

如果账户 BDUSS 失效，会立即禁用该账户。

## 注意事项

- **BDUSS 安全**：BDUSS 是敏感信息，不要泄露给他人
- **账户数量**：建议至少使用 2 个账户，最好 3-5 个
- **并发线程**：线程数不要超过账户数，建议设置为账户数或略少
- **网络环境**：稳定的网络环境可以减少失败率
- **风控提示**：如果大量账户被封，说明爬取频率过高，需要：
  - 增加更多账户
  - 减少并发线程数
  - 增加 min_interval 值

## 依赖

DoPJ 依赖 TiebaArchiver 的库，确保已安装：

```bash
cd ../example/TiebaArchiver-1.3.1
pip install -r requirements.txt
```

主要依赖：
- aiotieba >= 4.4.9
- aiohttp >= 3.9.5
- orjson >= 3.10.3
- aiofiles >= 24.1.0

## 故障排除

### 所有账户都被禁用

**原因**：账户 BDUSS 失效或被风控

**解决方法**：
1. 重新获取 BDUSS
2. 使用更多的账户
3. 减少并发线程数
4. 增加请求间隔

### 爬取速度慢

**解决方法**：
1. 增加并发线程数（`-t` 参数）
2. 使用更多账户
3. 检查网络连接

### 大量任务失败

**可能原因**：
1. 帖子已被删除
2. 帖子需要特殊权限
3. 网络不稳定

**解决方法**：
1. 检查失败任务的错误信息
2. 增加重试次数（`-r` 参数）
3. 检查网络连接

## 许可

本工具仅供学习和研究使用，请遵守贴吧相关规定。
