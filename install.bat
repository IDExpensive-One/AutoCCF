@echo off
REM AutoCCF 安装脚本 (Windows)
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ==========================================
echo   AutoCCF 安装脚本
echo ==========================================
echo.

REM 检查 Python
echo 检查 Python 版本...
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误：未找到 Python
    echo 请先安装 Python 3.10 或更高版本
    echo 下载地址：https://www.python.org/downloads/
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set python_version=%%i
echo √ Python 版本：%python_version%
echo.

REM 安装依赖
echo 安装依赖包...
echo 提示：如果下载速度慢，建议使用国内镜像源
echo.

set /p use_mirror="是否使用阿里云镜像源？(y/n) "

if /i "%use_mirror%"=="y" (
    echo 使用阿里云镜像源安装...
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
) else (
    echo 使用默认源安装...
    pip install -r requirements.txt
)

if errorlevel 1 (
    echo.
    echo 错误：依赖安装失败
    pause
    exit /b 1
)

echo.
echo √ 依赖安装完成
echo.

REM 创建配置文件
echo 创建配置文件...
cd DoPJ
if not exist "config\config.json" (
    copy "config\config.example.json" "config\config.json" > nul
    echo √ 已创建 DoPJ\config\config.json
    echo   请编辑此文件，填入你的 BDUSS
) else (
    echo √ 配置文件已存在
)

cd ..
echo.

REM 完成
echo ==========================================
echo   安装完成！
echo ==========================================
echo.
echo 快速开始：
echo.
echo 1. 使用 APoU 获取用户发言列表：
echo    python APoU.py -u 用户名
echo.
echo 2. 配置 DoPJ（填入 BDUSS）：
echo    编辑 DoPJ\config\config.json
echo.
echo 3. 使用 DoPJ 获取详细内容：
echo    cd DoPJ
echo    python DoPJ.py -i ..\用户名_posts.json -c config\config.json
echo.
echo 更多信息请查看 README.md
echo.

pause
