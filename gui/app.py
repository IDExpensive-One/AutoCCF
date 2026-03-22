"""
AutoCCF GUI 主应用程序

整合所有视图和导航逻辑。
"""
import flet as ft
from typing import Optional, Dict, Any

from .theme import configure_page, Colors
from .state import app_state, ViewName
from .components.navigation import NavigationRailComponent
from .views import (
    HomeView,
    SettingsView,
    APoUView,
    DoPJView,
    UsersView,
    UserDetailView,
)


class AutoCCFApp:
    """AutoCCF GUI 应用程序"""
    
    def __init__(self):
        self._page: Optional[ft.Page] = None
        self._nav_rail: Optional[NavigationRailComponent] = None
        self._content_area: Optional[ft.Container] = None
        self._current_view: Optional[Any] = None  # 使用 Any 替代 UserControl
        self._views: Dict[ViewName, Any] = {}
        # 视图缓存 - 保持 APoU 和 DoPJ 视图实例，防止切换标签时丢失状态
        self._view_cache: Dict[ViewName, Any] = {}
    
    def main(self, page: ft.Page):
        """应用程序入口点"""
        self._page = page
        
        # 配置页面
        configure_page(page)
        
        # 创建导航栏
        self._nav_rail = NavigationRailComponent(
            on_change=self._on_navigate,
        )
        
        # 创建内容区域
        self._content_area = ft.Container(
            expand=True,
            bgcolor=Colors.BACKGROUND,
        )
        
        # 创建主布局
        main_layout = ft.Row(
            controls=[
                self._nav_rail.control,  # 使用 .control 属性获取底层控件
                ft.VerticalDivider(width=1, color=Colors.DIVIDER),
                self._content_area,
            ],
            expand=True,
        )
        
        page.add(main_layout)
        
        # 显示首页
        self._show_view(ViewName.HOME)
        
        # 监听状态变化
        app_state.add_listener(self._on_state_change)
    
    def _on_navigate(self, view: ViewName):
        """导航回调"""
        self._show_view(view)
    
    def _show_view(self, view: ViewName, data: Any = None):
        """显示指定视图"""
        # 更新状态
        app_state.current_view = view
        
        # 更新导航栏选中状态
        if self._nav_rail:
            self._nav_rail.set_view(view)
        
        # 获取或创建视图
        view_instance = self._get_view(view, data)
        
        # 更新内容区域（使用视图的 .control 属性）
        if self._content_area and view_instance:
            self._content_area.content = view_instance.control
            self._content_area.update()
        
        self._current_view = view_instance
    
    def _get_view(self, view: ViewName, data: Any = None) -> Any:
        """获取或创建视图实例"""
        # 对于 APOU 和 DOPJ 视图，使用缓存机制防止切换标签时丢失爬取状态
        if view in (ViewName.APOU, ViewName.DOPJ):
            if view not in self._view_cache:
                # 首次访问，创建新实例
                self._view_cache[view] = self._create_view(view, data)
            else:
                # 已缓存，恢复状态
                cached_view = self._view_cache[view]
                if hasattr(cached_view, 'restore_state'):
                    cached_view.restore_state()
            return self._view_cache[view]
        
        # 其他视图每次都创建新实例以确保数据刷新
        return self._create_view(view, data)
    
    def _create_view(self, view: ViewName, data: Any = None) -> Any:
        """创建视图实例"""
        if view == ViewName.HOME:
            return HomeView(
                on_navigate=lambda v: self._show_view(v),
            )
        
        elif view == ViewName.APOU:
            return APoUView(
                page=self._page,
                on_complete=self._on_crawl_complete,
            )
        
        elif view == ViewName.DOPJ:
            return DoPJView(
                page=self._page,
                on_complete=self._on_crawl_complete,
            )
        
        elif view == ViewName.USERS:
            return UsersView(
                on_navigate=self._on_users_navigate,
            )
        
        elif view == ViewName.USER_DETAIL:
            username = data if isinstance(data, str) else app_state.selected_user
            return UserDetailView(
                username=username or "",
                on_navigate=lambda v: self._show_view(v),
            )
        
        elif view == ViewName.SETTINGS:
            return SettingsView()
        
        else:
            # 默认返回首页
            return HomeView(
                on_navigate=lambda v: self._show_view(v),
            )
    
    def _on_users_navigate(self, view: ViewName, data: Any = None):
        """用户列表导航回调"""
        self._show_view(view, data)
    
    def _on_crawl_complete(self):
        """爬取完成回调"""
        # 刷新用户缓存
        app_state.invalidate_users_cache()
        # 如果当前在用户列表页，立即刷新
        if self._current_view and hasattr(self._current_view, 'refresh'):
            try:
                self._current_view.refresh()
            except Exception:
                pass
    
    def _on_state_change(self):
        """状态变化回调"""
        # 目前不需要额外处理
        pass


def run_app():
    """运行 GUI 应用程序"""
    app = AutoCCFApp()
    ft.run(app.main)


if __name__ == "__main__":
    run_app()
