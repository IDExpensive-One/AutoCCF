"""
用户列表视图

显示已存档的用户列表。
使用包装类模式（Wrapper Class Pattern）以兼容新版 Flet API。
"""
import flet as ft
from typing import Callable, Optional, List, Dict, Any
from ..theme import Colors, Styles, create_card
from ..components.tables import UsersTable
from ..state import app_state, ViewName
from AutoCCF.config import config_manager


class UsersView:
    """用户列表视图"""
    
    def __init__(
        self,
        on_navigate: Optional[Callable[[ViewName, Optional[str]], None]] = None,
    ):
        self._on_navigate = on_navigate
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        # 加载用户列表
        users = self._load_users()
        
        # 搜索框
        self._search_field = ft.TextField(
            label="搜索用户",
            hint_text="输入用户名搜索",
            prefix_icon=ft.Icons.SEARCH,
            border_color=Colors.BORDER,
            focused_border_color=Colors.PRIMARY,
            on_change=self._on_search,
            width=300,
        )
        
        # 刷新按钮
        self._refresh_button = ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_color=Colors.PRIMARY,
            tooltip="刷新列表",
            on_click=self._refresh,
        )
        
        # 用户表格
        self._users_table = UsersTable(
            users=users,
            on_row_click=self._on_user_click,
        )
        
        # 统计信息
        total_users = len(users)
        total_posts = sum(u.get("posts_count", 0) for u in users)
        total_threads = sum(u.get("threads_count", 0) for u in users)
        
        self._control = ft.Container(
            content=ft.Column(
                controls=[
                    # 页面标题
                    ft.Row(
                        controls=[
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        "用户管理",
                                        size=28,
                                        weight=ft.FontWeight.BOLD,
                                        color=Colors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        f"共 {total_users} 个用户，{total_posts} 条发言，{total_threads} 个帖子",
                                        size=16,
                                        color=Colors.TEXT_SECONDARY,
                                    ),
                                ],
                                spacing=4,
                            ),
                            ft.Container(expand=True),
                            self._search_field,
                            self._refresh_button,
                        ],
                    ),
                    
                    ft.Divider(height=24, color=Colors.DIVIDER),
                    
                    # 用户表格
                    ft.Container(
                        content=self._users_table.control,
                        expand=True,
                    ),
                ],
                spacing=8,
                expand=True,
            ),
            padding=Styles.PADDING_LG,
            expand=True,
        )
    
    def _load_users(self) -> List[Dict[str, Any]]:
        """加载用户列表"""
        try:
            config_manager.load()
            return config_manager.list_users()
        except Exception:
            return []
    
    def _on_search(self, e):
        """搜索用户"""
        query = e.control.value.lower().strip()
        
        all_users = self._load_users()
        
        if query:
            filtered = [
                u for u in all_users
                if query in u.get("name", "").lower()
            ]
        else:
            filtered = all_users
        
        self._users_table.update_users(filtered)
    
    def _on_user_click(self, username: str):
        """点击用户"""
        app_state.selected_user = username
        if self._on_navigate:
            self._on_navigate(ViewName.USER_DETAIL, username)
    
    def _refresh(self, _=None):
        """刷新列表"""
        users = self._load_users()
        self._users_table.update_users(users)
    
    def refresh(self):
        """公开的刷新方法"""
        self._refresh()
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)
