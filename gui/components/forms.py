"""
表单组件

包含文本输入、滑块、按钮等表单控件。
使用包装类模式（Wrapper Class Pattern）以兼容新版 Flet API。
"""
import flet as ft
from typing import Optional, Callable
from ..theme import Colors, Styles


class UsernameInput:
    """
    用户名输入框
    
    带验证和清空按钮的用户名输入组件。
    """
    
    def __init__(
        self,
        label: str = "用户名",
        hint_text: str = "请输入贴吧用户名",
        on_change: Optional[Callable[[str], None]] = None,
        on_submit: Optional[Callable[[str], None]] = None,
    ):
        self._label = label
        self._hint_text = hint_text
        self._on_change = on_change
        self._on_submit = on_submit
        self._control: Optional[ft.TextField] = None
        self._build()
    
    def _build(self):
        self._text_field = ft.TextField(
            label=self._label,
            hint_text=self._hint_text,
            border_color=Colors.BORDER,
            focused_border_color=Colors.PRIMARY,
            cursor_color=Colors.PRIMARY,
            text_style=ft.TextStyle(color=Colors.TEXT_PRIMARY),
            label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),
            hint_style=ft.TextStyle(color=Colors.TEXT_DISABLED),
            border_radius=Styles.BORDER_RADIUS_MD,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
            on_change=self._handle_change,
            on_submit=self._handle_submit,
            suffix=ft.IconButton(
                icon=ft.Icons.CLEAR,
                icon_color=Colors.TEXT_SECONDARY,
                icon_size=18,
                on_click=self._clear,
                visible=False,
            ),
        )
        self._control = self._text_field
    
    def _handle_change(self, e):
        value = e.control.value
        # 显示/隐藏清空按钮
        self._text_field.suffix.visible = bool(value)
        self._text_field.update()
        
        if self._on_change:
            self._on_change(value)
    
    def _handle_submit(self, e):
        if self._on_submit:
            self._on_submit(e.control.value)
    
    def _clear(self, e):
        self._text_field.value = ""
        self._text_field.suffix.visible = False
        self._text_field.update()
        if self._on_change:
            self._on_change("")
    
    @property
    def value(self) -> str:
        return self._text_field.value or ""
    
    @value.setter
    def value(self, val: str):
        self._text_field.value = val
        self._text_field.suffix.visible = bool(val)
        self._text_field.update()
    
    def set_error(self, message: Optional[str]):
        """设置错误提示"""
        self._text_field.error_text = message
        self._text_field.update()
    
    @property
    def control(self) -> ft.TextField:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)


class BDUSSInput:
    """
    BDUSS 输入框
    
    密码模式的 BDUSS 输入，带验证功能。
    """
    
    def __init__(
        self,
        label: str = "BDUSS",
        hint_text: str = "请输入 BDUSS Cookie",
        on_change: Optional[Callable[[str], None]] = None,
    ):
        self._label = label
        self._hint_text = hint_text
        self._on_change = on_change
        self._password_visible = False
        self._control: Optional[ft.TextField] = None
        self._build()
    
    def _build(self):
        self._text_field = ft.TextField(
            label=self._label,
            hint_text=self._hint_text,
            password=True,
            can_reveal_password=True,
            border_color=Colors.BORDER,
            focused_border_color=Colors.PRIMARY,
            cursor_color=Colors.PRIMARY,
            text_style=ft.TextStyle(color=Colors.TEXT_PRIMARY),
            label_style=ft.TextStyle(color=Colors.TEXT_SECONDARY),
            hint_style=ft.TextStyle(color=Colors.TEXT_DISABLED),
            border_radius=Styles.BORDER_RADIUS_MD,
            content_padding=ft.padding.symmetric(horizontal=16, vertical=12),
            on_change=self._handle_change,
        )
        self._control = self._text_field
    
    def _handle_change(self, e):
        if self._on_change:
            self._on_change(e.control.value)
    
    @property
    def value(self) -> str:
        return self._text_field.value or ""
    
    @value.setter
    def value(self, val: str):
        self._text_field.value = val
        self._text_field.update()
    
    def set_error(self, message: Optional[str]):
        """设置错误提示"""
        self._text_field.error_text = message
        self._text_field.update()
    
    def validate(self) -> bool:
        """验证 BDUSS 格式"""
        value = self.value.strip()
        if not value:
            self.set_error("BDUSS 不能为空")
            return False
        if len(value) < 50:
            self.set_error("BDUSS 格式不正确（太短）")
            return False
        if value.startswith("你的") or value.startswith("your"):
            self.set_error("请输入真实的 BDUSS")
            return False
        self.set_error(None)
        return True
    
    @property
    def control(self) -> ft.TextField:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)


class ConfigSlider:
    """
    配置滑块
    
    用于数值配置的滑块组件，显示当前值。
    """
    
    def __init__(
        self,
        label: str,
        min_value: float,
        max_value: float,
        value: float,
        step: float = 1.0,
        unit: str = "",
        on_change: Optional[Callable[[float], None]] = None,
    ):
        self._label = label
        self._min_value = min_value
        self._max_value = max_value
        self._value = value
        self._step = step
        self._unit = unit
        self._on_change = on_change
        self._control: Optional[ft.Column] = None
        self._build()
    
    def _build(self):
        self._value_text = ft.Text(
            self._format_value(self._value),
            size=14,
            color=Colors.PRIMARY,
            weight=ft.FontWeight.W_500,
        )
        
        self._slider = ft.Slider(
            min=self._min_value,
            max=self._max_value,
            value=self._value,
            divisions=int((self._max_value - self._min_value) / self._step),
            active_color=Colors.PRIMARY,
            inactive_color=Colors.SURFACE_VARIANT,
            on_change=self._handle_change,
        )
        
        self._control = ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            self._label,
                            size=14,
                            color=Colors.TEXT_PRIMARY,
                        ),
                        ft.Container(expand=True),
                        self._value_text,
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                self._slider,
                ft.Row(
                    controls=[
                        ft.Text(
                            self._format_value(self._min_value),
                            size=12,
                            color=Colors.TEXT_DISABLED,
                        ),
                        ft.Container(expand=True),
                        ft.Text(
                            self._format_value(self._max_value),
                            size=12,
                            color=Colors.TEXT_DISABLED,
                        ),
                    ],
                ),
            ],
            spacing=0,
        )
    
    def _format_value(self, val: float) -> str:
        if self._step >= 1:
            return f"{int(val)}{self._unit}"
        return f"{val:.1f}{self._unit}"
    
    def _handle_change(self, e):
        self._value = e.control.value
        self._value_text.value = self._format_value(self._value)
        self._value_text.update()
        
        if self._on_change:
            self._on_change(self._value)
    
    @property
    def value(self) -> float:
        return self._value
    
    @value.setter
    def value(self, val: float):
        self._value = val
        self._slider.value = val
        self._value_text.value = self._format_value(val)
        self._control.update()
    
    @property
    def control(self) -> ft.Column:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)


class ActionButton:
    """
    动作按钮
    
    带加载状态的主要动作按钮。
    """
    
    def __init__(
        self,
        text: str,
        icon: Optional[str] = None,
        on_click: Optional[Callable[[], None]] = None,
        primary: bool = True,
        disabled: bool = False,
    ):
        self._text = text
        self._icon = icon
        self._on_click = on_click
        self._primary = primary
        self._disabled = disabled
        self._loading = False
        self._control: Optional[ft.ElevatedButton] = None
        self._visible = True
        self._build()
    
    def _build(self):
        bgcolor = Colors.PRIMARY if self._primary else Colors.SURFACE_VARIANT
        text_color = Colors.TEXT_PRIMARY
        
        button_content = ft.Row(
            controls=[],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=8,
        )
        
        if self._icon:
            button_content.controls.append(
                ft.Icon(self._icon, size=18, color=text_color)
            )
        
        self._text_control = ft.Text(
            self._text,
            size=14,
            color=text_color,
            weight=ft.FontWeight.W_500,
        )
        button_content.controls.append(self._text_control)
        
        self._loading_indicator = ft.ProgressRing(
            width=16,
            height=16,
            stroke_width=2,
            color=text_color,
            visible=False,
        )
        button_content.controls.append(self._loading_indicator)
        
        self._button = ft.ElevatedButton(
            content=button_content,
            bgcolor=bgcolor,
            color=text_color,
            on_click=self._handle_click,
            disabled=self._disabled,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=Styles.BORDER_RADIUS_MD),
                padding=ft.padding.symmetric(horizontal=24, vertical=12),
            ),
        )
        
        self._control = self._button
    
    def _handle_click(self, e):
        if self._loading:
            return
        if self._on_click:
            self._on_click()
    
    def set_loading(self, loading: bool):
        """设置加载状态"""
        self._loading = loading
        self._loading_indicator.visible = loading
        self._button.disabled = loading or self._disabled
        if loading:
            self._text_control.value = "处理中..."
        else:
            self._text_control.value = self._text
        self._control.update()
    
    def set_disabled(self, disabled: bool):
        """设置禁用状态"""
        self._disabled = disabled
        self._button.disabled = disabled or self._loading
        self._control.update()
    
    def set_text(self, text: str):
        """设置按钮文本"""
        self._text = text
        if not self._loading:
            self._text_control.value = text
            self._control.update()
    
    @property
    def visible(self) -> bool:
        return self._visible
    
    @visible.setter
    def visible(self, val: bool):
        self._visible = val
        self._control.visible = val
    
    @property
    def control(self) -> ft.ElevatedButton:
        """返回底层控件"""
        return self._control
    
    def __getattr__(self, name):
        """代理属性访问到底层控件"""
        return getattr(self._control, name)
