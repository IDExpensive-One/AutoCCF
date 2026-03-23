"""
数据解析器
将 aiotieba 返回的数据结构转换为统一的 Post 对象
"""
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass
class Post:
    """帖子数据结构"""
    id: int  # 序号
    tid: int  # 主题帖 ID
    pid: int  # 回复 ID
    title: str  # 标题（主题帖有，回复为空）
    content: str  # 文本内容
    forum: str  # 贴吧名
    href: str  # 帖子链接
    fid: int = 0  # 贴吧 ID
    create_time: int = 0  # 创建时间戳
    is_comment: bool = False  # 是否楼中楼
    is_thread: bool = False  # 是否为用户发的主题帖

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @staticmethod
    def build_href(tid: int, pid: int = 0) -> str:
        """构建帖子链接"""
        if pid:
            return f"https://tieba.baidu.com/p/{tid}?pid={pid}"
        return f"https://tieba.baidu.com/p/{tid}"


class PostParser:
    """帖子数据解析器"""

    @staticmethod
    def from_user_thread(uthread: Any, post_id: int = 0) -> Post:
        """
        从 aiotieba UserThread 对象创建 Post

        Args:
            uthread: aiotieba 的 UserThread 对象
            post_id: 序号

        Returns:
            Post 对象
        """
        tid = uthread.tid
        pid = uthread.pid
        return Post(
            id=post_id,
            tid=tid,
            pid=pid,
            title=uthread.title,
            content=uthread.text,
            forum=uthread.fname,
            href=Post.build_href(tid, pid),
            fid=uthread.fid,
            create_time=uthread.create_time,
            is_comment=False,
            is_thread=True,
        )

    @staticmethod
    def from_user_post(upost: Any, post_id: int = 0) -> Post:
        """
        从 aiotieba UserPost 对象创建 Post

        Args:
            upost: aiotieba 的 UserPost 对象
            post_id: 序号

        Returns:
            Post 对象
        """
        tid = upost.tid
        pid = upost.pid
        return Post(
            id=post_id,
            tid=tid,
            pid=pid,
            title="",  # 回复没有标题
            content=upost.text,
            forum="",  # 需要后续解析
            href=Post.build_href(tid, pid),
            fid=upost.fid,
            create_time=upost.create_time,
            is_comment=upost.is_comment,
            is_thread=False,
        )

    @staticmethod
    def from_anova_post(raw: Dict[str, Any], post_id: int = 0) -> Post:
        """
        从 tb.anova.me 的帖子字典创建 Post

        tb.anova.me 格式:
            {"title": "...", "content": "...", "href": "https://tieba.baidu.com/p/TID?pid=PID#PID"}

        Args:
            raw: tb.anova.me 返回的帖子字典
            post_id: 序号

        Returns:
            Post 对象
        """
        from AutoCCF.utils import extract_tid_from_href, extract_pid_from_href

        href = raw.get("href", "")
        title = raw.get("title", "")
        content = raw.get("content", "")

        tid = extract_tid_from_href(href) or 0
        pid = extract_pid_from_href(href) or 0

        # anova 始终返回帖子标题（即使是回复），无法可靠判断 is_thread
        # 默认为 False（回复），因为大多数用户发言是回复而非主题帖
        is_thread = False

        return Post(
            id=post_id,
            tid=tid,
            pid=pid,
            title=title,
            content=content,
            forum="",  # anova 不提供贴吧名
            href=href,
            fid=0,  # anova 不提供 fid
            create_time=0,  # anova 不提供时间戳
            is_comment=False,  # anova 不区分楼中楼
            is_thread=is_thread,
        )

    @staticmethod
    def from_dict(data: Dict[str, Any], post_id: int = 0) -> Post:
        """
        从字典创建 Post（用于加载已保存的数据）

        兼容新旧格式：
        - 新格式：直接有 tid, pid 等字段
        - 旧格式：从 href 中提取 tid

        Args:
            data: 帖子字典
            post_id: 序号（0 表示使用字典中的 id）

        Returns:
            Post 对象
        """
        from AutoCCF.utils import extract_tid_from_href, extract_pid_from_href

        tid = data.get("tid", 0)
        pid = data.get("pid", 0)
        href = data.get("href", "")

        # 旧格式兼容：从 href 中提取 tid/pid
        if not tid and href:
            tid = extract_tid_from_href(href) or 0
        if not pid and href:
            pid = extract_pid_from_href(href) or 0

        return Post(
            id=post_id or data.get("id", 0),
            tid=tid,
            pid=pid,
            title=data.get("title", ""),
            content=data.get("content", ""),
            forum=data.get("forum", ""),
            href=href or Post.build_href(tid, pid),
            fid=data.get("fid", 0),
            create_time=data.get("create_time", 0),
            is_comment=data.get("is_comment", False),
            is_thread=data.get("is_thread", False),
        )
