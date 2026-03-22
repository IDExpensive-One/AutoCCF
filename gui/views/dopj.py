"""
DoPJ 视图

帖子详情爬取界面。
使用包装类模式（Wrapper Class Pattern）以兼容新版 Flet API。
"""
import flet as ft
from typing import Callable, Optional, List, Dict, Any
from ..theme import Colors, Styles, create_card
from ..components.forms import ActionButton
from ..components.progress import TaskProgressBar, CrawlStatusCard, LogViewer, AccountStatusCard
from ..state import app_state, CrawlState
from ..workers.dopj_worker import DoPJWorker
from AutoCCF.config import config_manager


class UserSelector:
    """用户选择器"""
    
    def __init__(
        self,
        on_select: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        self._on_select = on_select
        self._users: List[Dict[str, Any]] = []
        self._selected_user: Optional[Dict[str, Any]] = None
        self._control: Optional[ft.Column] = None
        self._build()
    
    def _build(self):
        self._load_users()
        
        self._dropdown = ft.Dropdown(
            label="选择用户",
            options=self._build_options(),
            on_select=self._on_dropdown_select,
        )
        
        self._info_text = ft.Text(
            "",
            size=12,
            color=Colors.TEXT_SECONDARY,
        )
        
        self._control = ft.Column(
            controls=[
                self._dropdown,
                self._info_text,
            ],
            spacing=4,
        )
    
    def _load_users(self):
        """加载用户列表"""
        try:
            config_manager.load()
            self._users = config_manager.find_apou_outputs()
        except Exception:
            self._users = []
    
    def _build_options(self) -> List[ft.dropdown.Option]:
        """构建下拉选项"""
        options = []
        for user in self._users:
            username = user.get("username", "未知")
            posts_count = user.get("posts_count", 0)
            has_index = user.get("has_index", False)
            
            status = "已完成" if has_index else "待爬取"
            label = f"{username} ({posts_count} 条发言, {status})"
            
            options.append(ft.dropdown.Option(
                key=username,
                text=label,
            ))
        
        if not options:
            options.append(ft.dropdown.Option(
                key="",
                text="暂无可用用户，请先使用 APoU 获取发言列表",
            ))
        
        return options
    
    def _on_dropdown_select(self, e):
        """选择变化"""
        username = e.control.value
        
        # 查找用户信息
        self._selected_user = None
        for user in self._users:
            if user.get("username") == username:
                self._selected_user = user
                break
        
        if self._selected_user:
            self._info_text.value = f"文件: {self._selected_user.get('path', '')}"
            self._info_text.update()
        
        if self._on_select and self._selected_user:
            self._on_select(self._selected_user)
    
    def refresh(self):
        """刷新列表"""
        self._load_users()
        self._dropdown.options = self._build_options()
        self._control.update()
    
    @property
    def selected_user(self) -> Optional[Dict[str, Any]]:
        return self._selected_user
    
    @property
    def control(self) -> ft.Column:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)


class DoPJView:
    """DoPJ 视图"""
    
    def __init__(
        self,
        page: ft.Page,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        self._page = page
        self._on_complete = on_complete
        self._worker: Optional[DoPJWorker] = None
        self._selected_user: Optional[Dict[str, Any]] = None
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        # 加载配置
        try:
            config = config_manager.load()
            self._output_dir = str(config.get_database_path())
            self._accounts = [
                {"name": acc.name, "bduss": acc.bduss}
                for acc in config.accounts
            ]
            threads = config.dopj.threads
            max_retries = config.dopj.max_retries
            min_interval = config.dopj.min_interval
            has_accounts = config.has_valid_accounts()
        except Exception:
            self._output_dir = "./database"
            self._accounts = []
            threads = 3
            max_retries = 3
            min_interval = 2.0
            has_accounts = False
        
        # 用户选择器
        self._user_selector = UserSelector(
            on_select=self._on_user_select,
        )
        
        # 校验修复模式开关
        self._verify_switch = ft.Switch(
            label="校验修复模式（重新爬取数据不完整的帖子）",
            value=False,
            active_color=Colors.PRIMARY,
        )
        
        # 线程数滑块
        self._threads_slider = ft.Slider(
            min=1,
            max=10,
            value=threads,
            divisions=9,
            label="{value}",
            active_color=Colors.PRIMARY,
        )
        
        # 开始按钮
        self._start_button = ActionButton(
            text="开始爬取",
            icon=ft.Icons.PLAY_ARROW,
            on_click=self._start_crawl,
            disabled=not has_accounts,
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
        
        # 状态卡片
        self._status_card = CrawlStatusCard(
            title="爬取状态",
        )
        
        # 日志查看器
        self._log_viewer = LogViewer(
            max_lines=500,
            height=400,
        )
        
        # 状态文本
        self._status_text = ft.Text(
            "" if has_accounts else "请先在设置中配置账户 BDUSS",
            size=14,
            color=Colors.TEXT_SECONDARY if has_accounts else Colors.WARNING,
        )
        
        # 账户状态区域
        self._accounts_column = ft.Column(
            controls=self._build_account_status(),
            spacing=4,
        )
        
        self._control = ft.Container(
            content=ft.Column(
                controls=[
                    # 页面标题
                    ft.Text(
                        "DoPJ - 帖子详情",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "获取发言列表中每个帖子的完整内容",
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
                                self._user_selector.control,
                                self._verify_switch,
                                ft.Row(
                                    controls=[
                                        ft.Text("并发线程数:", color=Colors.TEXT_SECONDARY),
                                        self._threads_slider,
                                    ],
                                    expand=True,
                                ),
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
                    
                    # 账户状态
                    create_card(
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "账户状态",
                                    size=16,
                                    weight=ft.FontWeight.W_500,
                                    color=Colors.TEXT_PRIMARY,
                                ),
                                ft.Divider(height=1, color=Colors.DIVIDER),
                                self._accounts_column,
                            ],
                            spacing=8,
                        )
                    ),
                    
                    ft.Container(height=16),
                    
                    # 进度区域
                    ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "爬取进度",
                                            size=16,
                                            weight=ft.FontWeight.W_500,
                                            color=Colors.TEXT_PRIMARY,
                                        ),
                                        self._progress_bar.control,
                                    ],
                                    spacing=8,
                                ),
                                expand=True,
                            ),
                            self._status_card.control,
                        ],
                        spacing=16,
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
    
    def _build_account_status(self) -> List[ft.Control]:
        """构建账户状态列表"""
        if not self._accounts:
            return [
                ft.Text(
                    "暂无账户，请在设置中添加",
                    color=Colors.TEXT_DISABLED,
                )
            ]
        
        items = []
        for acc in self._accounts:
            items.append(
                AccountStatusCard(
                    name=acc.get("name", "未命名"),
                    is_banned=False,
                    fail_count=0,
                ).control
            )
        return items
    
    def _on_user_select(self, user: Dict[str, Any]):
        """用户选择回调"""
        self._selected_user = user
        self._status_text.value = f"已选择: {user.get('username', '')} ({user.get('posts_count', 0)} 条)"
        self._status_text.color = Colors.TEXT_SECONDARY
        self._status_text.update()
    
    def _start_crawl(self):
        """开始爬取"""
        if not self._selected_user:
            self._status_text.value = "请先选择用户"
            self._status_text.color = Colors.WARNING
            self._status_text.update()
            return
        
        if not self._accounts:
            self._status_text.value = "请先配置账户"
            self._status_text.color = Colors.ERROR
            self._status_text.update()
            return
        
        # 创建工作器
        self._worker = DoPJWorker(
            page=self._page,
            on_log=self._on_log,
            on_complete=self._on_crawl_complete,
            on_task_update=self._on_task_update,
        )
        
        # 获取配置
        input_json = self._selected_user.get("path", "")
        threads = int(self._threads_slider.value)
        verify_mode = self._verify_switch.value
        
        # 更新 UI 状态
        self._start_button.set_loading(True)
        self._stop_button.visible = True
        self._stop_button.control.update()
        self._log_viewer.clear()
        
        # 显示当前任务
        username = self._selected_user.get("username", "未知")
        self._log_viewer.set_current_task(f"正在爬取用户帖子: {username}")
        
        # 开始爬取
        self._worker.start(
            input_json=input_json,
            accounts=self._accounts,
            output_dir=self._output_dir,
            threads=threads,
            incremental=not verify_mode,
        )
        
        # 监听状态变化
        app_state.add_listener(self._on_state_change)
    
    def _stop_crawl(self):
        """停止爬取"""
        if self._worker:
            self._worker.stop()
            # 立即给予视觉反馈
            self._status_text.value = "正在停止，等待当前任务完成..."
            self._status_text.color = Colors.WARNING
            try:
                self._status_text.update()
            except Exception:
                pass
    
    def _on_log(self, message: str, level: str):
        """日志回调"""
        self._log_viewer.add_log(message, level)
    
    def _on_task_update(self, stats: Dict[str, Any]):
        """任务状态更新"""
        self._status_card.update_stats(
            success=stats.get("success", 0),
            failed=stats.get("failed", 0),
            pending=stats.get("pending", 0),
            skipped=stats.get("skipped", 0),
        )
    
    def _on_state_change(self):
        """状态变化回调"""
        progress = app_state.dopj_progress
        if not progress:
            return
        
        # 更新进度条
        self._progress_bar.update_progress(
            current=progress.current,
            total=progress.total,
            label=progress.message or progress.current_title,
        )
        
        # 更新当前任务显示
        if progress.current_title:
            self._log_viewer.set_current_task(f"正在爬取: {progress.current_title}")
    
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
        
        # 刷新用户选择器
        self._user_selector.refresh()
        
        # 通知完成
        if self._on_complete:
            self._on_complete()
    
    def refresh(self):
        """刷新视图"""
        self._user_selector.refresh()
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def restore_state(self):
        """恢复视图状态（从 app_state 读取当前爬取状态）"""
        progress = app_state.dopj_progress
        is_running = app_state.is_dopj_running
        
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
                current=progress.current,
                total=progress.total,
                label=progress.message or progress.current_title,
            )
            
            # 恢复状态卡片
            self._status_card.update_stats(
                success=progress.success_count,
                failed=progress.failed_count,
                pending=progress.total - progress.current,
                skipped=progress.skipped_count,
            )
            
            # 恢复状态文本
            self._status_text.value = f"正在爬取: {progress.username or '未知'}"
            self._status_text.color = Colors.TEXT_SECONDARY
            try:
                self._status_text.update()
            except Exception:
                pass
            
            # 显示当前任务
            if hasattr(self._log_viewer, 'set_current_task'):
                self._log_viewer.set_current_task(f"正在爬取帖子: {progress.current_title or progress.current_tid or '未知'}")
            
            # 重新绑定监听器（确保状态更新能够继续）
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
