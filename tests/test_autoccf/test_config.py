"""
AutoCCF config tests.
"""
from AutoCCF.config import UnifiedConfig


class TestUnifiedConfig:
    """Test unified config defaults."""

    def test_default_apou_delay_is_one_second(self):
        """Test APoU default page delay is 1 second."""
        config = UnifiedConfig()

        assert config.apou.page_delay == 1.0

    def test_from_dict_uses_one_second_apou_delay_by_default(self):
        """Test missing apou.page_delay falls back to 1 second."""
        config = UnifiedConfig.from_dict({})

        assert config.apou.page_delay == 1.0

    def test_default_dopj_threads_is_two(self):
        """Test DoPJ default thread count uses safer default."""
        config = UnifiedConfig()

        assert config.dopj.threads == 2

    def test_from_dict_uses_two_dopj_threads_by_default(self):
        """Test missing dopj.threads falls back to 2."""
        config = UnifiedConfig.from_dict({})

        assert config.dopj.threads == 2
