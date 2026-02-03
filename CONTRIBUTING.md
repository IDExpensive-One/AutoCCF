# 贡献指南

感谢你对 AutoCCF 项目的关注！我们欢迎任何形式的贡献。

## 🎯 贡献方式

### 报告问题（Bug Report）

在提交 Issue 前，请先搜索是否已有相关问题。如果没有，请创建新 Issue 并包含：

**必需信息**：
- 操作系统和版本（如 Windows 11, Ubuntu 22.04）
- Python 版本（`python --version`）
- 依赖版本（`pip freeze | grep -E "aiotieba|aiohttp|requests"`）
- 完整的错误信息（包括堆栈跟踪）

**问题描述**：
1. 问题的简短描述
2. 详细的复现步骤
3. 预期行为
4. 实际行为
5. 相关截图（如果有）

**示例**：
```
### 问题描述
使用 DoPJ 爬取时，所有账户都被标记为失效

### 环境信息
- OS: Windows 11
- Python: 3.11.5
- aiotieba: 4.6.1

### 复现步骤
1. 配置 3 个有效的 BDUSS
2. 运行 `python DoPJ.py -i test.json -c config.json`
3. 几分钟后所有账户都显示被封禁

### 预期行为
账户应该轮换使用，避免被封

### 实际行为
所有账户都被立即标记为失效

### 错误信息
[粘贴完整错误信息]
```

### 功能请求（Feature Request）

描述你希望添加的功能：

1. **功能描述**：详细说明新功能是什么
2. **使用场景**：为什么需要这个功能
3. **实现建议**：如果有想法，可以提供实现思路
4. **替代方案**：是否考虑过其他解决方案

### 提交代码（Pull Request）

#### 开发流程

1. **Fork 仓库**
   ```bash
   # 在 GitHub 上点击 Fork 按钮
   ```

2. **克隆到本地**
   ```bash
   git clone https://github.com/your-username/AutoCCF.git
   cd AutoCCF
   ```

3. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

4. **开发和测试**
   - 编写代码
   - 添加必要的注释（中文）
   - 测试功能是否正常

5. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加某某功能"
   # 或
   git commit -m "fix: 修复某某问题"
   ```

6. **推送到 GitHub**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写详细的描述
   - 等待审核和反馈

#### Commit 规范

使用语义化的 commit message：

- `feat:` - 新功能
- `fix:` - 修复 bug
- `docs:` - 文档更新
- `style:` - 代码格式调整（不影响功能）
- `refactor:` - 代码重构
- `test:` - 添加或修改测试
- `chore:` - 构建工具或辅助工具的变动

**示例**：
```
feat: 添加多进程支持以提升爬取速度
fix: 修复 SimplePath 缺少方法的问题
docs: 更新 README 中的安装说明
refactor: 重构账户管理器代码结构
```

#### 代码规范

**Python 代码风格**：

1. **遵循 PEP 8**
   ```bash
   # 使用 black 格式化
   pip install black
   black *.py DoPJ/
   ```

2. **函数文档**
   ```python
   def crawl_user_posts(self, username: str) -> List[dict]:
       """
       爬取指定用户的所有发言

       Args:
           username: 目标用户名

       Returns:
           所有爬取到的发言列表

       Raises:
           ValueError: 如果用户名为空
           NetworkError: 如果网络连接失败
       """
       pass
   ```

3. **类型注解**
   ```python
   from typing import List, Dict, Optional

   def parse_url(url: str) -> Optional[tuple[int, Optional[int]]]:
       pass
   ```

4. **错误处理**
   ```python
   try:
       result = risky_operation()
   except SpecificError as e:
       logger.error(f"操作失败: {e}")
       return None
   ```

5. **命名规范**
   - 类名：`PascalCase` (如 `AccountManager`)
   - 函数/变量：`snake_case` (如 `get_next_task`)
   - 常量：`UPPER_SNAKE_CASE` (如 `MAX_RETRIES`)
   - 私有方法：`_leading_underscore` (如 `_update_stats`)

#### Pull Request 检查清单

提交 PR 前请确认：

- [ ] 代码已通过本地测试
- [ ] 添加了必要的注释和文档
- [ ] 更新了相关的 README 或文档
- [ ] 没有提交敏感信息（BDUSS、密码等）
- [ ] Commit message 遵循规范
- [ ] 代码风格符合 PEP 8
- [ ] 添加了类型注解
- [ ] 处理了可能的异常情况

## 🧪 测试

### 运行测试

```bash
# APoU 测试
python APoU.py -u test_user

# DoPJ 基础测试
cd DoPJ
python test_simple.py

# DoPJ 单帖测试
python test_one_post.py

# DoPJ 语音测试
python test_voice_scrape.py
```

### 添加测试

如果添加了新功能，请考虑添加相应的测试代码。

## 📝 文档

### 更新文档

如果你的更改影响到了用户使用方式：

1. 更新 `README.md`
2. 更新 `DoPJ/README.md`（如果涉及 DoPJ）
3. 更新 `CLAUDE.md`（如果涉及技术架构）

### 文档风格

- 使用中文
- 提供代码示例
- 包含常见问题的解决方案
- 保持格式一致

## 🔐 安全性

### 敏感信息

**绝对不要提交**：
- 真实的 BDUSS
- 配置文件 `config.json`
- 个人凭证
- 爬取的数据

**.gitignore 已经配置**：
```
DoPJ/config/config.json
**/tieba_auth.json
**/bduss.txt
```

### 安全审查

如果你的更改涉及：
- 网络请求
- 文件操作
- 凭证处理

请确保：
- 输入验证
- 错误处理
- 日志脱敏

## 🎨 UI/UX 改进

虽然是 CLI 工具，但用户体验仍然重要：

- 清晰的输出信息
- 合理的进度显示
- 友好的错误提示
- 颜色和格式增强可读性

## 📮 沟通渠道

- **GitHub Issues** - 报告 bug 和功能请求
- **GitHub Discussions** - 一般讨论和问答
- **Pull Requests** - 代码贡献

## 🙏 行为准则

- 尊重所有贡献者
- 提供建设性的反馈
- 保持友好和专业
- 遵守开源社区规范

## ❓ 需要帮助？

- 查看 [README.md](README.md) 了解基本使用
- 查看 [CLAUDE.md](CLAUDE.md) 了解技术细节
- 在 Issues 中搜索相关问题
- 在 Discussions 中提问

---

再次感谢你的贡献！每一个 PR、Issue 或 Star 都是对项目的支持 ❤️
