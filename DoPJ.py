#!/usr/bin/env python3
"""
DoPJ - Detail of Posts JSON
百度贴吧帖子详情爬虫

用法：
    python DoPJ.py -i posts.json -c config.json
    python DoPJ.py -i posts.json -c config.json -o output -t 5
"""
import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    from DoPJ import main
    main()
