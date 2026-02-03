"""
APoU Exceptions Tests

Tests for custom exception classes in APoU/exceptions.py
"""
import pytest
from APoU.exceptions import (
    APoUError,
    NetworkError,
    APIError,
    ParseError,
    RateLimitError,
    EmptyPageError,
    MaxRetriesExceededError,
)


class TestAPoUError:
    """Test base APoUError class"""

    def test_basic_error(self):
        """Test creating basic error"""
        error = APoUError("Test message")
        
        assert error.message == "Test message"
        assert error.details == ""
        assert str(error) == "Test message"

    def test_error_with_details(self):
        """Test error with details"""
        error = APoUError("Main message", "Extra details")
        
        assert error.message == "Main message"
        assert error.details == "Extra details"
        assert str(error) == "Main message: Extra details"

    def test_error_is_exception(self):
        """Test that APoUError is an Exception"""
        error = APoUError("Test")
        
        assert isinstance(error, Exception)
        
        with pytest.raises(APoUError):
            raise error


class TestNetworkError:
    """Test NetworkError class"""

    def test_default_message(self):
        """Test default error message"""
        error = NetworkError()
        
        assert error.message == "网络请求失败"
        assert str(error) == "网络请求失败"

    def test_custom_message(self):
        """Test custom error message"""
        error = NetworkError("Connection timeout", "Host unreachable")
        
        assert error.message == "Connection timeout"
        assert error.details == "Host unreachable"

    def test_inheritance(self):
        """Test NetworkError inherits from APoUError"""
        error = NetworkError()
        
        assert isinstance(error, APoUError)


class TestAPIError:
    """Test APIError class"""

    def test_default_message(self):
        """Test default error message"""
        error = APIError()
        
        assert error.message == "API 返回错误"
        assert error.status_code == 0

    def test_with_status_code(self):
        """Test error with status code"""
        error = APIError("Server error", status_code=500)
        
        assert error.status_code == 500
        assert error.details == "状态码: 500"
        assert str(error) == "Server error: 状态码: 500"

    def test_with_response_text(self):
        """Test error with response text"""
        error = APIError("Bad request", status_code=400, response_text='{"error": "invalid"}')
        
        assert error.response_text == '{"error": "invalid"}'


class TestParseError:
    """Test ParseError class"""

    def test_default_message(self):
        """Test default error message"""
        error = ParseError()
        
        assert error.message == "数据解析失败"

    def test_with_raw_data(self):
        """Test error with raw data"""
        raw = "Invalid JSON {{{{"
        error = ParseError("JSON parse failed", raw_data=raw)
        
        assert error.raw_data == raw
        assert error.details == raw

    def test_raw_data_truncation(self):
        """Test that long raw data is truncated"""
        raw = "x" * 300
        error = ParseError("Parse failed", raw_data=raw)
        
        assert len(error.details) == 200


class TestRateLimitError:
    """Test RateLimitError class"""

    def test_default_message(self):
        """Test default error message"""
        error = RateLimitError()
        
        assert error.message == "请求过于频繁"
        assert error.retry_after == 0
        assert error.details == ""

    def test_with_retry_after(self):
        """Test error with retry_after"""
        error = RateLimitError("Too many requests", retry_after=60)
        
        assert error.retry_after == 60
        assert error.details == "建议 60 秒后重试"


class TestEmptyPageError:
    """Test EmptyPageError class"""

    def test_creation(self):
        """Test creating EmptyPageError"""
        error = EmptyPageError(page=5)
        
        assert error.page == 5
        assert error.message == "页面数据为空"
        assert error.details == "第 5 页"

    def test_custom_message(self):
        """Test custom error message"""
        error = EmptyPageError(page=10, message="No data found")
        
        assert error.message == "No data found"


class TestMaxRetriesExceededError:
    """Test MaxRetriesExceededError class"""

    def test_creation(self):
        """Test creating MaxRetriesExceededError"""
        error = MaxRetriesExceededError(page=3, max_retries=5)
        
        assert error.page == 3
        assert error.max_retries == 5
        assert error.message == "超过最大重试次数"
        assert error.details == "第 3 页，已重试 5 次"

    def test_str_representation(self):
        """Test string representation"""
        error = MaxRetriesExceededError(page=1, max_retries=3)
        
        assert str(error) == "超过最大重试次数: 第 1 页，已重试 3 次"


class TestExceptionHierarchy:
    """Test exception hierarchy"""

    def test_all_inherit_from_base(self):
        """Test all exceptions inherit from APoUError"""
        exceptions = [
            NetworkError(),
            APIError(),
            ParseError(),
            RateLimitError(),
            EmptyPageError(1),
            MaxRetriesExceededError(1, 1),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, APoUError)
            assert isinstance(exc, Exception)

    def test_can_catch_by_base_class(self):
        """Test catching exceptions by base class"""
        def raise_network():
            raise NetworkError("Test")
        
        with pytest.raises(APoUError):
            raise_network()
