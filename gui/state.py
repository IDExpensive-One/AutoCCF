"""
应用状态管理

集中管理 GUI 的响应式状态。
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import threading


class ViewName(str, Enum):
    """视图名称枚举"""
    HOME = "home"
    APOU = "apou"
    DOPJ = "dopj"
    USERS = "users"
    USER_DETAIL = "user_detail"
    SETTINGS = "settings"


class CrawlState(str, Enum):
    """爬取状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CrawlProgress:
    """爬取进度"""
    state: CrawlState = CrawlState.IDLE
    current: int = 0
    total: int = 0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def percentage(self) -> float:
        """进度百分比"""
        if self.total <= 0:
            return 0.0
        return min(100.0, (self.current / self.total) * 100)


@dataclass 
class APoUProgress(CrawlProgress):
    """APoU 爬取进度"""
    username: str = ""
    pages_done: int = 0
    posts_collected: int = 0
    current_title: str = ""
    incremental: bool = False


@dataclass
class DoPJProgress(CrawlProgress):
    """DoPJ 爬取进度"""
    username: str = ""
    success_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    current_tid: int = 0
    current_title: str = ""


class AppState:
    """
    应用全局状态
    
    线程安全的状态管理器，支持状态变更通知。
    """
    
    def __init__(self):
        self._lock = threading.Lock()
        self._listeners: List[Callable[[], None]] = []
        
        # 视图状态
        self._current_view: ViewName = ViewName.HOME
        self._selected_user: Optional[str] = None
        
        # 爬取状态
        self._apou_progress: Optional[APoUProgress] = None
        self._dopj_progress: Optional[DoPJProgress] = None
        
        # 缓存数据
        self._users_cache: List[Dict[str, Any]] = []
        self._users_cache_dirty: bool = True
    
    def add_listener(self, callback: Callable[[], None]) -> None:
        """添加状态变更监听器"""
        with self._lock:
            self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable[[], None]) -> None:
        """移除状态变更监听器"""
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)
    
    def _notify_listeners(self) -> None:
        """通知所有监听器"""
        listeners = []
        with self._lock:
            listeners = self._listeners.copy()
        for callback in listeners:
            try:
                callback()
            except Exception:
                pass
    
    # 视图状态
    @property
    def current_view(self) -> ViewName:
        with self._lock:
            return self._current_view
    
    @current_view.setter
    def current_view(self, value: ViewName) -> None:
        with self._lock:
            if self._current_view != value:
                self._current_view = value
        self._notify_listeners()
    
    @property
    def selected_user(self) -> Optional[str]:
        with self._lock:
            return self._selected_user
    
    @selected_user.setter
    def selected_user(self, value: Optional[str]) -> None:
        with self._lock:
            self._selected_user = value
        self._notify_listeners()
    
    # APoU 进度
    @property
    def apou_progress(self) -> Optional[APoUProgress]:
        with self._lock:
            return self._apou_progress
    
    @apou_progress.setter
    def apou_progress(self, value: Optional[APoUProgress]) -> None:
        with self._lock:
            self._apou_progress = value
        self._notify_listeners()
    
    def update_apou_progress(self, **kwargs) -> None:
        """更新 APoU 进度"""
        with self._lock:
            if self._apou_progress is None:
                self._apou_progress = APoUProgress()
            for key, value in kwargs.items():
                if hasattr(self._apou_progress, key):
                    setattr(self._apou_progress, key, value)
        self._notify_listeners()
    
    # DoPJ 进度
    @property
    def dopj_progress(self) -> Optional[DoPJProgress]:
        with self._lock:
            return self._dopj_progress
    
    @dopj_progress.setter
    def dopj_progress(self, value: Optional[DoPJProgress]) -> None:
        with self._lock:
            self._dopj_progress = value
        self._notify_listeners()
    
    def update_dopj_progress(self, **kwargs) -> None:
        """更新 DoPJ 进度"""
        with self._lock:
            if self._dopj_progress is None:
                self._dopj_progress = DoPJProgress()
            for key, value in kwargs.items():
                if hasattr(self._dopj_progress, key):
                    setattr(self._dopj_progress, key, value)
        self._notify_listeners()
    
    # 用户缓存
    @property
    def users(self) -> List[Dict[str, Any]]:
        with self._lock:
            return self._users_cache.copy()
    
    @users.setter
    def users(self, value: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._users_cache = value
            self._users_cache_dirty = False
        self._notify_listeners()
    
    def invalidate_users_cache(self) -> None:
        """标记用户缓存为脏"""
        with self._lock:
            self._users_cache_dirty = True
    
    @property
    def users_cache_dirty(self) -> bool:
        with self._lock:
            return self._users_cache_dirty
    
    # 爬取状态查询
    @property
    def is_apou_running(self) -> bool:
        with self._lock:
            return (
                self._apou_progress is not None 
                and self._apou_progress.state == CrawlState.RUNNING
            )
    
    @property
    def is_dopj_running(self) -> bool:
        with self._lock:
            return (
                self._dopj_progress is not None 
                and self._dopj_progress.state == CrawlState.RUNNING
            )
    
    @property
    def is_any_crawl_running(self) -> bool:
        return self.is_apou_running or self.is_dopj_running
    
    def reset_apou(self) -> None:
        """重置 APoU 状态"""
        with self._lock:
            self._apou_progress = None
        self._notify_listeners()
    
    def reset_dopj(self) -> None:
        """重置 DoPJ 状态"""
        with self._lock:
            self._dopj_progress = None
        self._notify_listeners()


# 全局状态实例
app_state = AppState()
