"""
CLI 工具模块

提供美化的命令行输出功能，支持 Windows 和 Unix 终端。
"""
import os
import sys
import shutil
from typing import Optional, List, Tuple
from datetime import datetime


def supports_unicode() -> bool:
    """
    检测终端是否支持 Unicode

    Returns:
        是否支持 Unicode
    """
    if sys.platform == "win32":
        # Windows 检测 - 检查是否在支持 UTF-8 的终端
        try:
            import ctypes
            code_page = ctypes.windll.kernel32.GetConsoleOutputCP()
            # 65001 是 UTF-8
            return code_page == 65001
        except Exception:
            return False
    return True


# 检测 Unicode 支持
_UNICODE_SUPPORT = supports_unicode()


class Colors:
    """ANSI 颜色代码"""

    # 基础颜色
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    # 样式
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    # 重置
    RESET = "\033[0m"

    @classmethod
    def disable(cls) -> None:
        """禁用颜色（用于不支持 ANSI 的终端）"""
        for attr in dir(cls):
            if not attr.startswith("_") and attr.isupper():
                setattr(cls, attr, "")


def safe_str(text: str) -> str:
    """
    将字符串转换为当前终端可安全显示的格式
    
    处理 Windows GBK 编码无法显示特殊 Unicode 字符的问题。
    
    Args:
        text: 原始字符串
        
    Returns:
        可安全显示的字符串，不可编码的字符被替换为 '?'
    """
    try:
        # 尝试用当前终端编码编码字符串
        encoding = sys.stdout.encoding or 'utf-8'
        text.encode(encoding)
        return text
    except (UnicodeEncodeError, LookupError):
        # 如果失败，替换无法编码的字符
        encoding = sys.stdout.encoding or 'utf-8'
        return text.encode(encoding, errors='replace').decode(encoding, errors='replace')


def supports_color() -> bool:
    """
    检测终端是否支持颜色

    Returns:
        是否支持 ANSI 颜色
    """
    # Windows 需要特殊处理
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # 启用 Windows 终端的 ANSI 支持
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return os.environ.get("TERM") is not None

    # Unix 系统
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


# 初始化颜色支持
if not supports_color():
    Colors.disable()


class CLI:
    """
    CLI 界面工具类

    提供美化的命令行输出功能，包括：
    - 横幅和分隔线
    - 彩色消息输出
    - 进度条
    - 表格
    - 任务状态显示
    """

    # Unicode 图标
    _ICONS_UNICODE = {
        "success": "+",
        "error": "x",
        "warning": "!",
        "info": "i",
        "arrow": "->",
        "bullet": "*",
        "progress": ">",
        "processing": "...",
        "skipped": "-",
    }

    # ASCII 图标（作为后备）
    _ICONS_ASCII = {
        "success": "[OK]",
        "error": "[X]",
        "warning": "[!]",
        "info": "[i]",
        "arrow": "->",
        "bullet": "*",
        "progress": ">",
        "processing": "...",
        "skipped": "[-]",
    }

    # 边框字符 - Unicode
    _BORDER_UNICODE = {
        "h": "=",
        "v": "|",
        "tl": "+",
        "tr": "+",
        "bl": "+",
        "br": "+",
        "line": "-",
        "section": "|",
        "tree_mid": "+-",
        "tree_end": "+-",
        "bar_filled": "#",
        "bar_empty": ".",
    }

    # 边框字符 - ASCII
    _BORDER_ASCII = {
        "h": "=",
        "v": "|",
        "tl": "+",
        "tr": "+",
        "bl": "+",
        "br": "+",
        "line": "-",
        "section": "|",
        "tree_mid": "+-",
        "tree_end": "+-",
        "bar_filled": "#",
        "bar_empty": ".",
    }

    def __init__(self, app_name: str, version: str = "1.0.0"):
        """
        初始化 CLI

        Args:
            app_name: 应用名称
            version: 版本号
        """
        self.app_name = app_name
        self.version = version
        self.terminal_width = shutil.get_terminal_size().columns

        # 选择图标和边框字符集
        self._icons = self._ICONS_UNICODE if _UNICODE_SUPPORT else self._ICONS_ASCII
        self._border = self._BORDER_UNICODE if _UNICODE_SUPPORT else self._BORDER_ASCII

    # 图标属性
    @property
    def ICON_SUCCESS(self) -> str:
        """成功图标"""
        return self._icons["success"]

    @property
    def ICON_ERROR(self) -> str:
        """错误图标"""
        return self._icons["error"]

    @property
    def ICON_WARNING(self) -> str:
        """警告图标"""
        return self._icons["warning"]

    @property
    def ICON_INFO(self) -> str:
        """信息图标"""
        return self._icons["info"]

    @property
    def ICON_ARROW(self) -> str:
        """箭头图标"""
        return self._icons["arrow"]

    @property
    def ICON_BULLET(self) -> str:
        """项目符号"""
        return self._icons["bullet"]

    @property
    def ICON_PROGRESS(self) -> str:
        """进度图标"""
        return self._icons["progress"]

    def print_banner(self, subtitle: str = "") -> None:
        """
        打印应用横幅

        Args:
            subtitle: 副标题
        """
        width = min(60, self.terminal_width - 4)
        border = self._border["h"] * width

        print()
        print(
            f"{Colors.CYAN}{Colors.BOLD}{self._border['tl']}{border}"
            f"{self._border['tr']}{Colors.RESET}"
        )
        print(
            f"{Colors.CYAN}{Colors.BOLD}{self._border['v']}{Colors.RESET} "
            f"{self._center_text(self.app_name, width - 2)} "
            f"{Colors.CYAN}{Colors.BOLD}{self._border['v']}{Colors.RESET}"
        )
        if subtitle:
            print(
                f"{Colors.CYAN}{Colors.BOLD}{self._border['v']}{Colors.RESET} "
                f"{self._center_text(subtitle, width - 2, Colors.GRAY)} "
                f"{Colors.CYAN}{Colors.BOLD}{self._border['v']}{Colors.RESET}"
            )
        print(
            f"{Colors.CYAN}{Colors.BOLD}{self._border['v']}{Colors.RESET} "
            f"{self._center_text(f'v{self.version}', width - 2, Colors.DIM)} "
            f"{Colors.CYAN}{Colors.BOLD}{self._border['v']}{Colors.RESET}"
        )
        print(
            f"{Colors.CYAN}{Colors.BOLD}{self._border['bl']}{border}"
            f"{self._border['br']}{Colors.RESET}"
        )
        print()

    def _center_text(self, text: str, width: int, color: str = "") -> str:
        """
        居中文本

        Args:
            text: 要居中的文本
            width: 目标宽度
            color: 颜色代码

        Returns:
            居中后的文本
        """
        # 计算实际显示宽度（中文字符占2个宽度）
        display_width = sum(2 if ord(c) > 127 else 1 for c in text)
        padding = max(0, width - display_width)
        left_pad = padding // 2
        right_pad = padding - left_pad
        return (
            f"{' ' * left_pad}{color}{text}"
            f"{Colors.RESET if color else ''}{' ' * right_pad}"
        )

    def print_section(self, title: str) -> None:
        """
        打印分节标题

        Args:
            title: 节标题
        """
        print(
            f"\n{Colors.BOLD}{Colors.BLUE}{self._border['section']} "
            f"{title}{Colors.RESET}"
        )
        print(
            f"{Colors.DIM}"
            f"{self._border['line'] * min(40, self.terminal_width - 4)}"
            f"{Colors.RESET}"
        )

    def print_divider(self, char: str = "") -> None:
        """
        打印分隔线

        Args:
            char: 分隔字符（默认使用边框字符）
        """
        div_char = char if char else self._border["h"]
        print(
            f"{Colors.DIM}"
            f"{div_char * min(60, self.terminal_width - 4)}"
            f"{Colors.RESET}"
        )

    def print_config(self, items: List[Tuple[str, str]]) -> None:
        """
        打印配置项列表

        Args:
            items: 配置项列表 [(标签, 值), ...]
        """
        max_label_len = max(
            sum(2 if ord(c) > 127 else 1 for c in label) for label, _ in items
        )
        for label, value in items:
            label_width = sum(2 if ord(c) > 127 else 1 for c in label)
            padding = " " * (max_label_len - label_width)
            print(
                f"  {Colors.GRAY}{label}{padding}{Colors.RESET} : "
                f"{Colors.WHITE}{value}{Colors.RESET}"
            )

    def success(self, message: str) -> None:
        """
        打印成功消息

        Args:
            message: 消息内容
        """
        print(f"{Colors.GREEN}{self.ICON_SUCCESS} {message}{Colors.RESET}")

    def error(self, message: str) -> None:
        """
        打印错误消息

        Args:
            message: 消息内容
        """
        print(f"{Colors.RED}{self.ICON_ERROR} {message}{Colors.RESET}")

    def warning(self, message: str) -> None:
        """
        打印警告消息

        Args:
            message: 消息内容
        """
        print(f"{Colors.YELLOW}{self.ICON_WARNING} {message}{Colors.RESET}")

    def info(self, message: str) -> None:
        """
        打印信息消息

        Args:
            message: 消息内容
        """
        print(f"{Colors.BLUE}{self.ICON_INFO} {message}{Colors.RESET}")

    def progress(self, message: str) -> None:
        """
        打印进度消息

        Args:
            message: 消息内容
        """
        print(f"{Colors.CYAN}{self.ICON_PROGRESS} {message}{Colors.RESET}")

    def print_task(
        self,
        index: int,
        total: int,
        title: str,
        status: str = "processing",
        details: Optional[List[str]] = None,
    ) -> None:
        """
        打印任务状态

        Args:
            index: 当前索引
            total: 总数
            title: 任务标题
            status: 状态 (processing/success/failed/skipped)
            details: 详细信息列表
        """
        # 状态图标和颜色
        status_map = {
            "processing": (Colors.CYAN, self._icons["processing"]),
            "success": (Colors.GREEN, self.ICON_SUCCESS),
            "failed": (Colors.RED, self.ICON_ERROR),
            "skipped": (Colors.YELLOW, self._icons["skipped"]),
        }
        color, icon = status_map.get(status, (Colors.WHITE, "?"))

        # 进度
        if total > 0:
            progress_str = f"[{index:04d}/{total:04d}]"
        else:
            progress_str = f"[{index:04d}]"

        # 截断标题
        max_title_len = 40
        if len(title) > max_title_len:
            title = title[: max_title_len - 3] + "..."

        # 确保标题可以在当前终端安全显示
        title = safe_str(title)

        print(
            f"{Colors.DIM}{progress_str}{Colors.RESET} "
            f"{color}{icon}{Colors.RESET} {title}"
        )

        if details:
            for i, detail in enumerate(details):
                prefix = (
                    self._border["tree_end"]
                    if i == len(details) - 1
                    else self._border["tree_mid"]
                )
                print(f"           {Colors.DIM}{prefix}{Colors.RESET} {detail}")

    def print_progress_bar(
        self,
        current: int,
        total: int,
        width: int = 30,
        suffix: str = "",
    ) -> None:
        """
        打印进度条

        Args:
            current: 当前进度
            total: 总数
            width: 进度条宽度
            suffix: 后缀文本
        """
        if total == 0:
            percent = 0.0
        else:
            percent = current / total

        filled = int(width * percent)
        bar = (
            self._border["bar_filled"] * filled
            + self._border["bar_empty"] * (width - filled)
        )

        print(
            f"\r{Colors.CYAN}[{bar}]{Colors.RESET} {percent*100:5.1f}% {suffix}",
            end="",
            flush=True,
        )

    def print_stats_box(self, stats: List[Tuple[str, str, str]]) -> None:
        """
        打印统计信息框

        Args:
            stats: 统计项列表 [(标签, 值, 颜色), ...]
        """
        print()
        for label, value, color in stats:
            color_code = getattr(Colors, color.upper(), Colors.WHITE)
            print(
                f"  {Colors.GRAY}{label}:{Colors.RESET} "
                f"{color_code}{Colors.BOLD}{value}{Colors.RESET}"
            )

    def print_table(
        self,
        headers: List[str],
        rows: List[List[str]],
        colors: Optional[List[str]] = None,
    ) -> None:
        """
        打印简单表格

        Args:
            headers: 表头列表
            rows: 数据行列表
            colors: 每列的颜色
        """
        if not rows:
            return

        # 计算列宽
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(str(cell)))

        # 打印表头
        header_str = " | ".join(
            h.ljust(col_widths[i]) for i, h in enumerate(headers)
        )
        print(f"  {Colors.BOLD}{header_str}{Colors.RESET}")
        print(f"  {'-+-'.join('-' * w for w in col_widths)}")

        # 打印数据行
        for row in rows:
            cells = []
            for i, cell in enumerate(row):
                color = getattr(
                    Colors, (colors[i] if colors else "WHITE").upper(), Colors.WHITE
                )
                cells.append(f"{color}{str(cell).ljust(col_widths[i])}{Colors.RESET}")
            print(f"  {' | '.join(cells)}")

    def confirm(self, message: str, default: bool = True) -> bool:
        """
        确认提示

        Args:
            message: 提示消息
            default: 默认值

        Returns:
            用户选择
        """
        hint = "[Y/n]" if default else "[y/N]"
        try:
            answer = (
                input(f"{Colors.YELLOW}? {message} {hint}{Colors.RESET} ")
                .strip()
                .lower()
            )
            if not answer:
                return default
            return answer in ("y", "yes")
        except (EOFError, KeyboardInterrupt):
            print()
            return default

    def format_duration(self, seconds: float) -> str:
        """
        格式化时长

        Args:
            seconds: 秒数

        Returns:
            格式化后的时长字符串
        """
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"

    def format_number(self, num: int) -> str:
        """
        格式化数字（添加千位分隔符）

        Args:
            num: 数字

        Returns:
            格式化后的字符串
        """
        return f"{num:,}"

    def clear_line(self) -> None:
        """清除当前行"""
        print("\r" + " " * self.terminal_width + "\r", end="", flush=True)

    def print_footer(self, message: str = "") -> None:
        """
        打印页脚

        Args:
            message: 附加消息
        """
        print()
        self.print_divider()
        if message:
            print(f"{Colors.DIM}{message}{Colors.RESET}")
        print(
            f"{Colors.DIM}Completed: "
            f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}"
        )
        print()


__all__ = ["CLI", "Colors", "supports_color", "supports_unicode"]
