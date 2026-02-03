"""
DoPJ Account Manager Tests

Tests for AccountManager from DoPJ/cli.py
"""
import time
import pytest
from unittest.mock import patch
from DoPJ.cli import AccountManager


class TestAccountManager:
    """Test AccountManager class"""

    def test_init(self, sample_accounts):
        """Test AccountManager initialization"""
        am = AccountManager(sample_accounts)
        
        assert len(am.accounts) == 3
        assert am.min_interval == 2.0
        assert am.max_fails == 5

    def test_init_with_custom_settings(self, sample_accounts):
        """Test AccountManager with custom settings"""
        am = AccountManager(
            sample_accounts,
            min_interval=1.0,
            max_fails=3,
        )
        
        assert am.min_interval == 1.0
        assert am.max_fails == 3

    def test_get_account_returns_dict(self, sample_accounts):
        """Test get_account returns proper account dict"""
        am = AccountManager(sample_accounts, min_interval=0)
        
        account = am.get_account()
        
        assert account is not None
        assert "index" in account
        assert "name" in account
        assert "bduss" in account
        assert account["name"] == "account1"
        assert account["bduss"] == "bduss_value_1"

    def test_get_account_rotates(self, sample_accounts):
        """Test that get_account rotates through accounts"""
        am = AccountManager(sample_accounts, min_interval=0)
        
        acc1 = am.get_account()
        acc2 = am.get_account()
        acc3 = am.get_account()
        acc4 = am.get_account()  # Should wrap around
        
        assert acc1["name"] == "account1"
        assert acc2["name"] == "account2"
        assert acc3["name"] == "account3"
        assert acc4["name"] == "account1"

    def test_get_account_skips_banned(self, sample_accounts):
        """Test that get_account skips banned accounts"""
        am = AccountManager(sample_accounts, min_interval=0)
        
        # Ban first account
        am._banned[0] = True
        
        acc = am.get_account()
        assert acc["name"] == "account2"

    def test_get_account_returns_none_when_all_banned(self, sample_accounts):
        """Test get_account returns None when all accounts banned"""
        am = AccountManager(sample_accounts, min_interval=0)
        
        # Ban all accounts
        for i in range(len(sample_accounts)):
            am._banned[i] = True
        
        acc = am.get_account()
        assert acc is None

    def test_report_success_decreases_fail_count(self, sample_accounts):
        """Test that report_success decreases fail count"""
        am = AccountManager(sample_accounts, min_interval=0)
        
        acc = am.get_account()
        am._fail_counts[acc["index"]] = 3
        
        am.report_success(acc)
        
        assert am._fail_counts[acc["index"]] == 2

    def test_report_success_doesnt_go_negative(self, sample_accounts):
        """Test that fail count doesn't go negative"""
        am = AccountManager(sample_accounts, min_interval=0)
        
        acc = am.get_account()
        am._fail_counts[acc["index"]] = 0
        
        am.report_success(acc)
        
        assert am._fail_counts[acc["index"]] == 0

    def test_report_failure_increases_fail_count(self, sample_accounts):
        """Test that report_failure increases fail count"""
        am = AccountManager(sample_accounts, min_interval=0)
        
        acc = am.get_account()
        
        am.report_failure(acc)
        
        assert am._fail_counts[acc["index"]] == 1

    def test_report_failure_bans_after_max_fails(self, sample_accounts):
        """Test that account is banned after max failures"""
        am = AccountManager(sample_accounts, min_interval=0, max_fails=3)
        
        acc = am.get_account()
        am._fail_counts[acc["index"]] = 2  # One more to trigger ban
        
        am.report_failure(acc)
        
        assert am._banned[acc["index"]] is True

    def test_report_failure_with_auth_error_bans_immediately(self, sample_accounts):
        """Test that auth error bans account immediately"""
        am = AccountManager(sample_accounts, min_interval=0)
        
        acc = am.get_account()
        
        am.report_failure(acc, is_auth_error=True)
        
        assert am._banned[acc["index"]] is True
        assert am._fail_counts[acc["index"]] == 1

    def test_get_status(self, sample_accounts):
        """Test get_status returns correct information"""
        am = AccountManager(sample_accounts, min_interval=0)
        
        # Ban one account
        am._banned[1] = True
        am._fail_counts[0] = 2
        
        status = am.get_status()
        
        assert status["total"] == 3
        assert status["available"] == 2
        assert len(status["accounts"]) == 3
        
        assert status["accounts"][0]["name"] == "account1"
        assert status["accounts"][0]["is_banned"] is False
        assert status["accounts"][0]["fail_count"] == 2
        
        assert status["accounts"][1]["is_banned"] is True

    @patch("time.sleep")
    def test_interval_enforcement(self, mock_sleep, sample_accounts):
        """Test that min_interval is enforced between uses"""
        am = AccountManager(sample_accounts, min_interval=2.0)
        
        # First call - no sleep needed
        am._last_use[0] = 0
        with patch("time.time", return_value=0.5):
            am.get_account()
        
        # Should have slept
        mock_sleep.assert_called()


class TestAccountManagerEdgeCases:
    """Test edge cases for AccountManager"""

    def test_single_account(self):
        """Test with single account"""
        am = AccountManager(
            [{"name": "only", "bduss": "single"}],
            min_interval=0,
        )
        
        acc1 = am.get_account()
        acc2 = am.get_account()
        
        assert acc1["name"] == "only"
        assert acc2["name"] == "only"

    def test_account_without_name(self):
        """Test account without name uses default"""
        am = AccountManager(
            [{"bduss": "test"}],
            min_interval=0,
        )
        
        acc = am.get_account()
        assert acc["name"] == "账户 1"

    def test_empty_accounts_list(self):
        """Test with empty accounts list"""
        am = AccountManager([], min_interval=0)
        
        acc = am.get_account()
        assert acc is None
