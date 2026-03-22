"""
APoU 视图

用户发言列表爬取界面。
使用包装类模式（Wrapper Class Pattern）以兼容新版 Flet API。
"""
import flet as ft
from typing import Callable, Optional
from ..theme import Colors, Styles, create_card
from ..components.forms import UsernameInput, ConfigSlider, ActionButton
from ..components.progress import TaskProgressBar, LogViewer
from ..state import app_state, CrawlState
from ..workers.apou_worker import APoUWorker
from AutoCCF.config import config_manager


class APoUView:
    """APoU 视图"""
    
    def __init__(
        self,
        page: ft.Page,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        self._page = page
        self._on_complete = on_complete
        self._worker: Optional[APoUWorker] = None
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        # 加载配置
        try:
            config = config_manager.load()
            self._output_dir = str(config.get_database_path())
            page_delay = config.apou.page_delay
            max_retries = config.apou.max_retries
        except Exception:
            from pathlib import Path
            self._output_dir = str(Path("./database").resolve())
            page_delay = 2.0
            max_retries = 3
        
        # 用户名输入
        self._username_input = UsernameInput(
            label="贴吧用户名",
            hint_text="请输入要爬取的贴吧用户名",
            on_submit=lambda _: self._start_crawl(),
        )
        
        # 校验修复模式开关
        self._verify_switch = ft.Switch(
            label="校验修复模式（重新爬取已有数据）",
            value=False,
            active_color=Colors.PRIMARY,
        )
        
        # 配置滑块
        self._delay_slider = ConfigSlider(
            label="页间延迟",
            min_value=0.5,
            max_value=10.0,
            value=page_delay,
            step=0.5,
            unit="秒",
        )
        
        self._retries_slider = ConfigSlider(
            label="最大重试次数",
            min_value=1,
            max_value=10,
            value=float(max_retries),
            step=1,
            unit="次",
        )
        
        # 开始按钮
        self._start_button = ActionButton(
            text="开始爬取",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._start_crawl,
        )
        
        # 停止按钮
        self._stop_button = ActionButton(
            text="停止",
            icon=ft.Icons.STOP,
            on_click=self._stop_crawl,
            primary=False,
        )
        self._stop_button.visible = False
        
        # 进度条
        self._progress_bar = TaskProgressBar(
            current=0,
            total=0,
            label="等待开始...",
        )
        
        # 日志查看器
        self._log_viewer = LogViewer(
            max_lines=500,
            height=400,
        )
        
        # 状态文本
        self._status_text = ft.Text(
            "",
            size=14,
            color=Colors.TEXT_SECONDARY,
        )
        
        self._control = ft.Container(
            content=ft.Column(
                controls=[
                    # 页面标题
                    ft.Text(
                        "APoU - 用户发言列表",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "获取指定用户在贴吧的所有发言记录",
                        size=16,
                        color=Colors.TEXT_SECONDARY,
                    ),
                    
                    ft.Divider(height=24, color=Colors.DIVIDER),
                    
                    # 配置区域
                    create_card(
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "爬取配置",
                                    size=16,
                                    weight=ft.FontWeight.W_500,
                                    color=Colors.TEXT_PRIMARY,
                                ),
                                ft.Divider(height=1, color=Colors.DIVIDER),
                                self._username_input.control,
                                ft.Row(
                                    controls=[
                                        self._verify_switch,
                                        ft.Container(expand=True),
                                        ft.Text(
                                            f"输出目录: {self._output_dir}",
                                            size=12,
                                            color=Colors.TEXT_DISABLED,
                                        ),
                                    ],
                                ),
                                self._delay_slider.control,
                                self._retries_slider.control,
                                ft.Row(
                                    controls=[
                                        self._start_button.control,
                                        self._stop_button.control,
                                        self._status_text,
                                    ],
                                    spacing=16,
                                ),
                            ],
                            spacing=12,
                        )
                    ),
                    
                    ft.Container(height=16),
                    
                    # 进度区域
                    create_card(
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "爬取进度",
                                    size=16,
                                    weight=ft.FontWeight.W_500,
                                    color=Colors.TEXT_PRIMARY,
                                ),
                                ft.Divider(height=1, color=Colors.DIVIDER),
                                self._progress_bar.control,
                            ],
                            spacing=8,
                        )
                    ),
                    
                    ft.Container(height=16),
                    
                    # 日志区域
                    ft.Text(
                        "运行日志",
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    self._log_viewer.control,
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=Styles.PADDING_LG,
            expand=True,
        )
    
    def _start_crawl(self):
        """开始爬取"""
        username = self._username_input.value.strip()
        
        if not username:
            self._username_input.set_error("请输入用户名")
            return
        
        self._username_input.set_error(None)
        
        # 创建工作器
        self._worker = APoUWorker(
            page=self._page,
            on_log=self._on_log,
            on_complete=self._on_crawl_complete,
        )
        
        # 获取配置（APoU 数据存放在 apou/ 子目录）
        output_dir = f"{self._output_dir}/{username}/apou"
        incremental = not self._verify_switch.value
        page_delay = self._delay_slider.value
        max_retries = int(self._retries_slider.value)
        
        # 更新 UI 状态
        self._start_button.set_loading(True)
        self._stop_button.visible = True
        self._stop_button.control.update()
        self._log_viewer.clear()
        
        # 显示当前任务
        self._log_viewer.set_current_task(f"正在爬取用户: {username}")
        
        # 开始爬取
        self._worker.start(
            username=username,
            output_dir=output_dir,
            incremental=incremental,
            page_delay=page_delay,
            max_retries=max_retries,
        )
        
        # 监听状态变化
        app_state.add_listener(self._on_state_change)
    
    def _stop_crawl(self):
        """停止爬取"""
        if self._worker:
            self._worker.stop()
    
    def _on_log(self, message: str, level: str):
        """日志回调"""
        self._log_viewer.add_log(message, level)
    
    def _on_state_change(self):
        """状态变化回调"""
        progress = app_state.apou_progress
        if not progress:
            return
        
        # 更新进度条
        self._progress_bar.update_progress(
            current=progress.pages_done,
            total=progress.pages_done + 1,  # 未知总数，显示当前进度
            label=progress.message,
        )
        
        # 更新状态文本
        self._status_text.value = f"已获取 {progress.posts_collected} 条发言"
        self._status_text.update()
        
        # 更新当前任务显示
        if progress.current_title:
            self._log_viewer.set_current_task(f"正在处理: {progress.current_title}")
    
    def _on_crawl_complete(self, success: bool, message: str):
        """爬取完成回调"""
        # 移除监听器
        app_state.remove_listener(self._on_state_change)
        
        # 恢复 UI 状态
        self._start_button.set_loading(False)
        self._stop_button.visible = False
        self._stop_button.control.update()
        
        # 显示结果
        if success:
            self._status_text.value = message
            self._status_text.color = Colors.SUCCESS
        else:
            self._status_text.value = message
            self._status_text.color = Colors.ERROR
        self._status_text.update()
        
        # 通知完成
        if self._on_complete:
            self._on_complete()
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def restore_state(self):
        """恢复视图状态（从 app_state 读取当前爬取状态）"""
        progress = app_state.apou_progress
        is_running = app_state.is_apou_running
        
        if is_running and progress:
            # 正在爬取，恢复 UI 到运行状态
            self._start_button.set_loading(True)
            self._stop_button.visible = True
            try:
                self._stop_button.control.update()
            except Exception:
                pass
            
            # 恢复进度显示
            self._progress_bar.update_progress(
                current=progress.pages_done,
                total=progress.pages_done + 1,
                label=progress.message,
            )
            
            # 恢复状态文本
            self._status_text.value = f"已获取 {progress.posts_collected} 条发言"
            self._status_text.color = Colors.TEXT_SECONDARY
            try:
                self._status_text.update()
            except Exception:
                pass
            
            # 显示当前任务
            if hasattr(self._log_viewer, 'set_current_task'):
                self._log_viewer.set_current_task(f"正在爬取用户: {progress.username or '未知'}")
            
            # 重新绑定监听器（确保状态更新能够继续）
            # 先移除再添加，避免重复
            try:
                app_state.remove_listener(self._on_state_change)
            except Exception:
                pass
            app_state.add_listener(self._on_state_change)
        else:
            # 未在运行，确保 UI 处于空闲状态
            self._start_button.set_loading(False)
            self._stop_button.visible = False
            try:
                self._stop_button.control.update()
            except Exception:
                pass
            
            # 清除当前任务显示
            if hasattr(self._log_viewer, 'set_current_task'):
                self._log_viewer.set_current_task("")
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)
