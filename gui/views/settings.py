"""
设置视图

配置管理界面。
使用包装类模式（Wrapper Class Pattern）以兼容新版 Flet API。
"""
import flet as ft
from typing import Callable, Optional, List, Dict, Any
from pathlib import Path
from ..theme import Colors, Styles, create_card
from ..components.forms import BDUSSInput, ConfigSlider, ActionButton
from AutoCCF.config import config_manager, UnifiedConfig, Account
from AutoCCF.utils import is_valid_bduss


class AccountEditor:
    """账户编辑器"""
    
    def __init__(
        self,
        accounts: List[Account] = None,
        on_change: Optional[Callable[[List[Account]], None]] = None,
    ):
        self._accounts = accounts or []
        self._on_change = on_change
        self._control: Optional[ft.Column] = None
        self._build()
    
    def _build(self):
        self._accounts_column = ft.Column(
            controls=self._build_account_rows(),
            spacing=8,
        )
        
        self._control = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            "账户管理",
                            size=16,
                            weight=ft.FontWeight.W_500,
                            color=Colors.TEXT_PRIMARY,
                        ),
                        ft.Container(expand=True),
                        ft.IconButton(
                            icon=ft.Icons.ADD,
                            icon_color=Colors.PRIMARY,
                            tooltip="添加账户",
                            on_click=self._add_account,
                        ),
                    ],
                ),
                ft.Divider(height=1, color=Colors.DIVIDER),
                self._accounts_column,
                ft.Text(
                    "BDUSS 获取方法: 浏览器 F12 → Application → Cookies → BDUSS",
                    size=12,
                    color=Colors.TEXT_DISABLED,
                ),
            ],
            spacing=8,
        )
    
    def _build_account_rows(self) -> List[ft.Control]:
        """构建账户行"""
        rows = []
        for i, account in enumerate(self._accounts):
            is_valid = is_valid_bduss(account.bduss)
            
            row = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(
                            ft.Icons.CHECK_CIRCLE if is_valid else ft.Icons.ERROR,
                            size=20,
                            color=Colors.SUCCESS if is_valid else Colors.WARNING,
                        ),
                        ft.TextField(
                            value=account.name,
                            label="名称",
                            width=120,
                            height=48,
                            text_size=14,
                            border_color=Colors.BORDER,
                            focused_border_color=Colors.PRIMARY,
                            on_change=lambda e, idx=i: self._update_name(idx, e.control.value),
                        ),
                        ft.TextField(
                            value=account.bduss[:20] + "..." if len(account.bduss) > 20 else account.bduss,
                            label="BDUSS",
                            password=True,
                            can_reveal_password=True,
                            expand=True,
                            height=48,
                            text_size=14,
                            border_color=Colors.BORDER,
                            focused_border_color=Colors.PRIMARY,
                            on_change=lambda e, idx=i: self._update_bduss(idx, e.control.value),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            icon_color=Colors.ERROR,
                            tooltip="删除账户",
                            on_click=lambda _, idx=i: self._remove_account(idx),
                        ),
                    ],
                    spacing=8,
                ),
                padding=Styles.PADDING_SM,
                bgcolor=Colors.SURFACE_VARIANT,
                border_radius=Styles.BORDER_RADIUS_SM,
            )
            rows.append(row)
        
        if not self._accounts:
            rows.append(
                ft.Container(
                    content=ft.Text(
                        "暂无账户，点击右上角 + 添加",
                        color=Colors.TEXT_DISABLED,
                    ),
                    padding=Styles.PADDING_MD,
                )
            )
        
        return rows
    
    def _add_account(self, _):
        """添加账户"""
        new_account = Account(
            name=f"账户{len(self._accounts) + 1}",
            bduss="",
        )
        self._accounts.append(new_account)
        self._refresh()
        self._notify_change()
    
    def _remove_account(self, index: int):
        """删除账户"""
        if 0 <= index < len(self._accounts):
            self._accounts.pop(index)
            self._refresh()
            self._notify_change()
    
    def _update_name(self, index: int, name: str):
        """更新账户名称"""
        if 0 <= index < len(self._accounts):
            self._accounts[index].name = name
            self._notify_change()
    
    def _update_bduss(self, index: int, bduss: str):
        """更新 BDUSS"""
        if 0 <= index < len(self._accounts):
            self._accounts[index].bduss = bduss
            self._notify_change()
    
    def _refresh(self):
        """刷新列表"""
        self._accounts_column.controls = self._build_account_rows()
        self._control.update()
    
    def _notify_change(self):
        """通知变更"""
        if self._on_change:
            self._on_change(self._accounts)
    
    def get_accounts(self) -> List[Account]:
        """获取账户列表"""
        return self._accounts
    
    @property
    def control(self) -> ft.Column:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)


class SettingsView:
    """设置视图"""
    
    def __init__(self):
        self._config: Optional[UnifiedConfig] = None
        self._modified = False
        self._control: Optional[ft.Container] = None
        self._build()
    
    def _build(self):
        # 加载配置
        try:
            self._config = config_manager.load()
        except Exception:
            self._config = UnifiedConfig()
        
        # 数据库目录（显示绝对路径）
        abs_db_dir = str(Path(self._config.database_dir).resolve())
        self._db_dir_field = ft.TextField(
            value=abs_db_dir,
            label="数据存储目录（绝对路径）",
            border_color=Colors.BORDER,
            focused_border_color=Colors.PRIMARY,
            on_change=self._on_db_dir_change,
            suffix=ft.IconButton(
                icon=ft.Icons.FOLDER_OPEN,
                icon_color=Colors.TEXT_SECONDARY,
                tooltip="选择目录",
                on_click=self._browse_folder,
            ),
        )
        
        # 账户编辑器
        self._account_editor = AccountEditor(
            accounts=list(self._config.accounts),
            on_change=self._on_accounts_change,
        )
        
        # APoU 设置
        self._apou_delay_slider = ConfigSlider(
            label="页间延迟",
            min_value=0.5,
            max_value=10.0,
            value=self._config.apou.page_delay,
            step=0.5,
            unit="秒",
            on_change=lambda v: self._on_config_change("apou_delay", v),
        )
        
        self._apou_retries_slider = ConfigSlider(
            label="最大重试次数",
            min_value=1,
            max_value=10,
            value=float(self._config.apou.max_retries),
            step=1,
            unit="次",
            on_change=lambda v: self._on_config_change("apou_retries", v),
        )
        
        # DoPJ 设置
        self._dopj_threads_slider = ConfigSlider(
            label="并发线程数",
            min_value=1,
            max_value=10,
            value=float(self._config.dopj.threads),
            step=1,
            unit="",
            on_change=lambda v: self._on_config_change("dopj_threads", v),
        )
        
        self._dopj_interval_slider = ConfigSlider(
            label="最小请求间隔",
            min_value=0.5,
            max_value=10.0,
            value=self._config.dopj.min_interval,
            step=0.5,
            unit="秒",
            on_change=lambda v: self._on_config_change("dopj_interval", v),
        )
        
        # 保存按钮
        self._save_button = ActionButton(
            text="保存设置",
            icon=ft.Icons.SAVE,
            on_click=self._save_config,
            disabled=True,
        )
        
        # 状态消息
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
                        "应用设置",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color=Colors.TEXT_PRIMARY,
                    ),
                    
                    ft.Divider(height=24, color=Colors.DIVIDER),
                    
                    # 基本设置
                    create_card(
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "基本设置",
                                    size=16,
                                    weight=ft.FontWeight.W_500,
                                    color=Colors.TEXT_PRIMARY,
                                ),
                                ft.Divider(height=1, color=Colors.DIVIDER),
                                self._db_dir_field,
                            ],
                            spacing=8,
                        )
                    ),
                    
                    ft.Container(height=16),
                    
                    # 账户设置
                    create_card(self._account_editor.control),
                    
                    ft.Container(height=16),
                    
                    # APoU 设置
                    create_card(
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "APoU 设置",
                                    size=16,
                                    weight=ft.FontWeight.W_500,
                                    color=Colors.TEXT_PRIMARY,
                                ),
                                ft.Divider(height=1, color=Colors.DIVIDER),
                                self._apou_delay_slider.control,
                                self._apou_retries_slider.control,
                            ],
                            spacing=12,
                        )
                    ),
                    
                    ft.Container(height=16),
                    
                    # DoPJ 设置
                    create_card(
                        ft.Column(
                            controls=[
                                ft.Text(
                                    "DoPJ 设置",
                                    size=16,
                                    weight=ft.FontWeight.W_500,
                                    color=Colors.TEXT_PRIMARY,
                                ),
                                ft.Divider(height=1, color=Colors.DIVIDER),
                                self._dopj_threads_slider.control,
                                self._dopj_interval_slider.control,
                            ],
                            spacing=12,
                        )
                    ),
                    
                    ft.Container(height=24),
                    
                    # 保存按钮
                    ft.Row(
                        controls=[
                            self._save_button.control,
                            self._status_text,
                        ],
                        spacing=16,
                    ),
                ],
                spacing=8,
                scroll=ft.ScrollMode.AUTO,
            ),
            padding=Styles.PADDING_LG,
            expand=True,
        )
    
    def _on_db_dir_change(self, e):
        """数据目录变更"""
        value = e.control.value.strip()
        # 保存绝对路径
        self._config.database_dir = str(Path(value).resolve()) if value else value
        self._set_modified(True)

    def _browse_folder(self, _):
        """浏览文件夹（使用系统原生对话框）"""
        import threading

        def _pick():
            try:
                import tkinter as tk
                from tkinter import filedialog
                root = tk.Tk()
                root.withdraw()
                root.attributes("-topmost", True)
                initial = self._db_dir_field.value or "."
                folder = filedialog.askdirectory(
                    title="选择数据存储目录",
                    initialdir=initial,
                )
                root.destroy()
                if folder:
                    abs_path = str(Path(folder).resolve())
                    self._db_dir_field.value = abs_path
                    self._db_dir_field.update()
                    self._config.database_dir = abs_path
                    self._set_modified(True)
            except Exception:
                pass

        # 在线程中运行以避免阻塞 UI
        threading.Thread(target=_pick, daemon=True).start()
    
    def _on_accounts_change(self, accounts: List[Account]):
        """账户变更"""
        self._config.accounts = accounts
        self._set_modified(True)
    
    def _on_config_change(self, key: str, value: float):
        """配置变更"""
        if key == "apou_delay":
            self._config.apou.page_delay = value
        elif key == "apou_retries":
            self._config.apou.max_retries = int(value)
        elif key == "dopj_threads":
            self._config.dopj.threads = int(value)
        elif key == "dopj_interval":
            self._config.dopj.min_interval = value
        
        self._set_modified(True)
    
    def _set_modified(self, modified: bool):
        """设置修改状态"""
        self._modified = modified
        self._save_button.set_disabled(not modified)
        if modified:
            self._status_text.value = "有未保存的更改"
            self._status_text.color = Colors.WARNING
        else:
            self._status_text.value = ""
        self._status_text.update()
    
    def _save_config(self):
        """保存配置"""
        try:
            self._save_button.set_loading(True)
            
            # 保存配置
            config_path = self._config.save()
            
            self._set_modified(False)
            self._status_text.value = f"已保存到 {config_path}"
            self._status_text.color = Colors.SUCCESS
            self._status_text.update()
            
        except Exception as e:
            self._status_text.value = f"保存失败: {str(e)}"
            self._status_text.color = Colors.ERROR
            self._status_text.update()
        finally:
            self._save_button.set_loading(False)
    
    @property
    def control(self) -> ft.Container:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)
