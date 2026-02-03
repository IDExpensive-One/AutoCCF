# AutoCCF - 百度贴吧爬虫工具集

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/yourusername/AutoCCF)

> 一个完整的百度贴吧数据采集解决方案，采用两步式设计：快速获取列表 + 深度爬取详情

## ✨ 特性

- 🚀 **两步式设计** - 先快速获取列表，再按需深度爬取
- 🔄 **多线程并发** - 支持多线程同时爬取，效率更高
- 👥 **多账户轮换** - 自动轮换使用多个账户，避免风控
- 💾 **即时保存** - 每个任务完成后立即保存，避免数据丢失
- 🔁 **断点续传** - 支持中断后继续，不会重复爬取
- 🔄 **失败重试** - 自动重试失败的任务，最大化成功率
- 📊 **完整数据** - 保存文本、图片、视频、语音等所有内容
- 🗄️ **SQLite 存储** - 使用 SQLite 数据库，方便查询和管理

## 📋 目录

- [工具组成](#工具组成)
- [快速开始](#快速开始)
- [详细使用](#详细使用)
- [项目结构](#项目结构)
- [配置说明](#配置说明)
- [常见问题](#常见问题)
- [贡献指南](#贡献指南)
- [许可证](#许可证)
- [致谢](#致谢)

## 🛠️ 工具组成

## 工具组成

### 🚀 第一步：APoU (All Posts of User)

快速获取用户的所有发言列表。

- 轻量级，只依赖 requests
- 通过第三方 API (tb.anova.me) 快速获取
- 输出简洁的 JSON 文件

**使用方法：**
```bash
python APoU.py -u 用户名
```

**输出：**
- `用户名_posts.json` - 包含所有发言的 href 链接

### 📥 第二步：DoPJ (Detail of Posts JSON)

基于 APoU 输出，获取每个帖子的完整内容。

- 多线程并发，速度快
- 多账户轮换，避免风控
- 断点续传，不怕中断
- 失败重试，成功率高

**使用方法：**
```bash
cd DoPJ
cp config/config.example.json config/config.json
# 编辑 config.json，填入 2-5 个贴吧账户的 BDUSS

python DoPJ.py -i ../用户名_posts.json -c config/config.json -t 3
```

**输出：**
- `posts/` 目录，包含每个帖子的完整数据
  - SQLite 数据库（所有文本内容）
  - 媒体文件（图片、视频、语音）
  - 用户头像
  - 贴吧信息

## 快速开始

### 1. 安装依赖

```bash
# APoU 依赖
pip install requests

# DoPJ 依赖（基于 TiebaArchiver）
cd example/TiebaArchiver-1.3.1
pip install -r requirements.txt
cd ../..
```

### 2. 运行示例

```bash
# 步骤 1: 获取用户发言列表
python APoU.py -u 团子传说

# 步骤 2: 配置 DoPJ
cd DoPJ
cp config/config.example.json config/config.json
# 编辑 config.json，填入你的 BDUSS

# 步骤 3: 爬取详细内容
python DoPJ.py -i ../团子传说_posts.json -c config/config.json
```

### 3. 查看结果

爬取完成后：
- APoU 输出：`团子传说_posts.json`（轻量级列表）
- DoPJ 输出：`DoPJ/posts/`（完整数据）

可以使用 [TiebaReader](https://github.com/Sorceresssis/TiebaReader) 阅读爬取的数据。

## 获取 BDUSS

BDUSS 是贴吧的登录凭证，DoPJ 需要使用。

**获取方法：**
1. 浏览器登录百度贴吧
2. 按 F12 打开开发者工具
3. 进入 Application → Cookies → tieba.baidu.com
4. 找到 BDUSS 字段，复制其值（192 个字符）

**安全提示：**
- BDUSS 可以执行几乎所有账户操作
- 不要泄露给他人
- 过期时间长达数年
- 修改密码或退出登录后失效

## 特性对比

| 特性 | APoU | DoPJ |
|-----|------|------|
| 速度 | 非常快 | 较慢（取决于线程数） |
| 数据量 | 轻量级 | 完整数据 |
| 需要 BDUSS | 否 | 是 |
| 多线程 | 否 | 是 |
| 风控风险 | 低 | 中等（多账户可降低） |
| 断点续传 | 否 | 是 |
| 输出格式 | JSON | SQLite + 媒体文件 |

## 使用场景

### 场景 1：只需要快速浏览用户发言

```bash
python APoU.py -u 用户名
# 查看 用户名_posts.json
```

### 场景 2：需要完整的帖子数据和媒体文件

```bash
# 第一步
python APoU.py -u 用户名

# 第二步
cd DoPJ
python DoPJ.py -i ../用户名_posts.json -c config/config.json -t 5
```

### 场景 3：爬取特定用户在特定贴吧的发言

修改 APoU.py 中的 `fname` 参数（第 39 行）：
```python
params = {
    "fname": "贴吧名",  # 指定贴吧名
    "username": username,
    "page": page
}
```

## 性能建议

### APoU
- 单线程，速度取决于 API 响应
- 通常几分钟内完成

### DoPJ
- **3 个账户**：使用 `-t 3`，预计每个帖子 2-5 秒
- **5 个账户**：使用 `-t 5`，预计每个帖子 1-3 秒
- 大型帖子（1000+ 回复）可能需要几分钟

**示例：**
- 500 个帖子，5 个账户，5 个线程
- 预计耗时：500 × 2 / 5 = 200 秒 ≈ 3.5 分钟

## 故障排除

### APoU 返回空数据
- 检查用户名是否正确
- API 可能临时不可用，稍后重试
- 用户可能没有公开发言

### DoPJ 所有账户被封
- 使用更多账户
- 减少并发线程数
- 增加 `config.json` 中的 `min_interval`

### 大量任务失败
- 检查 BDUSS 是否有效
- 检查网络连接
- 部分帖子可能已被删除（正常）

## 📁 项目结构

```
AutoCCF/
├── APoU.py                     # 第一步：获取用户发言列表
├── DoPJ/                       # 第二步：获取帖子详细内容
│   ├── DoPJ.py                 # 主程序
│   ├── core/                   # 核心模块
│   │   ├── account_manager.py  # 账户管理和轮换
│   │   ├── task_manager.py     # 任务队列和进度管理
│   │   └── scraper.py          # 爬取工作器
│   ├── utils/                  # 工具模块
│   │   └── url_parser.py       # URL 解析
│   ├── config/                 # 配置文件
│   │   ├── config.example.json # 配置模板
│   │   └── config.json         # 实际配置（需创建）
│   ├── requirements.txt        # DoPJ 依赖
│   └── README.md               # DoPJ 详细文档
├── example/                    # 示例和参考
│   ├── TiebaArchiver-1.3.1/    # TiebaArchiver 参考实现
│   └── test post/              # 测试数据
├── requirements.txt            # 项目依赖
├── install.sh                  # Linux/Mac 安装脚本
├── install.bat                 # Windows 安装脚本
├── README.md                   # 项目说明
├── CLAUDE.md                   # 技术文档
├── LICENSE                     # 开源许可证
└── .gitignore                  # Git 忽略规则
```

## 📖 文档

- [CLAUDE.md](CLAUDE.md) - 详细技术文档和架构说明
- [DoPJ/README.md](DoPJ/README.md) - DoPJ 完整使用指南
- [TiebaArchiver README](example/TiebaArchiver-1.3.1/README.md) - 参考项目文档

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出建议！

### 如何贡献

1. **Fork 本仓库**
2. **创建特性分支** (`git checkout -b feature/AmazingFeature`)
3. **提交更改** (`git commit -m 'Add some AmazingFeature'`)
4. **推送到分支** (`git push origin feature/AmazingFeature`)
5. **提交 Pull Request**

### 代码规范

- 使用 Python 3.10+ 语法
- 遵循 PEP 8 代码风格
- 函数和类需要有文档字符串（中文）
- 提交前运行测试确保功能正常

### 报告问题

提交 Issue 时请包含：
- 操作系统和 Python 版本
- 完整的错误信息
- 复现步骤
- 预期行为和实际行为

## 🔒 安全性

### BDUSS 安全

- **永远不要**提交包含真实 BDUSS 的配置文件
- **永远不要**分享你的 BDUSS 给他人
- 定期更换 BDUSS（修改密码即可失效）
- 使用专门的测试账户进行开发

### 数据安全

- 爬取的数据仅供个人学习使用
- 不要公开分享他人的隐私数据
- 遵守数据保护相关法律法规

## ⚠️ 免责声明

- 本工具**仅供学习和研究使用**
- 使用者必须遵守百度贴吧的服务条款
- 请遵守速率限制，避免对服务器造成过大压力
- 未经授权，请勿用于商业用途
- 作者不对工具的滥用行为负责

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源。

使用本项目时请注意：
- 保留原作者版权声明
- 修改后的代码也需要开源
- 不提供任何形式的担保

## 🙏 致谢

感谢以下项目和服务：

- [tb.anova.me](https://tb.anova.me) - 提供 APoU 使用的 API
- [TiebaArchiver](https://github.com/Sorceresssis/TiebaScraper) - DoPJ 基于此项目二次开发
- [aiotieba](https://github.com/Starry-OvO/aiotieba) - 优秀的异步贴吧 API 库
- [TiebaReader](https://github.com/Sorceresssis/TiebaReader) - 配套的阅读器工具

## 📮 联系方式

- 提交 Issue: [GitHub Issues](https://github.com/yourusername/AutoCCF/issues)
- 讨论交流: [GitHub Discussions](https://github.com/yourusername/AutoCCF/discussions)

## ⭐ Star History

如果觉得这个项目有用，请给个 Star ⭐

---

**注意**: 请合理使用本工具，尊重他人隐私，遵守相关法律法规。
