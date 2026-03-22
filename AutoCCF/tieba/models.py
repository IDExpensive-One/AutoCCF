"""
贴吧数据模型

定义与 TiebaReader 兼容的数据结构，包括：
- 内容片段类型（ContentFragType）
- 帖子实体（PostEntity）
- 用户实体（UserEntity）
- 主题帖信息（ThreadInfo）
- 贴吧信息（ForumInfo）
"""
from dataclasses import dataclass, field, asdict
from enum import IntEnum, auto
from pathlib import Path
from typing import Optional, Any
import json
import time as _time


# =============================================================================
# 内容片段类型
# =============================================================================


class ContentFragType(IntEnum):
    """
    内容片段类型枚举

    与 TiebaReader 兼容的类型定义：
    - TEXT = 1: 纯文本
    - EMOJI = 2: 表情
    - IMAGE = 3: 图片
    - AT = 4: @用户
    - LINK = 5: 链接
    - TIEBAPLUS = 6: 贴吧Plus广告
    - VIDEO = 7: 视频
    - VOICE = 8: 语音
    - SCRAPE_ERROR = -1: 爬取错误标记
    """

    TEXT = auto()  # 1
    EMOJI = auto()  # 2
    IMAGE = auto()  # 3
    AT = auto()  # 4
    LINK = auto()  # 5
    TIEBAPLUS = auto()  # 6
    VIDEO = auto()  # 7
    VOICE = auto()  # 8

    SCRAPE_ERROR = -1


# =============================================================================
# 内容片段数据类
# =============================================================================


@dataclass
class ContentFrag:
    """内容片段基类"""

    type: int = 0  # 默认值，子类通过 __post_init__ 设置正确的类型

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class FragScrapeError(ContentFrag):
    """
    爬取错误标记

    这是一个特殊的片段，用于标记爬取过程中出现错误的内容块。
    """

    error_frag_type: int = 0
    error_frag_name: str = ""

    def __post_init__(self):
        self.type = ContentFragType.SCRAPE_ERROR


@dataclass
class FragText(ContentFrag):
    """
    文本片段

    JSON 格式: {"type": 1, "text": "文本内容"}
    """

    text: str = ""

    def __post_init__(self):
        self.type = ContentFragType.TEXT


@dataclass
class FragEmoji(ContentFrag):
    """
    表情片段

    JSON 格式: {"type": 2, "id": "image_emoticon25", "desc": "滑稽"}
    """

    id: str = ""
    desc: str = ""

    def __post_init__(self):
        self.type = ContentFragType.EMOJI


@dataclass
class FragImage(ContentFrag):
    """
    图片片段

    JSON 格式: {
        "type": 3,
        "filename": "p_123_0_xxx.jpg",
        "tb_origin_src": "https://...",
        "origin_size": 0,
        "show_width": 800,
        "show_height": 600,
        "hash": "abc123"
    }
    """

    filename: str = ""
    tb_origin_src: str = ""  # 贴吧原图链接
    origin_size: int = 0  # 原始大小（通常为0）
    show_width: int = 0
    show_height: int = 0
    hash: str = ""

    def __post_init__(self):
        self.type = ContentFragType.IMAGE


@dataclass
class FragAt(ContentFrag):
    """
    @用户片段

    JSON 格式: {"type": 4, "text": "@用户名", "user_id": 12345}
    """

    text: str = ""
    user_id: int = 0

    def __post_init__(self):
        self.type = ContentFragType.AT


@dataclass
class FragLink(ContentFrag):
    """
    链接片段

    JSON 格式: {"type": 5, "text": "显示文本", "title": "标题", "raw_url": "https://..."}
    """

    text: str = ""
    title: str = ""
    raw_url: str = ""

    def __post_init__(self):
        self.type = ContentFragType.LINK


@dataclass
class FragTiebaPlus(ContentFrag):
    """
    贴吧Plus广告片段

    JSON 格式: {"type": 6, "text": "广告描述", "url": "https://..."}
    """

    text: str = ""
    url: str = ""

    def __post_init__(self):
        self.type = ContentFragType.TIEBAPLUS


@dataclass
class FragVideo(ContentFrag):
    """
    视频片段

    JSON 格式: {
        "type": 7,
        "filename": "v_xxx.mp4",
        "cover_filename": "v_xxx_cover.jpg",
        "duration": 120,
        "width": 1920,
        "height": 1080,
        "view_num": 1000,
        "tb_origin_src": "https://...",
        "tb_origin_cover_src": "https://..."
    }
    """

    filename: str = ""
    cover_filename: str = ""
    duration: int = 0
    width: int = 0
    height: int = 0
    view_num: int = 0
    tb_origin_src: str = ""
    tb_origin_cover_src: str = ""

    def __post_init__(self):
        self.type = ContentFragType.VIDEO


@dataclass
class FragVoice(ContentFrag):
    """
    语音片段

    JSON 格式: {
        "type": 8,
        "filename": "a_xxx.mp3",
        "md5": "abc123",
        "duration": 30,
        "tb_origin_src": "https://..."
    }
    """

    filename: str = ""
    md5: str = ""
    duration: int = 0
    tb_origin_src: str = ""

    def __post_init__(self):
        self.type = ContentFragType.VOICE


# =============================================================================
# 用户状态和实体
# =============================================================================


class UserStatus(IntEnum):
    """用户状态"""

    ACTIVE = 0  # 正常
    DEACTIVATED = auto()  # 注销


@dataclass
class UserEntity:
    """
    用户实体

    与 TiebaReader content.db 的 user 表兼容。
    """

    id: int  # user_id
    portrait: Optional[str] = None  # portrait 标识
    username: Optional[str] = None  # 用户名
    nickname: str = ""  # 昵称 (nick_name_new > nickname_old)
    tieba_uid: Optional[int] = None  # 贴吧 UID

    avatar: Optional[str] = None  # 头像文件名
    glevel: int = 0  # 成长等级
    gender: int = 0  # 性别: 0=未知, 1=男, 2=女
    ip: str = ""  # IP 属地
    is_vip: bool = False  # 是否贵族
    is_god: bool = False  # 是否大神
    age: float = 0.0  # 吧龄
    sign: str = ""  # 个性签名
    post_num: int = 0  # 发帖数
    agree_num: int = 0  # 获赞数
    fan_num: int = 0  # 粉丝数
    follow_num: int = 0  # 关注数
    forum_num: int = 0  # 关注的贴吧数

    # 吧相关
    level: int = 0  # 在当前吧的等级
    is_bawu: bool = False  # 是否吧务

    status: int = UserStatus.ACTIVE  # 用户状态
    completed: int = 0  # 是否已完成信息抓取 (0|1)
    scrape_time: int = 0  # 最近一次抓取时间戳

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_db_tuple(self) -> tuple:
        """
        转换为数据库插入元组

        Returns:
            适用于 SQLite INSERT 的元组
        """
        return (
            self.id,
            self.portrait,
            self.username,
            self.nickname,
            self.tieba_uid,
            self.avatar,
            self.glevel,
            self.gender,
            self.ip,
            int(self.is_vip),
            int(self.is_god),
            self.age,
            self.sign,
            self.post_num,
            self.agree_num,
            self.fan_num,
            self.follow_num,
            self.forum_num,
            self.level,
            int(self.is_bawu),
            self.status,
            self.completed,
            self.scrape_time,
        )


# =============================================================================
# 帖子实体
# =============================================================================


@dataclass
class PostEntity:
    """
    帖子实体

    与 TiebaReader content.db 的 post 表兼容。
    """

    id: int  # pid (帖子ID)
    contents: str  # JSON 格式的内容片段列表
    floor: int  # 楼层（楼和楼中楼使用相同的楼层号）
    user_id: int  # 发帖用户 ID
    agree: int = 0  # 点赞数
    disagree: int = 0  # 点踩数
    create_time: int = 0  # 创建时间戳
    is_thread_author: bool = False  # 是否楼主
    sign: str = ""  # 小尾巴（楼独有）
    reply_num: int = 0  # 回复数（楼独有）
    parent_id: int = 0  # 父帖子 ID（楼中楼独有，0=主楼）
    reply_to_id: int = 0  # 回复的用户 ID（楼中楼独有）
    scrape_batch_id: int = 0  # 爬取批次 ID

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    def to_db_tuple(self) -> tuple:
        """
        转换为数据库插入元组

        Returns:
            适用于 SQLite INSERT 的元组
        """
        return (
            self.id,
            self.contents,
            self.floor,
            self.user_id,
            self.agree,
            self.disagree,
            self.create_time,
            int(self.is_thread_author),
            self.sign,
            self.reply_num,
            self.parent_id,
            self.reply_to_id,
            self.scrape_batch_id,
        )


# =============================================================================
# 投票信息
# =============================================================================


@dataclass
class VoteOption:
    """投票选项"""

    text: str = ""
    vote_num: int = 0

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class VoteInfo:
    """投票信息"""

    title: str = ""
    is_multi: bool = False  # 是否多选
    total_vote: int = 0  # 总票数
    total_user: int = 0  # 参与人数
    options: list[VoteOption] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result["options"] = [opt.to_dict() for opt in self.options]
        return result


# =============================================================================
# 主题帖信息
# =============================================================================


class ThreadStatus:
    """主题帖状态"""

    NORMAL = 0  # 正常
    DELETED = 1  # 已删除/已屏蔽


@dataclass
class ThreadInfo:
    """
    主题帖信息

    用于保存到 thread.json 文件。
    """

    id: int  # tid
    title: str  # 标题
    forum_id: int  # 贴吧 ID
    forum_name: str  # 贴吧名
    post_id: int  # 首楼 pid
    user_id: int  # 楼主 user_id
    type: int = 0  # 帖子类型
    is_share: bool = False  # 是否分享帖
    is_help: bool = False  # 是否求助帖
    vote_info: VoteInfo = field(default_factory=VoteInfo)  # 投票信息
    share_origin: int = 0  # 分享来源
    view_num: int = 0  # 浏览数
    reply_num: int = 0  # 回复数
    share_num: int = 0  # 分享数
    agree: int = 0  # 点赞数
    disagree: int = 0  # 点踩数
    create_time: int = 0  # 创建时间戳
    status: int = ThreadStatus.NORMAL  # 状态

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于保存到 JSON）"""
        result = asdict(self)
        if isinstance(self.vote_info, VoteInfo):
            result["vote_info"] = self.vote_info.to_dict()
        return result

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# =============================================================================
# 贴吧信息
# =============================================================================


@dataclass
class ForumInfo:
    """
    贴吧信息

    用于保存到 forum.json 文件。
    """

    id: int  # 贴吧 ID
    name: str  # 贴吧名称
    category: str = ""  # 分类
    subcategory: str = ""  # 子分类
    member_num: int = 0  # 成员数
    post_num: int = 0  # 帖子数
    thread_num: int = 0  # 主题数
    slogan: str = ""  # 标语
    small_avatar: str = ""  # 小头像文件名
    origin_avatar: str = ""  # 原始头像文件名

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于保存到 JSON）"""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# =============================================================================
# 爬取信息
# =============================================================================


@dataclass
class ScrapeRecord:
    """单次爬取记录（TiebaReader 兼容）"""

    scrape_time: int = 0
    scrape_config: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"scrape_time": self.scrape_time, "scrape_config": self.scrape_config}


@dataclass
class ScrapeInfo:
    """
    爬取信息（TiebaReader 兼容）

    保存到每个帖子存档根目录的 scrape_info.json。
    格式与 TiebaReader / TiebaArchiver 完全一致。
    """

    main_thread: int = 0
    create_time: int = 0
    update_time: int = 0
    scraper_version: str = ""
    scrape_records: list[ScrapeRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "main_thread": self.main_thread,
            "create_time": self.create_time,
            "update_time": self.update_time,
            "scraper_version": self.scraper_version,
            "scrape_records": [r.to_dict() for r in self.scrape_records],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    @classmethod
    def load_or_create(cls, path: Path, tid: int, version: str) -> "ScrapeInfo":
        """加载已有或创建新的 ScrapeInfo"""
        now = int(_time.time())
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return cls(
                    main_thread=data.get("main_thread", tid),
                    create_time=data.get("create_time", now),
                    update_time=now,
                    scraper_version=version,
                    scrape_records=[
                        ScrapeRecord(**r) for r in data.get("scrape_records", [])
                    ],
                )
            except Exception:
                pass
        return cls(
            main_thread=tid,
            create_time=now,
            update_time=now,
            scraper_version=version,
        )


@dataclass
class ScrapeBatch:
    """
    爬取批次信息

    用于记录每次爬取的配置和时间。
    """

    id: int = 0
    scraper_version: str = ""
    scrape_config: str = ""  # JSON 格式的配置
    scrape_time: int = 0

    def to_db_tuple(self) -> tuple:
        """转换为数据库插入元组"""
        return (self.scraper_version, self.scrape_config, self.scrape_time)


# =============================================================================
# 辅助函数
# =============================================================================


def contents_to_json(frags: list[ContentFrag]) -> str:
    """
    将内容片段列表转换为 JSON 字符串

    Args:
        frags: 内容片段列表

    Returns:
        JSON 字符串
    """
    return json.dumps([f.to_dict() for f in frags], ensure_ascii=False)


def json_to_contents(json_str: str) -> list[dict[str, Any]]:
    """
    将 JSON 字符串解析为内容片段字典列表

    Args:
        json_str: JSON 字符串

    Returns:
        内容片段字典列表
    """
    return json.loads(json_str)


__all__ = [
    # 枚举
    "ContentFragType",
    "UserStatus",
    "ThreadStatus",
    # 内容片段
    "ContentFrag",
    "FragText",
    "FragEmoji",
    "FragImage",
    "FragAt",
    "FragLink",
    "FragTiebaPlus",
    "FragVideo",
    "FragVoice",
    "FragScrapeError",
    # 实体
    "PostEntity",
    "UserEntity",
    "ThreadInfo",
    "ForumInfo",
    "VoteInfo",
    "VoteOption",
    "ScrapeRecord",
    "ScrapeInfo",
    "ScrapeBatch",
    # 辅助函数
    "contents_to_json",
    "json_to_contents",
]
