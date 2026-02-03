# 更新日志

所有重要的项目更改都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划添加
- [ ] 支持多进程爬取
- [ ] 添加 Web UI 界面
- [ ] 支持导出为其他格式（JSON、CSV、Excel）
- [ ] 添加数据分析功能
- [ ] 支持自定义爬取规则

## [1.0.0] - 2026-02-03

### 新增
- ✨ **APoU** - 用户发言列表快速获取工具
  - 支持通过 tb.anova.me API 获取用户所有发言
  - 自动重试机制（普通失败3次，空数据5次）
  - 同时保存原始数据和处理后数据
  - 内置速率限制（2秒间隔）

- ✨ **DoPJ** - 帖子详细内容获取工具
  - 基于 TiebaArchiver 二次开发
  - 多线程并发爬取（可配置线程数）
  - 多账户轮换机制（避免风控）
  - 断点续传功能（中断后可继续）
  - 失败自动重试（可配置重试次数）
  - 即时保存机制（每个任务完成立即保存）
  - 完整的媒体文件支持：
    - ✅ 文本内容（SQLite 数据库）
    - ✅ 图片下载
    - ✅ 视频下载
    - ✅ 语音文件下载（AMR 格式）
    - ✅ 用户头像下载
  - 进度追踪和实时统计
  - 索引化目录结构（`索引_tid_pid`）

### 文档
- 📝 完整的中文文档
- 📝 详细的技术架构文档（CLAUDE.md）
- 📝 使用示例和常见问题
- 📝 贡献指南（CONTRIBUTING.md）

### 工具
- 🔧 一键安装脚本（Windows/Linux/Mac）
- 🔧 统一的依赖管理（requirements.txt）
- 🔧 配置文件模板（config.example.json）

### 测试
- ✅ URL 解析器测试通过
- ✅ 账户管理器测试通过
- ✅ 任务管理器测试通过
- ✅ 单帖爬取测试通过（109个帖子/回复，20个用户）
- ✅ 语音保存测试通过（229个语音文件，1.4MB）

### 开源准备
- 📄 MIT 许可证
- 📄 .gitignore 配置
- 📄 GitHub Actions CI/CD
- 📄 完整的项目结构

## [0.1.0] - 2026-02-01

### 新增
- 🎉 项目初始化
- 🎉 APoU.py 基础版本
- 🎉 引入 TiebaArchiver 作为参考

---

## 版本说明

### 版本格式

版本号格式：`主版本号.次版本号.修订号`

- **主版本号**：不兼容的 API 修改
- **次版本号**：向后兼容的功能性新增
- **修订号**：向后兼容的问题修正

### 变更类型

- `新增` - 新功能
- `更改` - 已有功能的变更
- `弃用` - 即将移除的功能
- `移除` - 已移除的功能
- `修复` - 问题修复
- `安全` - 安全问题修复

[Unreleased]: https://github.com/yourusername/AutoCCF/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/yourusername/AutoCCF/releases/tag/v1.0.0
[0.1.0]: https://github.com/yourusername/AutoCCF/releases/tag/v0.1.0
