"""
表格组件

用于显示用户列表、帖子列表等数据表格。
使用包装类模式（Wrapper Class Pattern）以兼容新版 Flet API。
"""
import flet as ft
from typing import List, Dict, Any, Optional, Callable
from ..theme import Colors, Styles, create_status_badge


class UsersTable:
    """
    用户列表表格
    
    显示已存档用户及其统计信息。
    """
    
    def __init__(
        self,
        users: List[Dict[str, Any]] = None,
        on_row_click: Optional[Callable[[str], None]] = None,
    ):
        self._users = users or []
        self._on_row_click = on_row_click
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        self._data_table = ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Text("用户名", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=False,
                ),
                ft.DataColumn(
                    ft.Text("发言数", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=True,
                ),
                ft.DataColumn(
                    ft.Text("帖子数", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=True,
                ),
                ft.DataColumn(
                    ft.Text("状态", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=False,
                ),
            ],
            rows=self._build_rows(),
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Styles.BORDER_RADIUS_MD,
            heading_row_color=Colors.SURFACE_VARIANT,
            data_row_color={
                ft.ControlState.HOVERED: Colors.SURFACE_VARIANT,
            },
            column_spacing=30,
            horizontal_lines=ft.border.BorderSide(1, Colors.DIVIDER),
        )
        
        self._control = ft.Container(
            content=self._data_table,
            border_radius=Styles.BORDER_RADIUS_MD,
        )
    
    def _build_rows(self) -> List[ft.DataRow]:
        rows = []
        for user in self._users:
            username = user.get("name", "未知")
            posts_count = user.get("posts_count", 0)
            threads_count = user.get("threads_count", 0)
            
            # 确定状态
            if user.get("has_index"):
                status = ("已完成", "success")
            elif user.get("has_posts"):
                status = ("待详情", "warning")
            else:
                status = ("空目录", "info")
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Text(username, color=Colors.TEXT_PRIMARY),
                        on_tap=lambda e, u=username: self._handle_row_click(u),
                    ),
                    ft.DataCell(
                        ft.Text(str(posts_count), color=Colors.TEXT_SECONDARY),
                    ),
                    ft.DataCell(
                        ft.Text(str(threads_count), color=Colors.TEXT_SECONDARY),
                    ),
                    ft.DataCell(
                        create_status_badge(status[0], status[1]),
                    ),
                ],
                on_select_change=lambda e, u=username: self._handle_row_click(u),
            )
            rows.append(row)
        return rows
    
    def _handle_row_click(self, username: str):
        if self._on_row_click:
            self._on_row_click(username)
    
    def update_users(self, users: List[Dict[str, Any]]):
        """更新用户列表"""
        self._users = users
        self._data_table.rows = self._build_rows()
        self._control.update()
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)


class PostsTable:
    """
    帖子列表表格
    
    显示用户的发言列表（来自 posts.json）。
    """
    
    def __init__(
        self,
        posts: List[Dict[str, Any]] = None,
        on_row_click: Optional[Callable[[Dict[str, Any]], None]] = None,
        max_rows: int = 100,
    ):
        self._posts = posts or []
        self._on_row_click = on_row_click
        self._max_rows = max_rows
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        self._data_table = ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Text("ID", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=True,
                ),
                ft.DataColumn(
                    ft.Text("标题", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=False,
                ),
                ft.DataColumn(
                    ft.Text("贴吧", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=False,
                ),
                ft.DataColumn(
                    ft.Text("内容", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=False,
                ),
            ],
            rows=self._build_rows(),
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Styles.BORDER_RADIUS_MD,
            heading_row_color=Colors.SURFACE_VARIANT,
            data_row_color={
                ft.ControlState.HOVERED: Colors.SURFACE_VARIANT,
            },
            column_spacing=20,
            horizontal_lines=ft.border.BorderSide(1, Colors.DIVIDER),
        )
        
        # 如果帖子太多，添加滚动
        content = self._data_table
        if len(self._posts) > 20:
            content = ft.Column(
                controls=[self._data_table],
                scroll=ft.ScrollMode.AUTO,
                height=500,
            )
        
        self._control = ft.Container(
            content=content,
            border_radius=Styles.BORDER_RADIUS_MD,
        )
    
    def _build_rows(self) -> List[ft.DataRow]:
        rows = []
        display_posts = self._posts[:self._max_rows]
        
        for post in display_posts:
            post_id = post.get("id", 0)
            title = post.get("title", "无标题")
            forum = post.get("forum", "未知")
            content = post.get("content", "")
            
            # 截断长文本
            title_display = title[:40] + "..." if len(title) > 40 else title
            content_display = content[:30] + "..." if len(content) > 30 else content
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Text(str(post_id), color=Colors.TEXT_SECONDARY),
                    ),
                    ft.DataCell(
                        ft.Text(title_display, color=Colors.TEXT_PRIMARY),
                        on_tap=lambda e, p=post: self._handle_row_click(p),
                    ),
                    ft.DataCell(
                        ft.Text(forum, color=Colors.ACCENT),
                    ),
                    ft.DataCell(
                        ft.Text(content_display, color=Colors.TEXT_SECONDARY),
                    ),
                ],
                on_select_change=lambda e, p=post: self._handle_row_click(p),
            )
            rows.append(row)
        
        return rows
    
    def _handle_row_click(self, post: Dict[str, Any]):
        if self._on_row_click:
            self._on_row_click(post)
    
    def update_posts(self, posts: List[Dict[str, Any]]):
        """更新帖子列表"""
        self._posts = posts
        self._data_table.rows = self._build_rows()
        self._control.update()
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)


class ThreadsTable:
    """
    帖子详情列表表格
    
    显示已爬取的帖子详情（来自 threads 目录）。
    """
    
    def __init__(
        self,
        threads: List[Dict[str, Any]] = None,
        on_row_click: Optional[Callable[[int], None]] = None,
    ):
        self._threads = threads or []
        self._on_row_click = on_row_click
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        self._data_table = ft.DataTable(
            columns=[
                ft.DataColumn(
                    ft.Text("TID", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=True,
                ),
                ft.DataColumn(
                    ft.Text("标题", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=False,
                ),
                ft.DataColumn(
                    ft.Text("状态", color=Colors.TEXT_PRIMARY, weight=ft.FontWeight.W_500),
                    numeric=False,
                ),
            ],
            rows=self._build_rows(),
            border=ft.border.all(1, Colors.BORDER),
            border_radius=Styles.BORDER_RADIUS_MD,
            heading_row_color=Colors.SURFACE_VARIANT,
            data_row_color={
                ft.ControlState.HOVERED: Colors.SURFACE_VARIANT,
            },
            column_spacing=30,
            horizontal_lines=ft.border.BorderSide(1, Colors.DIVIDER),
        )
        
        self._control = ft.Container(
            content=self._data_table,
            border_radius=Styles.BORDER_RADIUS_MD,
        )
    
    def _build_rows(self) -> List[ft.DataRow]:
        rows = []
        for thread in self._threads:
            tid = thread.get("tid", 0)
            title = thread.get("title", "未知")
            status = thread.get("status", "pending")
            
            # 截断长文本
            title_display = title[:50] + "..." if len(title) > 50 else title
            
            # 状态映射
            status_map = {
                "success": ("成功", "success"),
                "failed": ("失败", "error"),
                "pending": ("等待", "info"),
                "skipped": ("跳过", "warning"),
            }
            status_info = status_map.get(status, ("未知", "info"))
            
            row = ft.DataRow(
                cells=[
                    ft.DataCell(
                        ft.Text(str(tid), color=Colors.TEXT_SECONDARY),
                    ),
                    ft.DataCell(
                        ft.Text(title_display, color=Colors.TEXT_PRIMARY),
                        on_tap=lambda e, t=tid: self._handle_row_click(t),
                    ),
                    ft.DataCell(
                        create_status_badge(status_info[0], status_info[1]),
                    ),
                ],
                on_select_change=lambda e, t=tid: self._handle_row_click(t),
            )
            rows.append(row)
        
        return rows
    
    def _handle_row_click(self, tid: int):
        if self._on_row_click:
            self._on_row_click(tid)
    
    def update_threads(self, threads: List[Dict[str, Any]]):
        """更新帖子列表"""
        self._threads = threads
        self._data_table.rows = self._build_rows()
        self._control.update()
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)
