"""
GUI 主题配置

Material Design 亮色主题，针对中文优化。
"""
import flet as ft
from typing import Dict, Any
import platform


# 颜色常量 - Dark Mode
class Colors:
    """应用颜色常量（暗色模式）"""
    # 主色调
    PRIMARY = "#64B5F6"  # Blue 300
    PRIMARY_DARK = "#42A5F5"
    PRIMARY_LIGHT = "#90CAF9"

    # 强调色
    ACCENT = "#4DD0E1"  # Cyan 300

    # 背景色
    BACKGROUND = "#121212"
    SURFACE = "#1E1E1E"
    SURFACE_VARIANT = "#2D2D2D"
    CARD = "#252525"

    # 文字色
    TEXT_PRIMARY = "#E0E0E0"
    TEXT_SECONDARY = "#A0A0A0"
    TEXT_DISABLED = "#606060"

    # 状态色
    SUCCESS = "#66BB6A"  # Green 400
    WARNING = "#FFA726"  # Orange 400
    ERROR = "#EF5350"    # Red 400
    INFO = "#42A5F5"     # Blue 400

    # 边框
    BORDER = "#404040"
    DIVIDER = "#333333"

    # 日志终端风格
    LOG_BACKGROUND = "#0D0D0D"
    LOG_TEXT = "#D4D4D4"
    LOG_SUCCESS = "#4EC9B0"
    LOG_WARNING = "#DCDCAA"
    LOG_ERROR = "#F14C4C"
    LOG_INFO = "#9CDCFE"

    # 运行状态指示器
    RUNNING_INDICATOR = "#4CAF50"


def get_system_font() -> str:
    """获取系统中文字体"""
    system = platform.system()
    if system == "Windows":
        return "Microsoft YaHei"
    elif system == "Darwin":  # macOS
        return "PingFang SC"
    else:  # Linux
        return "Noto Sans CJK SC"


def create_theme() -> ft.Theme:
    """创建应用主题（暗色模式）"""
    return ft.Theme(
        color_scheme_seed=Colors.PRIMARY,
        color_scheme=ft.ColorScheme(
            primary=Colors.PRIMARY,
            secondary=Colors.ACCENT,
            surface=Colors.SURFACE,
            surface_container=Colors.SURFACE_VARIANT,
            surface_container_highest=Colors.CARD,
            error=Colors.ERROR,
            on_primary="#000000",
            on_secondary="#000000",
            on_surface=Colors.TEXT_PRIMARY,
            on_error="#000000",
            outline=Colors.BORDER,
        ),
        text_theme=ft.TextTheme(
            body_large=ft.TextStyle(size=16),
            body_medium=ft.TextStyle(size=14),
            body_small=ft.TextStyle(size=12),
            title_large=ft.TextStyle(size=24, weight=ft.FontWeight.BOLD),
            title_medium=ft.TextStyle(size=20, weight=ft.FontWeight.W_500),
            title_small=ft.TextStyle(size=16, weight=ft.FontWeight.W_500),
        ),
    )


def configure_page(page: ft.Page) -> None:
    """配置页面样式"""
    # 基本设置
    page.title = "AutoCCF - 百度贴吧数据存档工具"
    page.theme_mode = ft.ThemeMode.DARK
    page.theme = create_theme()
    page.bgcolor = Colors.BACKGROUND
    page.padding = 0
    
    # 窗口设置
    page.window.width = 1200
    page.window.height = 800
    page.window.min_width = 900
    page.window.min_height = 600
    # Note: window.center() is async in new Flet, skip it for now
    
    # 字体设置
    page.fonts = {
        "default": get_system_font(),
    }


# 通用样式
class Styles:
    """通用样式常量"""
    # 圆角
    BORDER_RADIUS_SM = 4
    BORDER_RADIUS_MD = 8
    BORDER_RADIUS_LG = 12
    
    # 间距
    PADDING_SM = 8
    PADDING_MD = 16
    PADDING_LG = 24
    
    # 阴影
    ELEVATION_LOW = 1
    ELEVATION_MED = 2
    ELEVATION_HIGH = 4


def create_card(content: ft.Control, **kwargs) -> ft.Card:
    """创建标准卡片"""
    return ft.Card(
        content=ft.Container(
            content=content,
            padding=Styles.PADDING_MD,
        ),
        elevation=Styles.ELEVATION_LOW,
        **kwargs,
    )


def create_status_badge(
    text: str,
    status: str = "info",  # success, warning, error, info
) -> ft.Container:
    """创建状态徽章"""
    color_map = {
        "success": Colors.SUCCESS,
        "warning": Colors.WARNING,
        "error": Colors.ERROR,
        "info": Colors.INFO,
    }
    bg_color = color_map.get(status, Colors.INFO)
    
    return ft.Container(
        content=ft.Text(
            text,
            size=12,
            color="#FFFFFF",
            weight=ft.FontWeight.W_500,
        ),
        bgcolor=bg_color,
        padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=Styles.BORDER_RADIUS_SM,
    )
