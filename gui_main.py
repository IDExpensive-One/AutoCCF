#!/usr/bin/env python3
"""
AutoCCF GUI 入口点

启动 AutoCCF 图形界面应用程序。
"""
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    """主函数"""
    try:
        from gui.app import run_app
        run_app()
    except ImportError as e:
        print(f"错误: 无法导入 GUI 模块: {e}")
        print()
        print("请确保已安装 Flet:")
        print("  pip install flet")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
