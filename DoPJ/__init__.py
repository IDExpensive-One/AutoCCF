"""
DoPJ - Detail of Posts JSON

从 APoU 输出的 JSON 获取每个帖子的详细内容。

特性：
- 多线程并发爬取
- 多账户轮换避免风控
- 即时保存，断点续传
- 失败自动重试
- 与 TiebaReader 兼容的输出格式
"""

__version__ = "2.0.0"
__author__ = "AutoCCF Contributors"

from DoPJ.scraper import ThreadScraper, scrape_thread
from DoPJ.storage import ContentDatabase
from DoPJ.cli import main

__all__ = [
    "ThreadScraper",
    "scrape_thread",
    "ContentDatabase",
    "main",
    "__version__",
]
