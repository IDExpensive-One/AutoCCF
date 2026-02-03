# 部署和迁移指南

本文档介绍如何将 AutoCCF 项目部署到 GitHub 或其他平台。

## 📦 准备工作

### 1. 清理敏感数据

在上传前，**务必确保**没有敏感信息：

```bash
# 检查是否有配置文件
find . -name "config.json" -not -path "*/config.example.json"
find . -name "*bduss*"
find . -name "*auth.json"

# 检查是否有输出数据
find . -name "*_posts.json" -not -path "*/example/*"
find . -name "progress.json"
find . -type d -name "posts"
```

如果发现敏感文件，删除或移动到安全位置：

```bash
# 删除配置文件
rm DoPJ/config/config.json

# 删除输出数据
rm -rf DoPJ/posts/
rm -rf DoPJ/*_output/
rm *_posts.json
rm progress.json
```

### 2. 验证 .gitignore

确认 `.gitignore` 包含所有敏感文件模式：

```bash
cat .gitignore | grep -E "config.json|bduss|posts.json"
```

## 🚀 部署到 GitHub

### 初次部署

1. **在 GitHub 创建新仓库**
   - 访问 https://github.com/new
   - 仓库名：`AutoCCF`
   - 描述：百度贴吧爬虫工具集
   - 选择：Public（公开）或 Private（私有）
   - **不要**初始化 README、.gitignore 或 LICENSE（我们已经有了）

2. **初始化本地仓库**
   ```bash
   cd /path/to/AutoCCF
   git init
   git add .
   git commit -m "feat: 初始化项目"
   ```

3. **连接到远程仓库**
   ```bash
   git remote add origin https://github.com/your-username/AutoCCF.git
   git branch -M main
   git push -u origin main
   ```

### 更新部署

```bash
# 拉取最新更改
git pull origin main

# 添加更改
git add .

# 提交更改
git commit -m "feat: 添加新功能"

# 推送到远程
git push origin main
```

## 🔑 配置 GitHub 仓库

### 1. 添加 README 徽章

编辑 `README.md`，更新徽章链接：

```markdown
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Stars](https://img.shields.io/github/stars/your-username/AutoCCF.svg)](https://github.com/your-username/AutoCCF/stargazers)
[![Issues](https://img.shields.io/github/issues/your-username/AutoCCF.svg)](https://github.com/your-username/AutoCCF/issues)
```

### 2. 配置 GitHub Topics

在仓库页面添加相关主题标签：
- `tieba`
- `web-scraping`
- `crawler`
- `python`
- `asyncio`
- `data-collection`

### 3. 设置 About

在仓库设置中添加：
- **Description**: 百度贴吧爬虫工具集 - 两步式设计，快速获取列表+深度爬取详情
- **Website**: (如果有文档站点)
- **Topics**: 如上所述

### 4. 启用功能

在 Settings → Features 中启用：
- ✅ Issues
- ✅ Discussions
- ✅ Wiki（可选）
- ✅ Projects（可选）

### 5. 配置分支保护

在 Settings → Branches → Add rule:
- Branch name pattern: `main`
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging

## 📱 其他平台部署

### Gitee（码云）

```bash
# 创建 Gitee 仓库后
git remote add gitee https://gitee.com/your-username/AutoCCF.git
git push gitee main
```

### GitLab

```bash
# 创建 GitLab 仓库后
git remote add gitlab https://gitlab.com/your-username/AutoCCF.git
git push gitlab main
```

### 同时推送到多个远程

编辑 `.git/config`：

```ini
[remote "all"]
    url = https://github.com/your-username/AutoCCF.git
    url = https://gitee.com/your-username/AutoCCF.git
    url = https://gitlab.com/your-username/AutoCCF.git
```

然后：
```bash
git push all main
```

## 📝 发布版本

### 创建 Release

1. **打标签**
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0"
   git push origin v1.0.0
   ```

2. **在 GitHub 创建 Release**
   - 访问仓库的 Releases 页面
   - 点击 "Create a new release"
   - 选择标签：`v1.0.0`
   - 标题：`v1.0.0 - 初始版本`
   - 描述：从 `CHANGELOG.md` 复制相应版本的更新内容
   - 上传资产（可选）：打包后的程序
   - 点击 "Publish release"

### 自动化发布

使用 GitHub Actions 自动化：

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
```

## 🌐 文档站点

### 使用 GitHub Pages

1. **创建 docs 分支**
   ```bash
   git checkout --orphan gh-pages
   git rm -rf .
   echo "# AutoCCF Documentation" > index.md
   git add index.md
   git commit -m "docs: 初始化文档"
   git push origin gh-pages
   ```

2. **在 Settings → Pages 中配置**
   - Source: Deploy from a branch
   - Branch: `gh-pages`
   - Folder: `/` (root)

3. **访问**: https://your-username.github.io/AutoCCF/

## 🔒 安全检查清单

发布前检查：

- [ ] 没有提交真实的 BDUSS
- [ ] 没有提交 `config.json`（只有 `config.example.json`）
- [ ] 没有提交个人数据或爬取结果
- [ ] `.gitignore` 配置正确
- [ ] LICENSE 文件已添加
- [ ] README 中没有敏感信息
- [ ] 代码中没有硬编码的凭证

## 📊 监控和分析

### GitHub Insights

定期查看：
- **Traffic**: 访问量和克隆数
- **Community**: 贡献者和活动
- **Network**: Fork 和引用

### 添加分析工具

可选的第三方工具：
- [Shields.io](https://shields.io/) - 徽章生成
- [CodeCov](https://codecov.io/) - 代码覆盖率
- [Snyk](https://snyk.io/) - 安全扫描

## 🤝 社区建设

### 初期推广

1. 在相关社区分享（遵守规则）
2. 写一篇使用教程博客
3. 录制演示视频
4. 在 Twitter/微博等社交媒体分享

### 维护建议

- 及时回复 Issue
- 欢迎 Pull Request
- 定期更新文档
- 发布新版本

## ❓ 常见问题

### Q: 如何撤销已提交的敏感信息？

```bash
# 使用 git-filter-repo
pip install git-filter-repo
git filter-repo --path config.json --invert-paths

# 强制推送（危险操作！）
git push origin --force --all
```

**注意**: 如果已经推送到 GitHub，敏感信息可能已被他人看到。建议：
1. 立即更改凭证（修改密码使 BDUSS 失效）
2. 使用上述方法清理历史
3. 通知协作者

### Q: 如何创建镜像仓库？

```bash
# 克隆镜像
git clone --mirror https://github.com/original/AutoCCF.git
cd AutoCCF.git

# 推送到新位置
git push --mirror https://github.com/your-username/AutoCCF.git
```

### Q: 如何从其他平台迁移？

如果代码在 Gitee/GitLab：
```bash
git clone https://gitee.com/original/AutoCCF.git
cd AutoCCF
git remote set-url origin https://github.com/your-username/AutoCCF.git
git push -u origin main
```

---

**祝部署顺利！** 如有问题，欢迎提 Issue 🎉
