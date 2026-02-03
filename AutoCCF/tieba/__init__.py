"""
贴吧 API 封装模块

提供 aiotieba 客户端封装、数据模型和媒体下载器。
"""

from AutoCCF.tieba.models import (
    ContentFragType,
    FragText,
    FragEmoji,
    FragImage,
    FragAt,
    FragLink,
    FragTiebaPlus,
    FragVideo,
    FragVoice,
    FragScrapeError,
    PostEntity,
    UserEntity,
    UserStatus,
    ThreadInfo,
    ThreadStatus,
    ForumInfo,
    VoteInfo,
    VoteOption,
    ScrapeInfo,
    ScrapeBatch,
    contents_to_json,
    json_to_contents,
)

from AutoCCF.tieba.client import (
    TiebaClient,
    ClientConfig,
    AccountPool,
    create_client,
)

from AutoCCF.tieba.downloader import (
    MediaDownloader,
    AssetManager,
    TiebaVoiceAPI,
)

__all__ = [
    # 内容片段类型
    "ContentFragType",
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
    "UserStatus",
    "ThreadInfo",
    "ThreadStatus",
    "ForumInfo",
    "VoteInfo",
    "VoteOption",
    "ScrapeInfo",
    "ScrapeBatch",
    # 辅助函数
    "contents_to_json",
    "json_to_contents",
    # 客户端
    "TiebaClient",
    "ClientConfig",
    "AccountPool",
    "create_client",
    # 下载器
    "MediaDownloader",
    "AssetManager",
    "TiebaVoiceAPI",
]
