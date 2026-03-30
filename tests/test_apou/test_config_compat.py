"""
APoU config compatibility tests.
"""

from APoU.config import CrawlerConfig


class TestCrawlerConfigCompat:
    """测试 CrawlerConfig 旧字段兼容。"""

    def test_base_url_property_maps_to_anova_base_url(self):
        """读取 base_url 时应返回 anova_base_url。"""
        config = CrawlerConfig(anova_base_url="https://example.com/new")
        assert config.base_url == "https://example.com/new"

    def test_base_url_setter_updates_anova_base_url(self):
        """写入 base_url 时应同步更新 anova_base_url。"""
        config = CrawlerConfig()
        config.base_url = "https://example.com/legacy"
        assert config.anova_base_url == "https://example.com/legacy"

    def test_init_accepts_legacy_base_url(self):
        """初始化时传入 base_url 旧参数应生效。"""
        config = CrawlerConfig(base_url="https://example.com/init-legacy")
        assert config.anova_base_url == "https://example.com/init-legacy"
        assert config.base_url == "https://example.com/init-legacy"
