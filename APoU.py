#!/usr/bin/env python3
"""
APoU - All Posts of User
百度贴吧用户发言列表爬虫

使用方法：
    python APoU.py -u <用户名>
    python APoU.py --username <用户名>
"""
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    from APoU import main
    main()
