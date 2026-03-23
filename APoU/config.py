"""
配置常量
集中管理所有可配置参数
"""
from dataclasses import dataclass


@dataclass
class CrawlerConfig:
    """爬虫配置类"""

    # 认证（必需）
    bduss: str = ""

    # 分页
    page_delay: float = 2.0  # 每页之间的延迟（秒）
    page_size: int = 20  # 每页数据条数（最大 50）

    # 重试配置
    max_retries: int = 3  # 最大重试次数
    retry_delay: float = 3.0  # 重试间隔（秒）

    # 空页面重试配置（API 有时临时返回空数据）
    max_empty_page_retries: int = 3
    empty_page_retry_delay: float = 3.0

    # 请求超时（秒）
    request_timeout: float = 30.0

    # tb.anova.me 回退引擎配置
    anova_base_url: str = "https://tb.anova.me/getPostsNew"
    anova_page_delay: float = 3.0  # anova 每页延迟（服务器较慢，设更长）
    anova_request_timeout: float = 60.0  # anova 请求超时（响应较慢）
    anova_max_retries: int = 3  # anova 单页最大重试次数

    # 输出配置
    raw_data_dir: str = "raw_data"

    # 调试配置
    debug: bool = False


# 默认配置实例
DEFAULT_CONFIG = CrawlerConfig()
