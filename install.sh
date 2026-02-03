#!/bin/bash
# AutoCCF 安装脚本 (Linux/Mac)

set -e

echo "=========================================="
echo "  AutoCCF 安装脚本"
echo "=========================================="
echo ""

# 检查 Python 版本
echo "检查 Python 版本..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
required_version="3.10"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
    echo "错误：需要 Python 3.10 或更高版本"
    echo "当前版本：$python_version"
    exit 1
fi

echo "✓ Python 版本：$python_version"
echo ""

# 安装依赖
echo "安装依赖包..."
echo "提示：如果下载速度慢，可以使用国内镜像源"
echo ""

read -p "是否使用阿里云镜像源？(y/n) " use_mirror

if [ "$use_mirror" = "y" ] || [ "$use_mirror" = "Y" ]; then
    echo "使用阿里云镜像源安装..."
    pip3 install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
else
    echo "使用默认源安装..."
    pip3 install -r requirements.txt
fi

echo ""
echo "✓ 依赖安装完成"
echo ""

# 创建配置目录
echo "创建配置文件..."
cd DoPJ
if [ ! -f "config/config.json" ]; then
    cp config/config.example.json config/config.json
    echo "✓ 已创建 DoPJ/config/config.json"
    echo "  请编辑此文件，填入你的 BDUSS"
else
    echo "✓ 配置文件已存在"
fi

cd ..
echo ""

# 完成
echo "=========================================="
echo "  安装完成！"
echo "=========================================="
echo ""
echo "快速开始："
echo ""
echo "1. 使用 APoU 获取用户发言列表："
echo "   python APoU.py -u 用户名"
echo ""
echo "2. 配置 DoPJ（填入 BDUSS）："
echo "   编辑 DoPJ/config/config.json"
echo ""
echo "3. 使用 DoPJ 获取详细内容："
echo "   cd DoPJ"
echo "   python DoPJ.py -i ../用户名_posts.json -c config/config.json"
echo ""
echo "更多信息请查看 README.md"
echo ""
