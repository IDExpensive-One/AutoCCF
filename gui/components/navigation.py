"""
导航组件

NavigationRail 侧边栏导航。
使用包装类模式（Wrapper Class Pattern）以兼容新版 Flet API。
"""
import flet as ft
from typing import Callable, Optional
from ..theme import Colors, Styles
from ..state import ViewName, app_state


def create_icon_with_indicator(
    icon: str,
    show_indicator: bool = False,
) -> ft.Stack:
    """
    创建带运行状态指示器的图标
    
    Args:
        icon: 图标名称
        show_indicator: 是否显示绿色指示点
        
    Returns:
        Stack 包含图标和可选的指示点
    """
    indicator = ft.Container(
        width=8,
        height=8,
        border_radius=4,
        bgcolor=Colors.RUNNING_INDICATOR if show_indicator else "transparent",
        right=0,
        top=0,
    )
    
    return ft.Stack(
        controls=[
            ft.Icon(icon, size=24),
            indicator,
        ],
        width=24,
        height=24,
    )


def create_navigation_rail(
    selected_index: int = 0,
    on_change: Optional[Callable[[ViewName], None]] = None,
) -> ft.NavigationRail:
    """
    创建导航栏
    
    Args:
        selected_index: 当前选中的索引
        on_change: 选中变化回调
        
    Returns:
        NavigationRail 组件
    """
    
    # 视图映射
    view_map = {
        0: ViewName.HOME,
        1: ViewName.APOU,
        2: ViewName.DOPJ,
        3: ViewName.USERS,
        4: ViewName.SETTINGS,
    }
    
    def handle_change(e):
        if on_change and e.control.selected_index is not None:
            view = view_map.get(e.control.selected_index, ViewName.HOME)
            on_change(view)
    
    return ft.NavigationRail(
        selected_index=selected_index,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=80,
        min_extended_width=180,
        bgcolor=Colors.SURFACE,
        indicator_color=Colors.PRIMARY,
        on_change=handle_change,
        leading=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Icon(
                        ft.Icons.ARCHIVE,
                        size=32,
                        color=Colors.PRIMARY,
                    ),
                    ft.Text(
                        "AutoCCF",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.TEXT_PRIMARY,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            ),
            padding=ft.padding.only(top=20, bottom=20),
        ),
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.HOME_OUTLINED,
                selected_icon=ft.Icons.HOME,
                label="主页",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.PERSON_SEARCH_OUTLINED,
                selected_icon=ft.Icons.PERSON_SEARCH,
                label="APoU",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ARTICLE_OUTLINED,
                selected_icon=ft.Icons.ARTICLE,
                label="DoPJ",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.PEOPLE_OUTLINED,
                selected_icon=ft.Icons.PEOPLE,
                label="用户",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="设置",
            ),
        ],
    )


class NavigationRailComponent:
    """
    导航栏组件（包装类版本）
    
    支持动态更新和状态管理，包括运行状态指示器。
    """
    
    def __init__(
        self,
        on_change: Optional[Callable[[ViewName], None]] = None,
    ):
        self._on_change = on_change
        self._selected_index = 0
        self._control: Optional[ft.NavigationRail] = None
        
        # 视图到索引的映射
        self._view_to_index = {
            ViewName.HOME: 0,
            ViewName.APOU: 1,
            ViewName.DOPJ: 2,
            ViewName.USERS: 3,
            ViewName.USER_DETAIL: 3,  # 用户详情也属于用户页面
            ViewName.SETTINGS: 4,
        }
        
        self._index_to_view = {v: k for k, v in self._view_to_index.items() if k != ViewName.USER_DETAIL}
        
        # 运行状态指示器
        self._apou_indicator: Optional[ft.Container] = None
        self._dopj_indicator: Optional[ft.Container] = None
        
        self._build()
        
        # 监听状态变化以更新指示器
        app_state.add_listener(self._update_indicators)
    
    def _build(self):
        # 创建带指示器的图标
        self._apou_indicator = ft.Container(
            width=8,
            height=8,
            border_radius=4,
            bgcolor="transparent",
            right=-2,
            top=-2,
        )
        
        self._dopj_indicator = ft.Container(
            width=8,
            height=8,
            border_radius=4,
            bgcolor="transparent",
            right=-2,
            top=-2,
        )
        
        apou_icon = ft.Stack(
            controls=[
                ft.Icon(ft.Icons.PERSON_SEARCH_OUTLINED, size=24),
                self._apou_indicator,
            ],
            width=28,
            height=28,
        )
        
        apou_icon_selected = ft.Stack(
            controls=[
                ft.Icon(ft.Icons.PERSON_SEARCH, size=24),
                self._apou_indicator,
            ],
            width=28,
            height=28,
        )
        
        dopj_icon = ft.Stack(
            controls=[
                ft.Icon(ft.Icons.ARTICLE_OUTLINED, size=24),
                self._dopj_indicator,
            ],
            width=28,
            height=28,
        )
        
        dopj_icon_selected = ft.Stack(
            controls=[
                ft.Icon(ft.Icons.ARTICLE, size=24),
                self._dopj_indicator,
            ],
            width=28,
            height=28,
        )
        
        self._nav_rail = ft.NavigationRail(
            selected_index=self._selected_index,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=80,
            min_extended_width=180,
            bgcolor=Colors.SURFACE,
            indicator_color=Colors.PRIMARY,
            on_change=self._handle_nav_change,
            leading=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(
                            ft.Icons.ARCHIVE,
                            size=32,
                            color=Colors.PRIMARY,
                        ),
                        ft.Text(
                            "AutoCCF",
                            size=14,
                            weight=ft.FontWeight.BOLD,
                            color=Colors.TEXT_PRIMARY,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                ),
                padding=ft.padding.only(top=20, bottom=20),
            ),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="主页",
                ),
                ft.NavigationRailDestination(
                    icon=apou_icon,
                    selected_icon=apou_icon_selected,
                    label="APoU",
                ),
                ft.NavigationRailDestination(
                    icon=dopj_icon,
                    selected_icon=dopj_icon_selected,
                    label="DoPJ",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.PEOPLE_OUTLINED,
                    selected_icon=ft.Icons.PEOPLE,
                    label="用户",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="设置",
                ),
            ],
        )
        self._control = self._nav_rail
        
        # 初始更新指示器状态
        self._update_indicators()
    
    def _handle_nav_change(self, e):
        """导航变化处理"""
        if e.control.selected_index is not None:
            self._selected_index = e.control.selected_index
            view = self._index_to_view.get(e.control.selected_index, ViewName.HOME)
            if self._on_change:
                self._on_change(view)
    
    def _update_indicators(self):
        """更新运行状态指示器"""
        # 更新 APoU 指示器
        if self._apou_indicator:
            new_color = Colors.RUNNING_INDICATOR if app_state.is_apou_running else "transparent"
            if self._apou_indicator.bgcolor != new_color:
                self._apou_indicator.bgcolor = new_color
                try:
                    self._apou_indicator.update()
                except Exception:
                    pass  # 控件可能尚未挂载
        
        # 更新 DoPJ 指示器
        if self._dopj_indicator:
            new_color = Colors.RUNNING_INDICATOR if app_state.is_dopj_running else "transparent"
            if self._dopj_indicator.bgcolor != new_color:
                self._dopj_indicator.bgcolor = new_color
                try:
                    self._dopj_indicator.update()
                except Exception:
                    pass  # 控件可能尚未挂载
    
    def set_view(self, view: ViewName):
        """设置当前视图"""
        new_index = self._view_to_index.get(view, 0)
        if new_index != self._selected_index:
            self._selected_index = new_index
            self._nav_rail.selected_index = new_index
            self._control.update()
    
    @property
    def control(self) -> ft.NavigationRail:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)
