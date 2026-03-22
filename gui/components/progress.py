"""
进度显示组件

包含进度条、状态卡片、日志查看器等。
使用 Flet 新版本的组件继承方式。
"""
import flet as ft
from typing import List, Optional
from dataclasses import field
from ..theme import Colors, Styles, create_card


def create_task_progress_bar(
    current: int = 0,
    total: int = 100,
    label: str = "",
    show_percentage: bool = True,
    color: str = Colors.PRIMARY,
) -> ft.Column:
    """创建任务进度条"""
    def get_percentage() -> float:
        if total <= 0:
            return 0.0
        return min(100.0, (current / total) * 100)
    
    def get_stats_text() -> str:
        if show_percentage:
            return f"{current}/{total} ({get_percentage():.1f}%)"
        return f"{current}/{total}"
    
    percentage = get_percentage()
    
    progress_bar = ft.ProgressBar(
        value=percentage / 100 if total > 0 else 0,
        color=color,
        bgcolor=Colors.SURFACE_VARIANT,
        height=8,
        border_radius=Styles.BORDER_RADIUS_SM,
    )
    
    label_text = ft.Text(
        label,
        size=14,
        color=Colors.TEXT_PRIMARY,
    )
    
    stats_text = ft.Text(
        get_stats_text(),
        size=12,
        color=Colors.TEXT_SECONDARY,
    )
    
    return ft.Column(
        controls=[
            ft.Row(
                controls=[
                    label_text,
                    ft.Container(expand=True),
                    stats_text,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            progress_bar,
        ],
        spacing=4,
        data={
            "progress_bar": progress_bar,
            "label_text": label_text,
            "stats_text": stats_text,
            "current": current,
            "total": total,
            "show_percentage": show_percentage,
        }
    )


class TaskProgressBar:
    """任务进度条组件包装类"""
    
    def __init__(
        self,
        current: int = 0,
        total: int = 100,
        label: str = "",
        show_percentage: bool = True,
        color: str = Colors.PRIMARY,
    ):
        self._current = current
        self._total = total
        self._label = label
        self._show_percentage = show_percentage
        self._color = color
        self._control: Optional[ft.Column] = None
        self._progress_bar: Optional[ft.ProgressBar] = None
        self._label_text: Optional[ft.Text] = None
        self._stats_text: Optional[ft.Text] = None
        self._build()
    
    def _build(self):
        percentage = self._get_percentage()
        
        self._progress_bar = ft.ProgressBar(
            value=percentage / 100 if self._total > 0 else 0,
            color=self._color,
            bgcolor=Colors.SURFACE_VARIANT,
            height=8,
            border_radius=Styles.BORDER_RADIUS_SM,
        )
        
        self._label_text = ft.Text(
            self._label,
            size=14,
            color=Colors.TEXT_PRIMARY,
        )
        
        self._stats_text = ft.Text(
            self._get_stats_text(),
            size=12,
            color=Colors.TEXT_SECONDARY,
        )
        
        self._control = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        self._label_text,
                        ft.Container(expand=True),
                        self._stats_text,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self._progress_bar,
            ],
            spacing=4,
        )
    
    def _get_percentage(self) -> float:
        if self._total <= 0:
            return 0.0
        return min(100.0, (self._current / self._total) * 100)
    
    def _get_stats_text(self) -> str:
        if self._show_percentage:
            return f"{self._current}/{self._total} ({self._get_percentage():.1f}%)"
        return f"{self._current}/{self._total}"
    
    def update_progress(self, current: int, total: Optional[int] = None, label: Optional[str] = None):
        """更新进度"""
        self._current = current
        if total is not None:
            self._total = total
        if label is not None:
            self._label = label
            if self._label_text:
                self._label_text.value = label
        
        percentage = self._get_percentage()
        if self._progress_bar:
            self._progress_bar.value = percentage / 100 if self._total > 0 else 0
        if self._stats_text:
            self._stats_text.value = self._get_stats_text()
        if self._control:
            self._control.update()
    
    @property
    def control(self) -> ft.Column:
        return self._control
    
    # 允许直接添加到页面
    def __getattr__(self, name):
        return getattr(self._control, name)


class CrawlStatusCard:
    """爬取状态卡片"""
    
    def __init__(
        self,
        title: str = "爬取状态",
        success: int = 0,
        failed: int = 0,
        pending: int = 0,
        skipped: int = 0,
    ):
        self._title = title
        self._success = success
        self._failed = failed
        self._pending = pending
        self._skipped = skipped
        self._control: Optional[ft.Card] = None
        self._success_text: Optional[ft.Container] = None
        self._failed_text: Optional[ft.Container] = None
        self._pending_text: Optional[ft.Container] = None
        self._skipped_text: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        self._success_text = self._create_stat_item("成功", self._success, Colors.SUCCESS)
        self._failed_text = self._create_stat_item("失败", self._failed, Colors.ERROR)
        self._pending_text = self._create_stat_item("等待", self._pending, Colors.TEXT_SECONDARY)
        self._skipped_text = self._create_stat_item("跳过", self._skipped, Colors.WARNING)
        
        self._control = create_card(
            ft.Column(
                controls=[
                    ft.Text(
                        self._title,
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Divider(height=1, color=Colors.DIVIDER),
                    ft.Row(
                        controls=[
                            self._success_text,
                            self._failed_text,
                            self._pending_text,
                            self._skipped_text,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    ),
                ],
                spacing=12,
            )
        )
    
    def _create_stat_item(self, label: str, value: int, color: str) -> ft.Container:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        str(value),
                        size=24,
                        weight=ft.FontWeight.BOLD,
                        color=color,
                    ),
                    ft.Text(
                        label,
                        size=12,
                        color=Colors.TEXT_SECONDARY,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=Styles.PADDING_SM,
        )
    
    def update_stats(
        self,
        success: Optional[int] = None,
        failed: Optional[int] = None,
        pending: Optional[int] = None,
        skipped: Optional[int] = None,
    ):
        """更新统计数据"""
        if success is not None:
            self._success = success
            if self._success_text:
                self._success_text.content.controls[0].value = str(success)
        if failed is not None:
            self._failed = failed
            if self._failed_text:
                self._failed_text.content.controls[0].value = str(failed)
        if pending is not None:
            self._pending = pending
            if self._pending_text:
                self._pending_text.content.controls[0].value = str(pending)
        if skipped is not None:
            self._skipped = skipped
            if self._skipped_text:
                self._skipped_text.content.controls[0].value = str(skipped)
        if self._control:
            self._control.update()
    
    @property
    def control(self) -> ft.Card:
        return self._control
    
    def __getattr__(self, name):
        return getattr(self._control, name)


class LogViewer:
    """日志查看器 - 深色终端风格"""
    
    def __init__(
        self,
        max_lines: int = 200,
        height: int = 300,
    ):
        self._max_lines = max_lines
        self._height = height
        self._logs: List[str] = []
        self._control: Optional[ft.Container] = None
        self._log_column: Optional[ft.Column] = None
        self._current_task_text: Optional[ft.Text] = None
        self._scroll_container: Optional[ft.Column] = None
        self._build()
    
    def _build(self):
        # 当前任务显示（固定在顶部）
        self._current_task_text = ft.Text(
            "",
            size=12,
            color=Colors.LOG_INFO,
            weight=ft.FontWeight.BOLD,
            font_family="Consolas",
        )
        
        # 日志列表（可滚动）
        self._log_column = ft.Column(
            controls=[],
            spacing=2,
            scroll=ft.ScrollMode.AUTO,
            auto_scroll=True,  # 自动滚动到底部
        )
        
        # 外层容器
        self._control = ft.Container(
            content=ft.Column(
                controls=[
                    # 当前任务区域
                    ft.Container(
                        content=self._current_task_text,
                        padding=ft.padding.only(bottom=8),
                        visible=False,  # 初始隐藏
                    ),
                    # 日志区域
                    ft.Container(
                        content=self._log_column,
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            height=self._height,
            bgcolor=Colors.LOG_BACKGROUND,  # 深色终端背景
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Styles.BORDER_RADIUS_MD,
            padding=Styles.PADDING_SM,
        )
    
    def set_current_task(self, message: str):
        """设置当前任务描述"""
        if self._current_task_text:
            if message:
                self._current_task_text.value = f"▶ {message}"
                # 显示当前任务区域
                if self._control and self._control.content:
                    self._control.content.controls[0].visible = True
            else:
                self._current_task_text.value = ""
                if self._control and self._control.content:
                    self._control.content.controls[0].visible = False
            if self._control:
                self._control.update()
    
    def add_log(self, message: str, level: str = "info"):
        """添加日志"""
        # 使用终端风格颜色
        color_map = {
            "info": Colors.LOG_TEXT,
            "success": Colors.LOG_SUCCESS,
            "warning": Colors.LOG_WARNING,
            "error": Colors.LOG_ERROR,
        }
        color = color_map.get(level, Colors.LOG_TEXT)
        
        # 添加时间戳前缀
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self._logs.append(formatted_message)
        
        # 限制最大行数
        if len(self._logs) > self._max_lines:
            self._logs = self._logs[-self._max_lines:]
            if self._log_column:
                self._log_column.controls = self._log_column.controls[-self._max_lines:]
        
        log_text = ft.Text(
            formatted_message,
            size=12,
            color=color,
            font_family="Consolas",
            selectable=True,  # 允许选择复制
        )
        if self._log_column:
            self._log_column.controls.append(log_text)
        if self._control:
            self._control.update()
    
    def clear(self):
        """清空日志"""
        self._logs.clear()
        if self._log_column:
            self._log_column.controls.clear()
        if self._current_task_text:
            self._current_task_text.value = ""
        if self._control:
            self._control.update()
    
    @property
    def control(self) -> ft.Container:
        return self._control
    
    def __getattr__(self, name):
        return getattr(self._control, name)


class AccountStatusCard:
    """账户状态卡片"""
    
    def __init__(
        self,
        name: str,
        is_banned: bool = False,
        fail_count: int = 0,
    ):
        self._name = name
        self._is_banned = is_banned
        self._fail_count = fail_count
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        status_color = Colors.ERROR if self._is_banned else Colors.SUCCESS
        status_text = "已禁用" if self._is_banned else "可用"
        status_icon = ft.Icons.CANCEL if self._is_banned else ft.Icons.CHECK_CIRCLE
        
        self._control = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        status_icon,
                        color=status_color,
                        size=20,
                    ),
                    ft.Text(
                        self._name,
                        size=14,
                        color=Colors.TEXT_PRIMARY,
                        weight=ft.FontWeight.W_500,
                    ),
                    ft.Container(expand=True),
                    ft.Text(
                        status_text,
                        size=12,
                        color=status_color,
                    ),
                    ft.Text(
                        f"失败: {self._fail_count}",
                        size=12,
                        color=Colors.TEXT_SECONDARY,
                    ),
                ],
                alignment=ft.MainAxisAlignment.START,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=Styles.PADDING_SM,
            bgcolor=Colors.SURFACE_VARIANT,
            border_radius=Styles.BORDER_RADIUS_SM,
        )
    
    def update_status(self, is_banned: bool, fail_count: int):
        """更新状态"""
        self._is_banned = is_banned
        self._fail_count = fail_count
        self._build()  # 重新构建
        if self._control:
            self._control.update()
    
    @property
    def control(self) -> ft.Container:
        return self._control
    
    def __getattr__(self, name):
        return getattr(self._control, name)
