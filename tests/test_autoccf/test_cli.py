"""
AutoCCF CLI Tests

Tests for CLI utilities from AutoCCF/cli.py
"""
import pytest
from AutoCCF.cli import Colors, CLI, supports_color, supports_unicode


class TestColors:
    """Test Colors class"""

    def test_basic_colors_exist(self, color_codes):
        """Test that basic color codes exist"""
        assert Colors.RESET == color_codes["RESET"]
        assert Colors.RED == color_codes["RED"]
        assert Colors.GREEN == color_codes["GREEN"]
        assert Colors.YELLOW == color_codes["YELLOW"]
        assert Colors.BLUE == color_codes["BLUE"]
        assert Colors.MAGENTA == color_codes["MAGENTA"]
        assert Colors.CYAN == color_codes["CYAN"]

    def test_style_codes_exist(self):
        """Test that style codes exist"""
        assert Colors.BOLD == "\033[1m"
        assert Colors.DIM == "\033[2m"
        assert Colors.UNDERLINE == "\033[4m"

    def test_white_and_gray(self):
        """Test white and gray colors"""
        assert Colors.WHITE == "\033[97m"
        assert Colors.GRAY == "\033[90m"

    def test_disable_clears_colors(self):
        """Test that disable() clears all color codes"""
        # Save original values
        original_reset = Colors.RESET
        original_red = Colors.RED
        
        # Disable
        Colors.disable()
        
        assert Colors.RED == ""
        assert Colors.RESET == ""
        
        # Restore for other tests
        Colors.RED = original_red
        Colors.RESET = original_reset


class TestCLI:
    """Test CLI class"""

    def test_cli_creation(self):
        """Test creating CLI instance"""
        cli = CLI("Test App", "1.0.0")
        
        assert cli.app_name == "Test App"
        assert cli.version == "1.0.0"

    def test_cli_default_version(self):
        """Test CLI with default version"""
        cli = CLI("App")
        
        assert cli.app_name == "App"
        assert cli.version == "1.0.0"  # Default version is "1.0.0"

    def test_format_duration_seconds(self):
        """Test formatting duration in seconds"""
        cli = CLI("Test")
        
        result = cli.format_duration(45)
        
        # Format uses float, so "45.0s"
        assert "45" in result and "s" in result

    def test_format_duration_minutes(self):
        """Test formatting duration in minutes"""
        cli = CLI("Test")
        
        result = cli.format_duration(125)  # 2 min 5 sec
        
        assert "2m" in result

    def test_format_duration_hours(self):
        """Test formatting duration in hours"""
        cli = CLI("Test")
        
        result = cli.format_duration(3665)  # 1 hour 1 min 5 sec
        
        assert "1h" in result and "1m" in result

    def test_format_duration_zero(self):
        """Test formatting zero duration"""
        cli = CLI("Test")
        
        result = cli.format_duration(0)
        
        assert "0" in result and "s" in result

    def test_success_message(self, capsys):
        """Test success message output"""
        cli = CLI("Test")
        
        cli.success("Operation completed")
        
        captured = capsys.readouterr()
        assert "Operation completed" in captured.out
        # Should contain green color or checkmark
        assert Colors.GREEN in captured.out or "✓" in captured.out or "+" in captured.out

    def test_error_message(self, capsys):
        """Test error message output"""
        cli = CLI("Test")
        
        cli.error("Something failed")
        
        captured = capsys.readouterr()
        assert "Something failed" in captured.out
        # Should contain red color
        assert Colors.RED in captured.out or "x" in captured.out

    def test_warning_message(self, capsys):
        """Test warning message output"""
        cli = CLI("Test")
        
        cli.warning("Be careful")
        
        captured = capsys.readouterr()
        assert "Be careful" in captured.out
        # Should contain yellow color
        assert Colors.YELLOW in captured.out or "!" in captured.out

    def test_info_message(self, capsys):
        """Test info message output"""
        cli = CLI("Test")
        
        cli.info("Information here")
        
        captured = capsys.readouterr()
        assert "Information here" in captured.out

    def test_print_banner(self, capsys):
        """Test banner printing"""
        cli = CLI("TestApp", "2.0.0")
        
        cli.print_banner("Welcome")
        
        captured = capsys.readouterr()
        output = captured.out
        
        # Should contain app info
        assert "TestApp" in output or "Welcome" in output

    def test_print_section(self, capsys):
        """Test section printing"""
        cli = CLI("Test")
        
        cli.print_section("Section Title")
        
        captured = capsys.readouterr()
        assert "Section Title" in captured.out

    def test_print_config(self, capsys):
        """Test config printing"""
        cli = CLI("Test")
        
        cli.print_config([
            ("Key1", "Value1"),
            ("Key2", "Value2"),
        ])
        
        captured = capsys.readouterr()
        assert "Key1" in captured.out
        assert "Value1" in captured.out
        assert "Key2" in captured.out
        assert "Value2" in captured.out


class TestSupportFunctions:
    """Test support detection functions"""

    def test_supports_color_returns_bool(self):
        """Test that supports_color returns boolean"""
        result = supports_color()
        
        assert isinstance(result, bool)

    def test_supports_unicode_returns_bool(self):
        """Test that supports_unicode returns boolean"""
        result = supports_unicode()
        
        assert isinstance(result, bool)


class TestCLIProgressBar:
    """Test CLI progress bar functionality"""

    def test_print_progress_bar(self, capsys):
        """Test printing progress bar"""
        cli = CLI("Test")
        
        cli.print_progress_bar(50, 100)
        
        captured = capsys.readouterr()
        # Should show 50%
        assert "50" in captured.out or "%" in captured.out

    def test_print_progress_bar_complete(self, capsys):
        """Test printing complete progress bar"""
        cli = CLI("Test")
        
        cli.print_progress_bar(100, 100)
        
        captured = capsys.readouterr()
        assert "100" in captured.out

    def test_print_progress_bar_with_suffix(self, capsys):
        """Test progress bar with suffix"""
        cli = CLI("Test")
        
        cli.print_progress_bar(25, 100, suffix="Processing...")
        
        captured = capsys.readouterr()
        assert "Processing" in captured.out


class TestCLITable:
    """Test CLI table functionality"""

    def test_print_table(self, capsys):
        """Test printing a table"""
        cli = CLI("Test")
        
        headers = ["Name", "Value"]
        rows = [
            ["Item 1", "100"],
            ["Item 2", "200"],
        ]
        
        cli.print_table(headers, rows)
        
        captured = capsys.readouterr()
        assert "Name" in captured.out
        assert "Value" in captured.out
        assert "Item 1" in captured.out
        assert "Item 2" in captured.out
        assert "100" in captured.out
        assert "200" in captured.out
