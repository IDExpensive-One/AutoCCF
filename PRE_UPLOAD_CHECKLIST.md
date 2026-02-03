# 上传前检查清单

在将项目上传到 GitHub 或其他开源平台前，请逐项检查以下内容。

## ✅ 安全检查

### 敏感数据检查

- [ ] **配置文件**
  ```bash
  # 运行以下命令检查
  find . -name "config.json" -not -path "*/config.example.json" -not -path "*/.git/*"
  ```
  - 确保只有 `config.example.json`，没有 `config.json`

- [ ] **BDUSS 文件**
  ```bash
  find . -name "*bduss*" -not -path "*/.git/*"
  find . -name "*auth.json" -not -path "*/.git/*"
  ```
  - 确保没有包含真实 BDUSS 的文件

- [ ] **爬取数据**
  ```bash
  find . -name "*_posts.json" -not -path "*/example/*" -not -path "*/.git/*"
  find . -name "progress.json" -not -path "*/.git/*"
  find . -type d -name "posts" -not -path "*/.git/*"
  ```
  - 确保没有实际的爬取结果

- [ ] **测试输出**
  ```bash
  find . -type d -name "*_output" -not -path "*/.git/*"
  find . -name "test_*.json" -not -path "*/.git/*" | grep -v url_parser
  ```
  - 确保没有测试时产生的输出

- [ ] **日志文件**
  ```bash
  find . -name "*.log" -not -path "*/.git/*"
  ```
  - 确保没有包含敏感信息的日志

- [ ] **代码中的硬编码**
  ```bash
  # 搜索可能的硬编码凭证
  grep -r "BDUSS.*=" . --include="*.py" | grep -v "example"
  grep -r "password.*=" . --include="*.py"
  ```
  - 确保没有硬编码的凭证

### .gitignore 检查

- [ ] **.gitignore 存在**
  ```bash
  ls -la .gitignore
  ```

- [ ] **.gitignore 包含必要规则**
  ```bash
  cat .gitignore | grep -E "config.json|bduss|posts.json|progress.json"
  ```
  - 应该包含：`config.json`, `*bduss*`, `*_posts.json`, `progress.json`

## 📝 文档检查

### 必需文件

- [ ] **README.md** 存在且完整
  - 包含项目描述
  - 包含安装说明
  - 包含使用示例
  - 包含常见问题

- [ ] **LICENSE** 存在
  ```bash
  ls -la LICENSE
  ```
  - 确认许可证类型（MIT）

- [ ] **CLAUDE.md** 存在
  - 包含技术架构说明

- [ ] **CONTRIBUTING.md** 存在
  - 包含贡献指南

- [ ] **CHANGELOG.md** 存在
  - 记录版本历史

### 文档内容

- [ ] **更新 README 中的链接**
  - 将 `yourusername` 替换为实际用户名
  - 更新徽章链接

- [ ] **检查中文编码**
  ```bash
  file -bi *.md DoPJ/*.md
  ```
  - 确保所有 Markdown 文件都是 UTF-8 编码

## 🔧 代码检查

### 代码质量

- [ ] **移除测试文件**（可选）
  ```bash
  # 如果不想上传测试文件
  rm DoPJ/test_*.py
  ```
  - 或者确保测试文件在 .gitignore 中

- [ ] **检查导入路径**
  ```bash
  python -m py_compile APoU.py
  cd DoPJ && python -m py_compile DoPJ.py
  ```
  - 确保没有语法错误

- [ ] **代码格式化**（可选）
  ```bash
  # 安装 black
  pip install black
  # 格式化代码
  black *.py DoPJ/
  ```

### 依赖文件

- [ ] **requirements.txt 正确**
  ```bash
  cat requirements.txt
  ```
  - 包含所有必需的依赖
  - 版本号正确

- [ ] **安装脚本可执行**
  ```bash
  # Linux/Mac
  chmod +x install.sh
  # Windows
  ls -la install.bat
  ```

## 📦 项目结构检查

- [ ] **目录结构合理**
  ```bash
  tree -L 2 -I '__pycache__|*.pyc|.git'
  ```
  - 核心代码在根目录或 DoPJ/
  - 示例数据在 example/
  - 配置模板在 config/

- [ ] **__pycache__ 已排除**
  ```bash
  find . -type d -name "__pycache__" -not -path "*/.git/*"
  ```
  - 应该返回空结果（或确保在 .gitignore 中）

- [ ] **不必要的文件已移除**
  - 临时文件（.tmp, .bak）
  - IDE 配置（.vscode, .idea）
  - 操作系统文件（.DS_Store, Thumbs.db）

## 🚀 Git 检查

### Git 配置

- [ ] **Git 已初始化**
  ```bash
  git status
  ```

- [ ] **远程仓库配置**
  ```bash
  git remote -v
  ```
  - 如果已有远程，确认 URL 正确

### 提交历史

- [ ] **首次提交准备**
  ```bash
  git add .
  git status
  ```
  - 查看将要提交的文件
  - 确认没有敏感文件

- [ ] **提交信息规范**
  ```bash
  git commit -m "feat: 初始化项目

  - 添加 APoU 和 DoPJ 工具
  - 完整的文档和示例
  - 开源友好的项目结构
  "
  ```

## 🌐 平台准备

### GitHub 仓库

- [ ] **在 GitHub 创建新仓库**
  - 仓库名：AutoCCF
  - 描述已填写
  - 可见性已选择（Public/Private）
  - **不要**初始化 README

- [ ] **SSH 密钥配置**（推荐）
  ```bash
  ssh -T git@github.com
  ```
  - 或使用 HTTPS（需要 token）

### 首次推送

- [ ] **准备推送命令**
  ```bash
  git remote add origin git@github.com:your-username/AutoCCF.git
  git branch -M main
  git push -u origin main
  ```

## 📋 最终检查清单

执行以下命令进行自动检查：

```bash
#!/bin/bash
echo "=== 开始安全检查 ==="

# 检查敏感文件
echo -e "\n1. 检查配置文件..."
find . -name "config.json" -not -path "*/config.example.json" -not -path "*/.git/*" && echo "警告：发现 config.json" || echo "✓ 通过"

echo -e "\n2. 检查 BDUSS 文件..."
find . -name "*bduss*" -not -path "*/.git/*" && echo "警告：发现 bduss 文件" || echo "✓ 通过"

echo -e "\n3. 检查输出数据..."
find . -name "*_posts.json" -not -path "*/example/*" -not -path "*/.git/*" && echo "警告：发现输出数据" || echo "✓ 通过"

echo -e "\n4. 检查 .gitignore..."
test -f .gitignore && echo "✓ .gitignore 存在" || echo "警告：缺少 .gitignore"

echo -e "\n5. 检查 LICENSE..."
test -f LICENSE && echo "✓ LICENSE 存在" || echo "警告：缺少 LICENSE"

echo -e "\n6. 检查 README.md..."
test -f README.md && echo "✓ README.md 存在" || echo "警告：缺少 README.md"

echo -e "\n=== 检查完成 ==="
```

将上述脚本保存为 `check.sh` 并运行：
```bash
chmod +x check.sh
./check.sh
```

## ✨ 全部通过？

如果所有检查都通过，你可以安全地推送代码了！

```bash
git push -u origin main
```

## ⚠️ 发现问题？

如果发现敏感信息：

1. **不要推送**
2. 删除或移动敏感文件
3. 重新检查
4. 确认 .gitignore 配置正确
5. 再次运行检查清单

## 📞 需要帮助？

如果不确定某个文件是否应该上传，参考：
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署指南
- [CONTRIBUTING.md](CONTRIBUTING.md) - 贡献指南
- [.gitignore](.gitignore) - 忽略规则

---

**安全第一！** 在确认所有检查通过前，不要上传代码 🔒
