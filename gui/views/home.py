"""
主页视图

显示统计信息和快速操作。
使用包装类模式（Wrapper Class Pattern）以兼容新版 Flet API。
"""
import flet as ft
from typing import Callable, Optional, List, Dict, Any
from ..theme import Colors, Styles, create_card
from ..state import app_state, ViewName
from AutoCCF.config import config_manager
from AutoCCF.utils import is_valid_bduss


class StatCard:
    """统计卡片"""
    
    def __init__(
        self,
        title: str,
        value: str,
        icon: str,
        color: str = Colors.PRIMARY,
        on_click: Optional[Callable[[], None]] = None,
    ):
        self._title = title
        self._value = value
        self._icon = icon
        self._color = color
        self._on_click = on_click
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        self._control = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        self._icon,
                        size=40,
                        color=self._color,
                    ),
                    ft.Column(
                        controls=[
                            ft.Text(
                                self._value,
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=Colors.TEXT_PRIMARY,
                            ),
                            ft.Text(
                                self._title,
                                size=14,
                                color=Colors.TEXT_SECONDARY,
                            ),
                        ],
                        spacing=2,
                    ),
                ],
                spacing=16,
            ),
            padding=Styles.PADDING_LG,
            bgcolor=Colors.CARD,
            border_radius=Styles.BORDER_RADIUS_LG,
            on_click=lambda _: self._on_click() if self._on_click else None,
            ink=True if self._on_click else False,
        )
    
    def update_value(self, value: str):
        """更新数值"""
        self._value = value
        self._control.update()
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)


class QuickActionCard:
    """快速操作卡片"""
    
    def __init__(
        self,
        title: str,
        description: str,
        icon: str,
        color: str = Colors.PRIMARY,
        on_click: Optional[Callable[[], None]] = None,
    ):
        self._title = title
        self._description = description
        self._icon = icon
        self._color = color
        self._on_click = on_click
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        self._control = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        self._icon,
                        size=32,
                        color=self._color,
                    ),
                    ft.Text(
                        self._title,
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        self._description,
                        size=12,
                        color=Colors.TEXT_SECONDARY,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            padding=Styles.PADDING_LG,
            bgcolor=Colors.CARD,
            border_radius=Styles.BORDER_RADIUS_LG,
            on_click=lambda _: self._on_click() if self._on_click else None,
            ink=True,
            width=180,
            height=140,
        )
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)


class HomeView:
    """主页视图"""
    
    def __init__(
        self,
        on_navigate: Optional[Callable[[ViewName], None]] = None,
    ):
        self._on_navigate = on_navigate
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        # 获取统计信息
        users = self._get_users_stats()
        
        self._control = ft.Container(
            content=ft.Column(
                controls=[
                    # 页面标题
                    ft.Text(
                        "欢迎使用 AutoCCF",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Text(
                        "百度贴吧数据存档工具",
                        size=16,
                        color=Colors.TEXT_SECONDARY,
                    ),
                    
                    ft.Divider(height=24, color=Colors.DIVIDER),
                    
                    # 统计卡片
                    ft.Text(
                        "数据概览",
                        size=20,
                        weight=ft.FontWeight.W_500,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Row(
                        controls=[
                            StatCard(
                                title="已存档用户",
                                value=str(users.get("total", 0)),
                                icon=ft.Icons.PEOPLE,
                                color=Colors.PRIMARY,
                                on_click=lambda: self._navigate(ViewName.USERS),
                            ).control,
                            StatCard(
                                title="已获取发言",
                                value=str(users.get("total_posts", 0)),
                                icon=ft.Icons.COMMENT,
                                color=Colors.ACCENT,
                            ).control,
                            StatCard(
                                title="已爬取帖子",
                                value=str(users.get("total_threads", 0)),
                                icon=ft.Icons.ARTICLE,
                                color=Colors.SUCCESS,
                            ).control,
                        ],
                        spacing=16,
                        wrap=True,
                    ),
                    
                    ft.Container(height=24),
                    
                    # 快速操作
                    ft.Text(
                        "快速操作",
                        size=20,
                        weight=ft.FontWeight.W_500,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Row(
                        controls=[
                            QuickActionCard(
                                title="获取发言列表",
                                description="APoU - 用户发言爬取",
                                icon=ft.Icons.PERSON_SEARCH,
                                color=Colors.PRIMARY,
                                on_click=lambda: self._navigate(ViewName.APOU),
                            ).control,
                            QuickActionCard(
                                title="获取帖子详情",
                                description="DoPJ - 帖子内容爬取",
                                icon=ft.Icons.ARTICLE,
                                color=Colors.ACCENT,
                                on_click=lambda: self._navigate(ViewName.DOPJ),
                            ).control,
                            QuickActionCard(
                                title="浏览用户数据",
                                description="查看已存档的用户",
                                icon=ft.Icons.FOLDER_OPEN,
                                color=Colors.WARNING,
                                on_click=lambda: self._navigate(ViewName.USERS),
                            ).control,
                            QuickActionCard(
                                title="应用设置",
                                description="配置账户和参数",
                                icon=ft.Icons.SETTINGS,
                                color=Colors.TEXT_SECONDARY,
                                on_click=lambda: self._navigate(ViewName.SETTINGS),
                            ).control,
                        ],
                        spacing=16,
                        wrap=True,
                    ),
                    
                    ft.Container(height=24),
                    
                    # 状态信息
                    self._build_status_section(),
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=Styles.PADDING_LG,
            expand=True,
        )
    
    def _navigate(self, view: ViewName):
        """导航到指定视图"""
        if self._on_navigate:
            self._on_navigate(view)
    
    def _get_users_stats(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        try:
            config_manager.load()
            users = config_manager.list_users()
            
            total_posts = sum(u.get("posts_count", 0) for u in users)
            total_threads = sum(u.get("threads_count", 0) for u in users)
            
            return {
                "total": len(users),
                "total_posts": total_posts,
                "total_threads": total_threads,
                "users": users,
            }
        except Exception:
            return {
                "total": 0,
                "total_posts": 0,
                "total_threads": 0,
                "users": [],
            }
    
    def _build_status_section(self) -> ft.Control:
        """构建状态区域"""
        # 检查配置状态
        try:
            config = config_manager.load()
            has_accounts = config.has_valid_accounts()
            total_accounts = len(config.accounts)
            valid_accounts = sum(1 for account in config.accounts if is_valid_bduss(account.bduss))
            db_dir = str(config.get_database_path())
        except Exception:
            has_accounts = False
            total_accounts = 0
            valid_accounts = 0
            db_dir = "未配置"
        
        status_items = []
        
        # 数据库目录
        status_items.append(
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.FOLDER, size=16, color=Colors.TEXT_SECONDARY),
                    ft.Text("数据目录:", size=14, color=Colors.TEXT_SECONDARY),
                    ft.Text(db_dir, size=14, color=Colors.TEXT_PRIMARY),
                ],
                spacing=8,
            )
        )
        
        # 账户状态
        if has_accounts:
            account_icon = ft.Icons.CHECK_CIRCLE
            account_color = Colors.SUCCESS
            account_text = f"有效 {valid_accounts} / 总计 {total_accounts}"
        else:
            account_icon = ft.Icons.WARNING
            account_color = Colors.WARNING
            account_text = f"有效 {valid_accounts} / 总计 {total_accounts} - 需要添加可用 BDUSS 才能使用 DoPJ"
        
        status_items.append(
            ft.Row(
                controls=[
                    ft.Icon(account_icon, size=16, color=account_color),
                    ft.Text("账户状态:", size=14, color=Colors.TEXT_SECONDARY),
                    ft.Text(account_text, size=14, color=account_color),
                ],
                spacing=8,
            )
        )
        
        return create_card(
            ft.Column(
                controls=[
                    ft.Text(
                        "系统状态",
                        size=16,
                        weight=ft.FontWeight.W_500,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    ft.Divider(height=1, color=Colors.DIVIDER),
                    *status_items,
                ],
                spacing=8,
            )
        )
    
    def refresh(self):
        """刷新视图"""
        self._control.update()
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)
