"""
配置常量
集中管理所有可配置参数
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CrawlerConfig:
    """爬虫配置类"""

    # API 配置
    base_url: str = "https://tb.anova.me/getPostsNew"

    # 请求头
    headers: Dict[str, str] = field(default_factory=lambda: {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    })

    # 超时设置（秒）
    request_timeout: int = 15

    # 重试配置
    max_retries: int = 3  # 普通错误最大重试次数
    retry_delay: float = 5.0  # 重试间隔（秒）

    # 空页面重试配置（API 有时临时返回空数据）
    max_empty_page_retries: int = 5  # 空页面最大重试次数
    empty_page_retry_delay: float = 3.0  # 空页面重试间隔（秒）

    # 速率限制
    page_delay: float = 2.0  # 每页之间的延迟（秒）

    # 分页
    page_size: int = 20  # 每页数据条数（API 固定值）

    # 输出配置
    raw_data_dir: str = "raw_data"  # 原始数据保存目录

    # 调试配置
    debug: bool = False  # 是否输出调试信息


# 默认配置实例
DEFAULT_CONFIG = CrawlerConfig()
