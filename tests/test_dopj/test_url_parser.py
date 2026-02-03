"""
DoPJ URL Parser Tests

Tests for DoPJ/utils/url_parser.py
"""
import pytest
from DoPJ.utils.url_parser import parse_tieba_url, extract_tid_from_url, extract_pid_from_url


class TestParseTiebaUrl:
    """Test parse_tieba_url function"""

    def test_parse_full_url_with_pid(self):
        """Test parsing URL with pid parameter"""
        url = "https://tieba.baidu.com/p/5052759887?pid=105910715857#105910715857"
        result = parse_tieba_url(url)
        assert result == (5052759887, 105910715857)

    def test_parse_url_without_pid(self):
        """Test parsing URL without pid (main post)"""
        url = "https://tieba.baidu.com/p/8173224373"
        result = parse_tieba_url(url)
        assert result == (8173224373, None)

    def test_parse_url_with_http(self):
        """Test parsing URL with http protocol"""
        url = "http://tieba.baidu.com/p/123456789"
        result = parse_tieba_url(url)
        assert result == (123456789, None)

    def test_parse_url_without_protocol(self):
        """Test parsing URL without protocol"""
        url = "tieba.baidu.com/p/999?pid=888"
        result = parse_tieba_url(url)
        assert result == (999, 888)

    def test_parse_url_with_fragment(self):
        """Test parsing URL with fragment identifier"""
        url = "https://tieba.baidu.com/p/111?pid=222#post_content_333"
        result = parse_tieba_url(url)
        assert result == (111, 222)

    def test_parse_url_pid_with_ampersand(self):
        """Test parsing URL with pid using & instead of ?"""
        url = "https://tieba.baidu.com/p/100?other=param&pid=200"
        result = parse_tieba_url(url)
        assert result == (100, 200)

    def test_parse_invalid_url_returns_none(self):
        """Test that invalid URL returns None"""
        url = "https://example.com/page/123"
        result = parse_tieba_url(url)
        assert result is None

    def test_parse_empty_url_returns_none(self):
        """Test that empty URL returns None"""
        result = parse_tieba_url("")
        assert result is None

    def test_parse_url_without_tid_returns_none(self):
        """Test URL without /p/ pattern returns None"""
        url = "https://tieba.baidu.com/f?kw=test"
        result = parse_tieba_url(url)
        assert result is None


class TestExtractTidFromUrl:
    """Test extract_tid_from_url function"""

    def test_extract_tid_success(self):
        """Test extracting tid from valid URL"""
        url = "https://tieba.baidu.com/p/123456?pid=789"
        result = extract_tid_from_url(url)
        assert result == 123456

    def test_extract_tid_from_invalid_url(self):
        """Test extracting tid from invalid URL returns None"""
        url = "https://example.com/page"
        result = extract_tid_from_url(url)
        assert result is None


class TestExtractPidFromUrl:
    """Test extract_pid_from_url function"""

    def test_extract_pid_success(self):
        """Test extracting pid from valid URL"""
        url = "https://tieba.baidu.com/p/123?pid=456"
        result = extract_pid_from_url(url)
        assert result == 456

    def test_extract_pid_when_missing(self):
        """Test extracting pid when not present returns None"""
        url = "https://tieba.baidu.com/p/123"
        result = extract_pid_from_url(url)
        assert result is None

    def test_extract_pid_from_invalid_url(self):
        """Test extracting pid from invalid URL returns None"""
        url = "https://example.com/page"
        result = extract_pid_from_url(url)
        assert result is None
