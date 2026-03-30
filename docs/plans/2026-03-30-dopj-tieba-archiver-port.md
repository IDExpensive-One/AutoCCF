# DoPJ TiebaArchiver 核心逻辑移植 实现计划

> 面向 AI 代理的工作者：使用 superpowers:subagent-driven-development 或 superpowers:executing-plans 逐任务实现此计划。

目标：将 TiebaArchiver 的生产者-消费者并发抓取模型和用户数据集中完善逻辑移植到 DoPJ，确保图片/视频/语音等媒体完整下载，集成测试改为 20 条帖子子集。

架构：新增 DoPJ/producer_consumer.py 并发协调器，重写 DoPJ/scraper.py 使用并发模型，新增 TiebaClient.get_user_info。现有 storage/cli/bridge 不变。

技术栈：Python 3.10+, asyncio, aiotieba, aiohttp, aiofiles, sqlite3

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| DoPJ/producer_consumer.py | 新增 | 生产者-消费者并发协调器(移植自 TiebaArchiver) |
| DoPJ/scraper.py | 修改 | 重写 _do_scrape 使用并发模型；新增 _complete_user_info |
| AutoCCF/tieba/client.py | 修改 | 新增 get_user_info() 方法 |
| tests/test_dopj/test_producer_consumer.py | 新增 | 协调器单元测试 |
| tests/test_dopj/test_scraper_integration.py | 修改 | 20帖子集测试+媒体落盘校验 |
| tests/test_autoccf/test_tieba/test_client.py | 修改 | get_user_info 回归测试 |

不动：DoPJ/storage.py, DoPJ/cli.py, electron/bridge.py, gui/, AutoCCF/config.py

---

## 任务 1：新增生产者-消费者协调器
创建 DoPJ/producer_consumer.py + tests/test_dopj/test_producer_consumer.py

## 任务 2：新增 TiebaClient.get_user_info
修改 AutoCCF/tieba/client.py + tests

## 任务 3：重写 ThreadScraper 使用并发模型
修改 DoPJ/scraper.py - 多producer拉页+多consumer处理+集中完善用户数据

## 任务 4：更新测试为 20 帖子集
修改 E2E 和集成测试

## 任务 5：完整回归验证 + 交叉审查

---

## 关键设计决策
1. 媒体下载保障：现有 ContentProcessor 已和 TiebaArchiver ContentService 等价
2. SQLite 线程安全：asyncio 消费者同一事件循环
3. 用户头像下载：暂不开启（对齐 TiebaArchiver NONE 模式）
4. 向后兼容：scrape_thread() 签名不变
