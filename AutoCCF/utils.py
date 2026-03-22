"""
AutoCCF 公共工具函数

提供项目通用的工具函数和类。
"""
import re
from pathlib import Path
from typing import Optional


# 预编译正则表达式
TID_PATTERN = re.compile(r"/p/(\d+)")
PID_PATTERN = re.compile(r"[?&]pid=(\d+)")


def extract_tid_from_href(href: str) -> Optional[int]:
    """
    从帖子链接中提取 tid

    Args:
        href: 帖子链接，如 https://tieba.baidu.com/p/5052759887?pid=xxx

    Returns:
        tid 或 None
    """
    if not href:
        return None
    match = TID_PATTERN.search(href)
    if match:
        return int(match.group(1))
    return None


def extract_pid_from_href(href: str) -> Optional[int]:
    """
    从帖子链接中提取 pid

    Args:
        href: 帖子链接

    Returns:
        pid 或 None
    """
    if not href:
        return None
    match = PID_PATTERN.search(href)
    if match:
        return int(match.group(1))
    return None


def is_valid_bduss(bduss: str) -> bool:
    """
    验证 BDUSS 是否有效

    Args:
        bduss: BDUSS 字符串

    Returns:
        是否有效
    """
    if not bduss or not isinstance(bduss, str):
        return False
    # BDUSS 通常长度超过 50 字符，且不是占位符
    return (
        len(bduss) > 50
        and not bduss.startswith("你的")
        and not bduss.startswith("请填入")
        and not bduss.startswith("your_")
    )


def truncate_string(s: str, max_length: int, suffix: str = "...") -> str:
    """
    截断字符串

    Args:
        s: 原字符串
        max_length: 最大长度（包含后缀）
        suffix: 截断后缀

    Returns:
        截断后的字符串
    """
    if len(s) <= max_length:
        return s
    return s[:max_length - len(suffix)] + suffix


class UserPaths:
    """
    用户数据目录路径管理

    统一管理用户数据的各种路径，避免重复拼接。
    APoU 数据存放在 apou/ 子目录，DoPJ 数据存放在 dopj/ 子目录。
    """

    def __init__(self, base_dir: str, username: str):
        """
        初始化路径管理器

        Args:
            base_dir: 基础目录（如 database）
            username: 用户名
        """
        self.base = Path(base_dir) / username

    # --- APoU 路径 ---

    @property
    def apou_dir(self) -> Path:
        """APoU 模块数据目录"""
        return self.base / "apou"

    @property
    def posts_file(self) -> Path:
        """APoU 输出的帖子列表文件"""
        return self.apou_dir / "posts.json"

    @property
    def raw_data_dir(self) -> Path:
        """APoU 原始数据目录"""
        return self.apou_dir / "raw_data"

    # --- DoPJ 路径 ---

    @property
    def dopj_dir(self) -> Path:
        """DoPJ 模块数据目录"""
        return self.base / "dopj"

    @property
    def progress_file(self) -> Path:
        """DoPJ 进度文件"""
        return self.dopj_dir / "progress.json"

    @property
    def index_file(self) -> Path:
        """DoPJ 索引文件"""
        return self.dopj_dir / "index.json"

    def thread_archive_dir(self, tid: int) -> Path:
        """TiebaReader 兼容的帖子存档根目录: dopj/{tid}/"""
        return self.dopj_dir / str(tid)

    def thread_data_dir(self, tid: int) -> Path:
        """帖子数据目录: dopj/{tid}/threads/{tid}/"""
        return self.thread_archive_dir(tid) / "threads" / str(tid)

    def thread_file(self, tid: int) -> Path:
        """帖子 JSON 文件"""
        return self.thread_data_dir(tid) / "thread.json"

    def scrape_info_file(self, tid: int) -> Path:
        """帖子的 scrape_info.json (TiebaReader 兼容)"""
        return self.thread_archive_dir(tid) / "scrape_info.json"

    # --- 旧版路径（向后兼容检测用） ---

    @property
    def legacy_posts_file(self) -> Path:
        """旧版 posts.json 位置"""
        return self.base / "posts.json"

    @property
    def legacy_index_file(self) -> Path:
        """旧版 index.json 位置"""
        return self.base / "index.json"

    @property
    def legacy_threads_dir(self) -> Path:
        """旧版 threads 目录"""
        return self.base / "threads"

    # --- 生命周期 ---

    def ensure_dirs(self) -> None:
        """确保所有必要目录存在"""
        self.apou_dir.mkdir(parents=True, exist_ok=True)
        self.dopj_dir.mkdir(parents=True, exist_ok=True)

    def ensure_apou(self) -> None:
        """确保 APoU 目录存在"""
        self.apou_dir.mkdir(parents=True, exist_ok=True)

    def ensure_dopj(self) -> None:
        """确保 DoPJ 目录存在"""
        self.dopj_dir.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        """检查用户目录是否存在"""
        return self.base.exists()

    def has_posts(self) -> bool:
        """检查是否有帖子列表（兼容新旧路径）"""
        return self.posts_file.exists() or self.legacy_posts_file.exists()

    def get_posts_file(self) -> Optional[Path]:
        """获取实际存在的 posts.json 路径（优先新路径）"""
        if self.posts_file.exists():
            return self.posts_file
        if self.legacy_posts_file.exists():
            return self.legacy_posts_file
        return None

    def has_threads(self) -> bool:
        """检查是否有帖子详情（兼容新旧路径）"""
        if self.dopj_dir.exists():
            return any(
                d.is_dir() and d.name.isdigit() for d in self.dopj_dir.iterdir()
            )
        if self.legacy_threads_dir.exists():
            return any(self.legacy_threads_dir.iterdir())
        return False

    def __str__(self) -> str:
        return str(self.base)

    def __repr__(self) -> str:
        return f"UserPaths({self.base})"
