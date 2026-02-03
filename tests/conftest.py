"""
Shared pytest fixtures for AutoCCF test suite.
"""
import sys
from pathlib import Path

import pytest

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================================
# DoPJ Fixtures
# ============================================================================

@pytest.fixture
def sample_tieba_urls():
    """Sample Tieba URLs for testing URL parser."""
    return [
        ("https://tieba.baidu.com/p/123456789", (123456789, None)),
        ("https://tieba.baidu.com/p/123?pid=456", (123, 456)),
        ("http://tieba.baidu.com/p/999", (999, None)),
        ("tieba.baidu.com/p/111?pid=222#post_content_333", (111, 222)),
    ]


@pytest.fixture
def sample_accounts():
    """Sample account configurations for testing."""
    return [
        {"name": "account1", "bduss": "bduss_value_1"},
        {"name": "account2", "bduss": "bduss_value_2"},
        {"name": "account3", "bduss": "bduss_value_3"},
    ]


@pytest.fixture
def temp_db_path(tmp_path):
    """Temporary database path for testing storage."""
    return tmp_path / "test_content.db"


# ============================================================================
# APoU Fixtures
# ============================================================================

@pytest.fixture
def sample_post_data():
    """Sample post data for testing APoU parser."""
    return {
        "thread_id": 123456789,
        "post_id": 987654321,
        "forum_name": "test_forum",
        "title": "Test Thread Title",
        "content": "This is test content",
        "create_time": 1700000000,
        "reply_num": 10,
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "user_id": 12345,
        "user_name": "test_user",
        "portrait": "portrait_hash",
    }


# ============================================================================
# AutoCCF Core Fixtures
# ============================================================================

@pytest.fixture
def color_codes():
    """Expected color codes for CLI testing."""
    return {
        "RESET": "\033[0m",
        "RED": "\033[91m",
        "GREEN": "\033[92m",
        "YELLOW": "\033[93m",
        "BLUE": "\033[94m",
        "MAGENTA": "\033[95m",
        "CYAN": "\033[96m",
    }
