"""
用户详情视图

显示单个用户的发言和帖子详情。
使用包装类模式（Wrapper Class Pattern）以兼容新版 Flet API。
"""
import json
import os
import flet as ft
from typing import Callable, Optional, List, Dict, Any
from pathlib import Path
from ..theme import Colors, Styles, create_card
from ..components.tables import PostsTable, ThreadsTable
from ..state import app_state, ViewName
from AutoCCF.config import config_manager


class UserDetailView:
    """用户详情视图"""
    
    def __init__(
        self,
        username: str = "",
        on_navigate: Optional[Callable[[ViewName], None]] = None,
    ):
        self._username = username or app_state.selected_user or ""
        self._on_navigate = on_navigate
        self._user_dir: Optional[Path] = None
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        # 获取用户目录
        try:
            config = config_manager.load()
            self._user_dir = config.get_user_dir(self._username)
        except Exception:
            self._user_dir = None
        
        # 加载数据
        user_data = self._load_user_data()
        posts = user_data.get("posts", [])
        threads = user_data.get("threads", [])
        
        # 返回按钮
        back_button = ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=Colors.TEXT_SECONDARY,
            tooltip="返回用户列表",
            on_click=lambda _: self._navigate_back(),
        )
        
        # 帖子表格
        self._posts_table = PostsTable(
            posts=posts,
            on_row_click=self._on_post_click,
        )
        
        # 帖子详情表格
        self._threads_table = ThreadsTable(
            threads=threads,
            on_row_click=self._on_thread_click,
        )
        
        # 标签页（Flet 0.80+ 新 API：Tabs 包含 TabBar + TabBarView）
        tab_bar = ft.TabBar(
            tabs=[
                ft.Tab(label=f"发言列表 ({len(posts)})", icon=ft.Icons.COMMENT),
                ft.Tab(label=f"帖子详情 ({len(threads)})", icon=ft.Icons.ARTICLE),
                ft.Tab(label="文件浏览", icon=ft.Icons.FOLDER),
            ],
        )
        tab_view = ft.TabBarView(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[self._posts_table.control],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=Styles.PADDING_MD,
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[self._threads_table.control],
                        scroll=ft.ScrollMode.AUTO,
                    ),
                    padding=Styles.PADDING_MD,
                ),
                self._build_files_tab(),
            ],
            expand=True,
        )
        tabs = ft.Tabs(
            content=ft.Column(
                controls=[tab_bar, tab_view],
                expand=True,
            ),
            length=3,
            selected_index=0,
            animation_duration=300,
        )
        
        self._control = ft.Container(
            content=ft.Column(
                controls=[
                    # 页面标题
                    ft.Row(
                        controls=[
                            back_button,
                            ft.Column(
                                controls=[
                                    ft.Text(
                                        self._username,
                                        size=28,
                                        weight=ft.FontWeight.BOLD,
                                        color=Colors.TEXT_PRIMARY,
                                    ),
                                    ft.Text(
                                        f"共 {len(posts)} 条发言，{len(threads)} 个帖子详情",
                                        size=16,
                                        color=Colors.TEXT_SECONDARY,
                                    ),
                                ],
                                spacing=4,
                            ),
                            ft.Container(expand=True),
                            self._build_action_buttons(),
                        ],
                    ),
                    
                    ft.Divider(height=16, color=Colors.DIVIDER),
                    
                    # 标签页
                    tabs,
                ],
                spacing=8,
                expand=True,
            ),
            padding=Styles.PADDING_LG,
            expand=True,
        )
    
    def _load_user_data(self) -> Dict[str, Any]:
        """加载用户数据（兼容新旧路径）"""
        result = {
            "posts": [],
            "threads": [],
            "index": None,
        }

        if not self._user_dir or not self._user_dir.exists():
            return result

        # 读取发言列表（优先新路径）
        posts_file = self._user_dir / "apou" / "posts.json"
        if not posts_file.exists():
            posts_file = self._user_dir / "posts.json"
        if posts_file.exists():
            try:
                with open(posts_file, "r", encoding="utf-8") as f:
                    result["posts"] = json.load(f)
            except Exception:
                pass

        # 读取索引（优先新路径）
        index_file = self._user_dir / "dopj" / "index.json"
        if not index_file.exists():
            index_file = self._user_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    result["index"] = json.load(f)

                # 从索引构建 threads 列表
                entries = result["index"].get("entries", [])
                result["threads"] = [
                    {
                        "tid": e.get("tid"),
                        "title": e.get("title"),
                        "status": e.get("status", "pending"),
                    }
                    for e in entries
                ]
            except Exception:
                pass
        else:
            # 如果没有索引，扫描 dopj/ 目录（新版）或 threads/ 目录（旧版）
            dopj_dir = self._user_dir / "dopj"
            if dopj_dir.exists():
                for tid_dir in dopj_dir.iterdir():
                    if tid_dir.is_dir() and tid_dir.name.isdigit():
                        # 新版路径: dopj/{tid}/threads/{tid}/thread.json
                        thread_file = tid_dir / "threads" / tid_dir.name / "thread.json"
                        if thread_file.exists():
                            try:
                                with open(thread_file, "r", encoding="utf-8") as f:
                                    thread_data = json.load(f)
                                result["threads"].append({
                                    "tid": int(tid_dir.name),
                                    "title": thread_data.get("title", "未知"),
                                    "status": "success",
                                })
                            except Exception:
                                pass
            else:
                # 旧版路径: threads/{tid}/thread.json
                threads_dir = self._user_dir / "threads"
                if threads_dir.exists():
                    for tid_dir in threads_dir.iterdir():
                        if tid_dir.is_dir():
                            thread_file = tid_dir / "thread.json"
                            if thread_file.exists():
                                try:
                                    with open(thread_file, "r", encoding="utf-8") as f:
                                        thread_data = json.load(f)
                                    result["threads"].append({
                                        "tid": int(tid_dir.name),
                                        "title": thread_data.get("title", "未知"),
                                        "status": "success",
                                    })
                                except Exception:
                                    pass

        return result
    
    def _build_action_buttons(self) -> ft.Control:
        """构建操作按钮"""
        return ft.Row(
            controls=[
                ft.ElevatedButton(
                    "打开目录",
                    icon=ft.Icons.FOLDER_OPEN,
                    bgcolor=Colors.SURFACE_VARIANT,
                    color=Colors.TEXT_PRIMARY,
                    on_click=self._open_folder,
                ),
                ft.ElevatedButton(
                    "刷新 APoU",
                    icon=ft.Icons.PERSON_SEARCH,
                    bgcolor=Colors.PRIMARY,
                    color=Colors.TEXT_PRIMARY,
                    on_click=lambda _: self._run_apou(),
                ),
                ft.ElevatedButton(
                    "运行 DoPJ",
                    icon=ft.Icons.ARTICLE,
                    bgcolor=Colors.ACCENT,
                    color=Colors.TEXT_PRIMARY,
                    on_click=lambda _: self._run_dopj(),
                ),
            ],
            spacing=8,
        )
    
    def _build_files_tab(self) -> ft.Control:
        """构建文件浏览标签页"""
        if not self._user_dir or not self._user_dir.exists():
            return ft.Container(
                content=ft.Text(
                    "用户目录不存在",
                    color=Colors.TEXT_DISABLED,
                ),
                padding=Styles.PADDING_LG,
            )
        
        files_list = []
        
        # 列出目录内容
        try:
            for item in sorted(self._user_dir.iterdir()):
                is_dir = item.is_dir()
                icon = ft.Icons.FOLDER if is_dir else ft.Icons.DESCRIPTION
                color = Colors.WARNING if is_dir else Colors.TEXT_SECONDARY
                
                # 获取文件大小
                if is_dir:
                    size_text = f"{len(list(item.iterdir()))} 项"
                else:
                    size = item.stat().st_size
                    if size < 1024:
                        size_text = f"{size} B"
                    elif size < 1024 * 1024:
                        size_text = f"{size / 1024:.1f} KB"
                    else:
                        size_text = f"{size / 1024 / 1024:.1f} MB"
                
                files_list.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Icon(icon, size=20, color=color),
                                ft.Text(
                                    item.name,
                                    size=14,
                                    color=Colors.TEXT_PRIMARY,
                                    expand=True,
                                ),
                                ft.Text(
                                    size_text,
                                    size=12,
                                    color=Colors.TEXT_DISABLED,
                                ),
                            ],
                            spacing=8,
                        ),
                        padding=Styles.PADDING_SM,
                        bgcolor=Colors.SURFACE_VARIANT,
                        border_radius=Styles.BORDER_RADIUS_SM,
                    )
                )
        except Exception:
            pass
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(
                        f"目录: {self._user_dir}",
                        size=12,
                        color=Colors.TEXT_DISABLED,
                    ),
                    ft.Divider(height=1, color=Colors.DIVIDER),
                    ft.Column(
                        controls=files_list if files_list else [
                            ft.Text("目录为空", color=Colors.TEXT_DISABLED)
                        ],
                        spacing=4,
                        scroll=ft.ScrollMode.AUTO,
                    ),
                ],
                spacing=8,
            ),
            padding=Styles.PADDING_MD,
        )
    
    def _navigate_back(self):
        """返回用户列表"""
        if self._on_navigate:
            self._on_navigate(ViewName.USERS)
    
    def _on_post_click(self, post: Dict[str, Any]):
        """点击发言"""
        # TODO: 显示发言详情或跳转到帖子
        pass
    
    def _on_thread_click(self, tid: int):
        """点击帖子"""
        # TODO: 显示帖子内容
        pass
    
    def _open_folder(self, _):
        """打开用户目录"""
        if self._user_dir and self._user_dir.exists():
            import subprocess
            import sys
            
            if sys.platform == "win32":
                os.startfile(str(self._user_dir))
            elif sys.platform == "darwin":
                subprocess.run(["open", str(self._user_dir)])
            else:
                subprocess.run(["xdg-open", str(self._user_dir)])
    
    def _run_apou(self):
        """运行 APoU"""
        app_state.selected_user = self._username
        if self._on_navigate:
            self._on_navigate(ViewName.APOU)
    
    def _run_dopj(self):
        """运行 DoPJ"""
        app_state.selected_user = self._username
        if self._on_navigate:
            self._on_navigate(ViewName.DOPJ)
    
    def set_username(self, username: str):
        """设置用户名"""
        self._username = username
        self._control.update()
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)
