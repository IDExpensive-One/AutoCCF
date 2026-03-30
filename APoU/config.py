"""
配置常量
集中管理所有可配置参数
"""
from dataclasses import dataclass


@dataclass(init=False)
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

    def __init__(
        self,
        bduss: str = "",
        page_delay: float = 2.0,
        page_size: int = 20,
        max_retries: int = 3,
        retry_delay: float = 3.0,
        max_empty_page_retries: int = 3,
        empty_page_retry_delay: float = 3.0,
        request_timeout: float = 30.0,
        anova_base_url: str = "https://tb.anova.me/getPostsNew",
        anova_page_delay: float = 3.0,
        anova_request_timeout: float = 60.0,
        anova_max_retries: int = 3,
        raw_data_dir: str = "raw_data",
        debug: bool = False,
        base_url: str | None = None,
    ):
        """
        初始化爬虫配置

        Args:
            base_url: 旧版字段，兼容历史调用；若传入则覆盖 anova_base_url
        """
        self.bduss = bduss
        self.page_delay = page_delay
        self.page_size = page_size
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_empty_page_retries = max_empty_page_retries
        self.empty_page_retry_delay = empty_page_retry_delay
        self.request_timeout = request_timeout
        self.anova_base_url = base_url if base_url is not None else anova_base_url
        self.anova_page_delay = anova_page_delay
        self.anova_request_timeout = anova_request_timeout
        self.anova_max_retries = anova_max_retries
        self.raw_data_dir = raw_data_dir
        self.debug = debug

    @property
    def base_url(self) -> str:
        """兼容旧配置字段，返回 anova 接口地址"""
        return self.anova_base_url

    @base_url.setter
    def base_url(self, value: str) -> None:
        """兼容旧配置字段，允许通过 base_url 更新 anova 接口地址"""
        self.anova_base_url = value


# 默认配置实例
DEFAULT_CONFIG = CrawlerConfig()
