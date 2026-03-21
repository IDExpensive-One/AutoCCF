"""
APoU Exceptions Tests

Tests for custom exception classes in APoU/exceptions.py
"""
import pytest
from APoU.exceptions import (
    APoUError,
    AuthError,
    NetworkError,
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


class TestAuthError:
    """Test AuthError class"""

    def test_default_message(self):
        """Test default error message"""
        error = AuthError()
        
        assert error.message == "认证失败"
        assert str(error) == "认证失败"

    def test_custom_message(self):
        """Test custom error message"""
        error = AuthError("登录失效")
        
        assert error.message == "登录失效"
        assert error.details == ""
        assert str(error) == "登录失效"

    def test_inheritance(self):
        """Test AuthError inherits from APoUError"""
        error = AuthError()
        
        assert isinstance(error, APoUError)


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
            AuthError(),
            NetworkError(),
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
