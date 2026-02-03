"""
媒体下载器

用于下载帖子中的图片、视频、语音等媒体文件。
"""
import asyncio
import os
import hashlib
import logging
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urlparse, unquote

try:
    import aiohttp
    import aiofiles
except ImportError:
    raise ImportError(
        "缺少依赖，请运行: pip install aiohttp aiofiles"
    )


logger = logging.getLogger(__name__)


# 常用的媒体文件扩展名
EXTENSION_MAP = {
    # 图片
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/bmp": "bmp",
    # 视频
    "video/mp4": "mp4",
    "video/webm": "webm",
    # 音频
    "audio/mpeg": "mp3",
    "audio/amr": "amr",
    "audio/ogg": "ogg",
}


class MediaDownloader:
    """
    媒体文件下载器

    支持并发下载图片、视频、语音等媒体文件。
    """

    def __init__(
        self,
        max_concurrent: int = 5,
        timeout: float = 30.0,
        retry: int = 3,
    ):
        """
        初始化下载器

        Args:
            max_concurrent: 最大并发下载数
            timeout: 下载超时时间（秒）
            retry: 失败重试次数
        """
        self.max_concurrent = max_concurrent
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.retry = retry
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "MediaDownloader":
        """异步上下文管理器入口"""
        self._session = aiohttp.ClientSession(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._session:
            await self._session.close()
            self._session = None

    def _get_extension_from_url(self, url: str) -> str:
        """
        从 URL 中提取文件扩展名

        Args:
            url: 文件 URL

        Returns:
            文件扩展名（不含点）
        """
        parsed = urlparse(url)
        path = unquote(parsed.path)
        ext = os.path.splitext(path)[1].lower()
        if ext:
            return ext.lstrip(".")
        return ""

    def _get_extension_from_content_type(self, content_type: str) -> str:
        """
        从 Content-Type 头中提取文件扩展名

        Args:
            content_type: HTTP Content-Type 头

        Returns:
            文件扩展名（不含点）
        """
        # 去除参数部分，如 "image/jpeg; charset=utf-8"
        mime_type = content_type.split(";")[0].strip().lower()
        return EXTENSION_MAP.get(mime_type, "")

    async def download_file(
        self,
        url: str,
        save_dir: str | Path,
        filename: str,
        fallback_ext: str = "",
    ) -> Tuple[str, bool]:
        """
        下载单个文件

        Args:
            url: 文件 URL
            save_dir: 保存目录
            filename: 文件名（不含扩展名）
            fallback_ext: 默认扩展名（无法从 URL 或响应头获取时使用）

        Returns:
            (完整文件名, 是否成功)
        """
        if not url:
            logger.warning(f"空 URL，跳过下载: {filename}")
            return f"{filename}.{fallback_ext}" if fallback_ext else filename, False

        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)

        async with self._semaphore:
            for attempt in range(1, self.retry + 1):
                # 检查是否已被取消或事件循环已关闭
                try:
                    # 检查当前任务是否被取消
                    current_task = asyncio.current_task()
                    if current_task and current_task.cancelled():
                        return f"{filename}.{fallback_ext}" if fallback_ext else filename, False
                except RuntimeError:
                    # 事件循环已关闭，直接返回
                    return f"{filename}.{fallback_ext}" if fallback_ext else filename, False

                try:
                    return await self._do_download(
                        url, save_dir, filename, fallback_ext
                    )
                except asyncio.CancelledError:
                    # 任务被取消，不重试，直接返回
                    logger.debug(f"下载被取消: {url}")
                    return f"{filename}.{fallback_ext}" if fallback_ext else filename, False
                except asyncio.TimeoutError:
                    logger.warning(
                        f"下载超时 (第 {attempt}/{self.retry} 次): {url}"
                    )
                except aiohttp.ClientError as e:
                    logger.warning(
                        f"下载错误 (第 {attempt}/{self.retry} 次): {url} - {e}"
                    )
                except RuntimeError as e:
                    # 捕获 "cannot schedule new futures after shutdown" 错误
                    if "shutdown" in str(e).lower() or "closed" in str(e).lower():
                        logger.debug(f"下载器已关闭，跳过: {url}")
                        return f"{filename}.{fallback_ext}" if fallback_ext else filename, False
                    logger.error(
                        f"下载失败 (第 {attempt}/{self.retry} 次): {url} - {e}"
                    )
                except Exception as e:
                    logger.error(
                        f"下载失败 (第 {attempt}/{self.retry} 次): {url} - {e}"
                    )

                if attempt < self.retry:
                    try:
                        await asyncio.sleep(0.5 * attempt)
                    except (asyncio.CancelledError, RuntimeError):
                        # 在等待期间被取消或事件循环关闭
                        return f"{filename}.{fallback_ext}" if fallback_ext else filename, False

        # 所有重试都失败了
        full_filename = f"{filename}.{fallback_ext}" if fallback_ext else filename
        return full_filename, False

    async def _do_download(
        self,
        url: str,
        save_dir: Path,
        filename: str,
        fallback_ext: str,
    ) -> Tuple[str, bool]:
        """
        执行实际的下载操作

        Args:
            url: 文件 URL
            save_dir: 保存目录
            filename: 文件名（不含扩展名）
            fallback_ext: 默认扩展名

        Returns:
            (完整文件名, 是否成功)
        """
        session = self._session or aiohttp.ClientSession(timeout=self.timeout)
        own_session = self._session is None

        try:
            async with session.get(url) as response:
                if response.status != 200:
                    raise aiohttp.ClientError(
                        f"HTTP {response.status}: {response.reason}"
                    )

                # 确定文件扩展名
                ext = self._get_extension_from_url(url)
                if not ext:
                    content_type = response.headers.get("Content-Type", "")
                    ext = self._get_extension_from_content_type(content_type)
                if not ext:
                    ext = fallback_ext

                full_filename = f"{filename}.{ext}" if ext else filename
                file_path = save_dir / full_filename

                # 如果文件已存在，跳过下载
                if file_path.exists():
                    logger.debug(f"文件已存在，跳过: {full_filename}")
                    return full_filename, True

                # 下载并保存
                content = await response.read()
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(content)

                logger.debug(f"下载成功: {full_filename}")
                return full_filename, True

        finally:
            if own_session:
                await session.close()

    async def download_batch(
        self,
        tasks: list[Tuple[str, str | Path, str, str]],
    ) -> list[Tuple[str, bool]]:
        """
        批量下载文件

        Args:
            tasks: 下载任务列表，每个任务为 (url, save_dir, filename, fallback_ext)

        Returns:
            结果列表，每个结果为 (完整文件名, 是否成功)
        """
        coros = [
            self.download_file(url, save_dir, filename, ext)
            for url, save_dir, filename, ext in tasks
        ]
        return await asyncio.gather(*coros)


class AssetManager:
    """
    资产管理器

    管理帖子的媒体资产目录结构，与 TiebaReader 兼容：
    - post_assets/images/
    - post_assets/videos/
    - post_assets/voices/
    - user_avatar/
    - forum_avatar/
    """

    def __init__(self, base_dir: str | Path):
        """
        初始化资产管理器

        Args:
            base_dir: 帖子数据的基础目录
        """
        self.base_dir = Path(base_dir)

        # 创建目录结构
        self.post_assets_dir = self.base_dir / "post_assets"
        self.images_dir = self.post_assets_dir / "images"
        self.videos_dir = self.post_assets_dir / "videos"
        self.voices_dir = self.post_assets_dir / "voices"
        self.user_avatar_dir = self.base_dir / "user_avatar"
        self.forum_avatar_dir = self.base_dir / "forum_avatar"

    def ensure_dirs(self) -> None:
        """确保所有目录存在"""
        for dir_path in [
            self.images_dir,
            self.videos_dir,
            self.voices_dir,
            self.user_avatar_dir,
            self.forum_avatar_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def get_image_filename(self, pid: int, index: int, hash_val: str = "") -> str:
        """
        生成图片文件名

        Args:
            pid: 帖子 ID
            index: 图片在帖子中的索引
            hash_val: 图片哈希值

        Returns:
            文件名（不含扩展名）
        """
        if hash_val:
            return f"p_{pid}_{index}_{hash_val[:8]}"
        return f"p_{pid}_{index}"

    def get_video_filename(self, pid: int, index: int) -> str:
        """
        生成视频文件名

        Args:
            pid: 帖子 ID
            index: 视频在帖子中的索引

        Returns:
            文件名（不含扩展名）
        """
        return f"v_{pid}_{index}"

    def get_voice_filename(self, pid: int, index: int, md5: str = "") -> str:
        """
        生成语音文件名

        Args:
            pid: 帖子 ID
            index: 语音在帖子中的索引
            md5: 语音文件的 MD5

        Returns:
            文件名（不含扩展名）
        """
        if md5:
            return f"a_{pid}_{index}_{md5[:8]}"
        return f"a_{pid}_{index}"

    def get_user_avatar_filename(self, portrait: str) -> str:
        """
        生成用户头像文件名

        Args:
            portrait: 用户 portrait

        Returns:
            文件名（不含扩展名）
        """
        # 使用 portrait 的 MD5 作为文件名，避免特殊字符问题
        return hashlib.md5(portrait.encode()).hexdigest()

    def get_forum_avatar_filename(self, forum_id: int, avatar_type: str = "small") -> str:
        """
        生成贴吧头像文件名

        Args:
            forum_id: 贴吧 ID
            avatar_type: 头像类型 ("small" 或 "origin")

        Returns:
            文件名（不含扩展名）
        """
        return f"forum_{forum_id}_{avatar_type}"


class TiebaVoiceAPI:
    """贴吧语音 API"""

    @staticmethod
    def get_voice_url(md5: str) -> str:
        """
        获取语音文件的下载 URL

        Args:
            md5: 语音文件的 MD5 值

        Returns:
            语音文件 URL
        """
        return f"https://tiebac.baidu.com/c/p/voice?voice_md5={md5}&play_from=pb_voice_play"


__all__ = [
    "MediaDownloader",
    "AssetManager",
    "TiebaVoiceAPI",
]
