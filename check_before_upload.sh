#!/bin/bash
# 上传前自动安全检查脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

error_count=0
warning_count=0

echo "=========================================="
echo "  AutoCCF 上传前安全检查"
echo "=========================================="
echo ""

# 检查函数
check_files() {
    local pattern="$1"
    local description="$2"
    local exclude="$3"

    echo -n "检查 $description... "

    if [ -n "$exclude" ]; then
        results=$(find . -name "$pattern" -not -path "$exclude" -not -path "*/.git/*" 2>/dev/null)
    else
        results=$(find . -name "$pattern" -not -path "*/.git/*" 2>/dev/null)
    fi

    if [ -n "$results" ]; then
        echo -e "${RED}✗ 发现问题${NC}"
        echo "$results" | sed 's/^/    /'
        ((error_count++))
        return 1
    else
        echo -e "${GREEN}✓ 通过${NC}"
        return 0
    fi
}

check_required_file() {
    local file="$1"
    local description="$2"

    echo -n "检查 $description... "

    if [ -f "$file" ]; then
        echo -e "${GREEN}✓ 存在${NC}"
        return 0
    else
        echo -e "${RED}✗ 缺失${NC}"
        ((error_count++))
        return 1
    fi
}

# 1. 敏感文件检查
echo "=== 1. 敏感数据检查 ==="
check_files "config.json" "配置文件" "*/config.example.json"
check_files "*bduss*" "BDUSS 文件"
check_files "*auth.json" "认证文件"
check_files "*_posts.json" "爬取数据" "*/example/*"
check_files "progress.json" "进度文件"
check_files "*.log" "日志文件"

# 检查输出目录
echo -n "检查输出目录... "
output_dirs=$(find . -type d \( -name "posts" -o -name "*_output" \) -not -path "*/.git/*" 2>/dev/null)
if [ -n "$output_dirs" ]; then
    echo -e "${RED}✗ 发现输出目录${NC}"
    echo "$output_dirs" | sed 's/^/    /'
    ((error_count++))
else
    echo -e "${GREEN}✓ 通过${NC}"
fi

echo ""

# 2. 必需文件检查
echo "=== 2. 必需文件检查 ==="
check_required_file ".gitignore" ".gitignore"
check_required_file "LICENSE" "LICENSE"
check_required_file "README.md" "README.md"
check_required_file "requirements.txt" "requirements.txt"
check_required_file "CLAUDE.md" "CLAUDE.md"
check_required_file "CONTRIBUTING.md" "CONTRIBUTING.md"
check_required_file "CHANGELOG.md" "CHANGELOG.md"

echo ""

# 3. .gitignore 内容检查
echo "=== 3. .gitignore 内容检查 ==="
echo -n "检查 .gitignore 规则... "

required_patterns=("config.json" "bduss" "posts.json" "progress.json" "__pycache__")
missing_patterns=()

for pattern in "${required_patterns[@]}"; do
    if ! grep -q "$pattern" .gitignore 2>/dev/null; then
        missing_patterns+=("$pattern")
    fi
done

if [ ${#missing_patterns[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ 完整${NC}"
else
    echo -e "${YELLOW}⚠ 缺少规则${NC}"
    for pattern in "${missing_patterns[@]}"; do
        echo "    - $pattern"
    done
    ((warning_count++))
fi

echo ""

# 4. 代码检查
echo "=== 4. 代码检查 ==="

echo -n "检查 Python 语法... "
if python3 -m py_compile APoU.py 2>/dev/null && \
   python3 -m py_compile DoPJ/DoPJ.py 2>/dev/null; then
    echo -e "${GREEN}✓ 通过${NC}"
else
    echo -e "${RED}✗ 语法错误${NC}"
    ((error_count++))
fi

echo -n "检查硬编码凭证... "
hardcoded=$(grep -r "BDUSS.*=" . --include="*.py" 2>/dev/null | grep -v "example" | grep -v ".pyc" | grep -v "__pycache__" || true)
if [ -n "$hardcoded" ]; then
    echo -e "${YELLOW}⚠ 发现可疑代码${NC}"
    echo "$hardcoded" | sed 's/^/    /'
    ((warning_count++))
else
    echo -e "${GREEN}✓ 通过${NC}"
fi

echo ""

# 5. 项目结构检查
echo "=== 5. 项目结构检查 ==="

echo -n "检查 __pycache__ 目录... "
pycache_dirs=$(find . -type d -name "__pycache__" -not -path "*/.git/*" 2>/dev/null)
if [ -n "$pycache_dirs" ]; then
    echo -e "${YELLOW}⚠ 发现缓存目录${NC}"
    echo "$pycache_dirs" | sed 's/^/    /'
    ((warning_count++))
else
    echo -e "${GREEN}✓ 通过${NC}"
fi

echo -n "检查 .pyc 文件... "
pyc_files=$(find . -name "*.pyc" -not -path "*/.git/*" 2>/dev/null)
if [ -n "$pyc_files" ]; then
    echo -e "${YELLOW}⚠ 发现编译文件${NC}"
    echo "$pyc_files" | wc -l | sed 's/^/    发现 /' | sed 's/$/ 个文件/'
    ((warning_count++))
else
    echo -e "${GREEN}✓ 通过${NC}"
fi

echo ""

# 6. Git 检查
echo "=== 6. Git 检查 ==="

echo -n "检查 Git 初始化... "
if [ -d ".git" ]; then
    echo -e "${GREEN}✓ 已初始化${NC}"
else
    echo -e "${YELLOW}⚠ 未初始化${NC}"
    echo "    运行: git init"
    ((warning_count++))
fi

echo -n "检查 Git 远程仓库... "
if git remote -v &>/dev/null; then
    remotes=$(git remote -v | grep -v "^$")
    if [ -n "$remotes" ]; then
        echo -e "${GREEN}✓ 已配置${NC}"
        echo "$remotes" | sed 's/^/    /'
    else
        echo -e "${YELLOW}⚠ 未配置${NC}"
        echo "    运行: git remote add origin <URL>"
        ((warning_count++))
    fi
else
    echo -e "${YELLOW}⚠ Git 未初始化${NC}"
    ((warning_count++))
fi

echo ""

# 7. 文件编码检查
echo "=== 7. 文件编码检查 ==="
echo -n "检查 Markdown 文件编码... "

non_utf8_files=()
for file in *.md DoPJ/*.md; do
    if [ -f "$file" ]; then
        encoding=$(file -bi "$file" | cut -d'=' -f2)
        if [ "$encoding" != "utf-8" ] && [ "$encoding" != "us-ascii" ]; then
            non_utf8_files+=("$file ($encoding)")
        fi
    fi
done

if [ ${#non_utf8_files[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ 全部 UTF-8${NC}"
else
    echo -e "${YELLOW}⚠ 发现非 UTF-8 文件${NC}"
    for file in "${non_utf8_files[@]}"; do
        echo "    - $file"
    done
    ((warning_count++))
fi

echo ""

# 总结
echo "=========================================="
echo "  检查完成"
echo "=========================================="
echo ""

if [ $error_count -eq 0 ] && [ $warning_count -eq 0 ]; then
    echo -e "${GREEN}✓ 所有检查通过！可以安全上传。${NC}"
    echo ""
    echo "建议的推送命令："
    echo "  git add ."
    echo "  git commit -m \"feat: 初始化项目\""
    echo "  git push -u origin main"
    exit 0
elif [ $error_count -eq 0 ]; then
    echo -e "${YELLOW}⚠ 发现 $warning_count 个警告${NC}"
    echo ""
    echo "建议："
    echo "  1. 检查上述警告"
    echo "  2. 根据需要修复"
    echo "  3. 如果警告可接受，可以继续上传"
    exit 0
else
    echo -e "${RED}✗ 发现 $error_count 个错误，$warning_count 个警告${NC}"
    echo ""
    echo "必须修复所有错误才能安全上传！"
    echo ""
    echo "修复建议："
    echo "  1. 删除所有敏感文件"
    echo "  2. 确保 .gitignore 配置正确"
    echo "  3. 再次运行此脚本检查"
    exit 1
fi
