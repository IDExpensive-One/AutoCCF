"""
DoPJ 帖子爬取器

全新实现，不依赖 TiebaArchiver，直接使用 aiotieba 库。
"""
import asyncio
import time
import logging
from pathlib import Path
from typing import Optional, Any, Callable
from urllib.parse import urlparse, parse_qs, quote

# 添加父目录到路径以导入 autoccf
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from AutoCCF.tieba.client import TiebaClient
from AutoCCF.tieba.downloader import MediaDownloader, AssetManager, TiebaVoiceAPI
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
    ThreadInfo,
    ThreadStatus,
    ForumInfo,
    VoteInfo,
    VoteOption,
    ScrapeRecord,
    ScrapeInfo,
    contents_to_json,
)
from DoPJ.storage import ContentDatabase
from DoPJ.producer_consumer import ProducerConsumerCoordinator, ProducerConsumerConfig


logger = logging.getLogger(__name__)


class ContentProcessor:
    """
    内容处理器

    将 aiotieba 的内容片段转换为 TiebaReader 兼容格式。
    """

    def __init__(
        self,
        downloader: MediaDownloader,
        asset_manager: AssetManager,
        db: ContentDatabase,
        download_media: bool = True,
    ):
        """
        初始化内容处理器

        Args:
            downloader: 媒体下载器
            asset_manager: 资产管理器
            db: 内容数据库
            download_media: 是否下载媒体文件
        """
        self.downloader = downloader
        self.asset_manager = asset_manager
        self.db = db
        self.download_media = download_media

    async def process_contents(
        self,
        contents: list,
        pid: int,
    ) -> str:
        """
        处理内容片段列表

        Args:
            contents: aiotieba 返回的内容片段列表
            pid: 帖子 ID

        Returns:
            JSON 格式的内容片段字符串
        """
        frags = []
        for idx, frag in enumerate(contents):
            processed = await self.process_frag(frag, pid, idx)
            frags.append(processed)

        return contents_to_json(frags)

    async def process_frag(self, frag: Any, pid: int, idx: int) -> Any:
        """
        处理单个内容片段

        Args:
            frag: aiotieba 的内容片段
            pid: 帖子 ID
            idx: 片段索引

        Returns:
            转换后的内容片段
        """
        class_name = type(frag).__name__

        try:
            if "FragText" in class_name:
                return self._process_text(frag)
            elif "FragEmoji" in class_name:
                return self._process_emoji(frag)
            elif "FragImage" in class_name:
                return await self._process_image(frag, pid, idx)
            elif "FragAt" in class_name:
                return self._process_at(frag)
            elif "FragLink" in class_name:
                return self._process_link(frag)
            elif "FragTiebaPlus" in class_name:
                return self._process_tiebaplus(frag)
            elif "FragVideo" in class_name:
                return await self._process_video(frag, pid, idx)
            elif "FragVoice" in class_name:
                return await self._process_voice(frag, pid, idx)
            else:
                # FragUnknown 等未知类型，尝试提取文本
                text = getattr(frag, "text", "") or str(frag)
                if text and text != class_name:
                    logger.debug(f"未知片段类型 {class_name}，提取文本: {text[:50]}")
                else:
                    logger.debug(f"未知片段类型 {class_name}，跳过")
                    text = ""
                return FragText(text=text)

        except Exception as e:
            logger.error(f"处理片段失败 [{class_name}]: {e}")
            error_type = getattr(ContentFragType, class_name.replace("Frag", "").upper(), 0)
            return FragScrapeError(
                error_frag_type=error_type,
                error_frag_name=class_name.lower(),
            )

    def _process_text(self, frag) -> FragText:
        """处理文本片段"""
        return FragText(text=frag.text)

    def _process_emoji(self, frag) -> FragEmoji:
        """处理表情片段"""
        return FragEmoji(id=frag.id, desc=frag.desc)

    async def _process_image(self, frag, pid: int, idx: int) -> FragImage:
        """处理图片片段"""
        origin_src = str(frag.origin_src) if hasattr(frag, "origin_src") else ""
        if not self.download_media:
            return FragImage(
                filename="",
                tb_origin_src=origin_src,
                origin_size=getattr(frag, "origin_size", 0),
                show_width=getattr(frag, "show_width", 0),
                show_height=getattr(frag, "show_height", 0),
                hash=getattr(frag, "hash", ""),
            )

        if origin_src:
            filename_base = self.asset_manager.get_image_filename(
                pid, idx, getattr(frag, "hash", "")
            )
            filename, success = await self.downloader.download_file(
                origin_src,
                self.asset_manager.images_dir,
                filename_base,
                "jpg",
            )

            if success:
                # 记录原始链接
                self.db.insert_origin_src(
                    filename, ContentFragType.IMAGE, origin_src
                )
        else:
            filename = ""

        return FragImage(
            filename=filename,
            tb_origin_src=origin_src,
            origin_size=getattr(frag, "origin_size", 0),
            show_width=getattr(frag, "show_width", 0),
            show_height=getattr(frag, "show_height", 0),
            hash=getattr(frag, "hash", ""),
        )

    def _process_at(self, frag) -> FragAt:
        """处理 @用户 片段"""
        return FragAt(text=frag.text, user_id=frag.user_id)

    def _process_link(self, frag) -> FragLink:
        """处理链接片段"""
        raw_url = str(frag.raw_url) if hasattr(frag, "raw_url") else ""

        # 尝试提取贴吧外链的真实 URL
        extracted_url = self._extract_tieba_outbound_url(raw_url)
        if extracted_url:
            raw_url = extracted_url

        return FragLink(
            text=quote(raw_url, safe="") if raw_url else "",
            title=getattr(frag, "title", ""),
            raw_url=raw_url,
        )

    def _process_tiebaplus(self, frag) -> FragTiebaPlus:
        """处理贴吧Plus片段"""
        return FragTiebaPlus(
            text=getattr(frag, "text", ""),
            url=str(frag.url) if hasattr(frag, "url") else "",
        )

    async def _process_video(self, frag, pid: int, idx: int) -> FragVideo:
        """处理视频片段"""
        video_src = str(frag.src) if hasattr(frag, "src") else ""
        cover_src = str(frag.cover_src) if hasattr(frag, "cover_src") else ""

        video_filename = ""
        cover_filename = ""
        if not self.download_media:
            return FragVideo(
                filename=video_filename,
                cover_filename=cover_filename,
                duration=getattr(frag, "duration", 0),
                width=getattr(frag, "width", 0),
                height=getattr(frag, "height", 0),
                view_num=getattr(frag, "view_num", 0),
                tb_origin_src=video_src,
                tb_origin_cover_src=cover_src,
            )

        if video_src:
            filename_base = self.asset_manager.get_video_filename(pid, idx)
            video_filename, success = await self.downloader.download_file(
                video_src,
                self.asset_manager.videos_dir,
                filename_base,
                "mp4",
            )
            if success:
                self.db.insert_origin_src(
                    video_filename, ContentFragType.VIDEO, video_src
                )

        if cover_src:
            cover_base = f"{self.asset_manager.get_video_filename(pid, idx)}_cover"
            cover_filename, success = await self.downloader.download_file(
                cover_src,
                self.asset_manager.images_dir,
                cover_base,
                "jpg",
            )
            if success:
                self.db.insert_origin_src(
                    cover_filename, ContentFragType.IMAGE, cover_src
                )

        return FragVideo(
            filename=video_filename,
            cover_filename=cover_filename,
            duration=getattr(frag, "duration", 0),
            width=getattr(frag, "width", 0),
            height=getattr(frag, "height", 0),
            view_num=getattr(frag, "view_num", 0),
            tb_origin_src=video_src,
            tb_origin_cover_src=cover_src,
        )

    async def _process_voice(self, frag, pid: int, idx: int) -> FragVoice:
        """处理语音片段"""
        md5 = getattr(frag, "md5", "")
        voice_url = TiebaVoiceAPI.get_voice_url(md5) if md5 else ""

        voice_filename = ""
        if not self.download_media:
            return FragVoice(
                filename=voice_filename,
                md5=md5,
                duration=getattr(frag, "duration", 0),
                tb_origin_src=voice_url,
            )

        if voice_url:
            filename_base = self.asset_manager.get_voice_filename(pid, idx, md5)
            voice_filename, success = await self.downloader.download_file(
                voice_url,
                self.asset_manager.voices_dir,
                filename_base,
                "amr",
            )
            if success:
                self.db.insert_origin_src(
                    voice_filename, ContentFragType.VOICE, voice_url
                )

        return FragVoice(
            filename=voice_filename,
            md5=md5,
            duration=getattr(frag, "duration", 0),
            tb_origin_src=voice_url,
        )

    @staticmethod
    def _extract_tieba_outbound_url(raw_url: str) -> Optional[str]:
        """
        提取贴吧外链的真实 URL

        Args:
            raw_url: 贴吧包装的 URL

        Returns:
            真实 URL 或 None
        """
        try:
            parsed = urlparse(raw_url)
            if parsed.hostname == "tieba.baidu.com" and parsed.path == "/mo/q/checkurl":
                query_params = parse_qs(parsed.query)
                return query_params.get("url", [None])[0]
        except Exception:
            pass
        return None


class ThreadScraper:
    """
    帖子爬取器

    爬取单个帖子的所有内容并保存到 TiebaReader 兼容格式。
    """

    VERSION = "2.0.0"

    def __init__(
        self,
        bduss: str,
        output_dir: str | Path,
        download_media: bool = True,
        only_thread_author: bool = False,
        on_log: Optional[Callable[[str, str], None]] = None,
        stop_event: Optional[Any] = None,
    ):
        """
        初始化爬取器

        Args:
            bduss: 百度账号的 BDUSS cookie
            output_dir: 输出目录
            download_media: 是否下载媒体文件
            only_thread_author: 是否只爬取楼主回复
            on_log: 日志回调 (message, level)
            stop_event: 停止信号（threading.Event），被设置时中止爬取
        """
        self.bduss = bduss
        self.output_dir = Path(output_dir)
        self.download_media = download_media
        self.only_thread_author = only_thread_author
        self._on_log = on_log
        self._stop_event = stop_event

        self._client: Optional[TiebaClient] = None
        self._downloader: Optional[MediaDownloader] = None

    def _log(self, message: str, level: str = "info"):
        """记录日志并通过回调通知"""
        getattr(logger, level if level != "success" else "info")(message)
        if self._on_log:
            self._on_log(message, level)

    @property
    def _stopped(self) -> bool:
        """检查是否收到停止信号"""
        return self._stop_event is not None and self._stop_event.is_set()

    async def scrape(self, tid: int) -> tuple[bool, str]:
        """
        爬取帖子

        Args:
            tid: 帖子 ID

        Returns:
            (是否成功, 错误信息)
        """
        try:
            async with TiebaClient(self.bduss) as client:
                self._client = client

                async with MediaDownloader() as downloader:
                    self._downloader = downloader

                    return await self._do_scrape(tid)

        except Exception as e:
            logger.exception(f"爬取帖子 {tid} 失败")
            return False, str(e)

    async def _do_scrape(self, tid: int) -> tuple[bool, str]:
        """
        执行爬取

        Args:
            tid: 帖子 ID

        Returns:
            (是否成功, 错误信息)
        """
        if self._client is None or self._downloader is None:
            return False, "客户端未初始化"

        client = self._client
        downloader = self._downloader

        # 获取第一页，检查帖子是否存在
        posts_page = await client.get_posts(
            tid,
            pn=1,
            with_comments=True,
            only_thread_author=self.only_thread_author,
        )

        if posts_page is None:
            return False, "无法获取帖子，可能已被删除"

        self._log(f"帖子 {tid} 获取成功，开始处理")

        # 创建目录结构
        thread_dir = self.output_dir / "threads" / str(tid)
        thread_dir.mkdir(parents=True, exist_ok=True)

        # 初始化资产管理器
        asset_manager = AssetManager(thread_dir)
        asset_manager.ensure_dirs()

        # 初始化数据库
        db_path = thread_dir / "content.db"
        with ContentDatabase(db_path) as db:
            # 设置数据库信息
            db.set_db_info(tid)
            batch_id = db.create_scrape_batch()

            # 初始化内容处理器
            processor = ContentProcessor(
                downloader,
                asset_manager,
                db,
                download_media=self.download_media,
            )

            # 保存论坛和帖子信息
            await self._save_forum_info(posts_page.forum, thread_dir)
            await self._save_thread_info(posts_page.thread, thread_dir)

            # 爬取所有页
            total_pages = posts_page.page.total_page
            self._log(f"帖子 {tid} 共 {total_pages} 页")

            user_refs: set[tuple[int, Optional[str]]] = set()

            # 先处理第一页
            first_page_user_refs = await self._process_posts_page(
                posts_page,
                tid,
                1,
                total_pages,
                processor,
                db,
                asset_manager,
            )
            user_refs.update(first_page_user_refs)

            # 剩余页采用生产者-消费者并发拉取
            if total_pages > 1:
                coordinator = ProducerConsumerCoordinator(
                    ProducerConsumerConfig(
                        producer_count=min(3, total_pages - 1),
                        consumer_count=1,
                        queue_size=min(32, max(8, total_pages - 1)),
                    )
                )
                refs_lock = asyncio.Lock()

                async def fetch_page(page_number: int):
                    if self._stopped:
                        return None

                    self._log(f"[页 {page_number}/{total_pages}] 正在拉取...")
                    page = await client.get_posts(
                        tid,
                        pn=page_number,
                        with_comments=True,
                        only_thread_author=self.only_thread_author,
                    )
                    if page is None:
                        self._log(f"[页 {page_number}/{total_pages}] 获取失败，跳过", "warning")
                        return None
                    return page

                async def consume_page(page_number: int, page_data):
                    page_user_refs = await self._process_posts_page(
                        page_data,
                        tid,
                        page_number,
                        total_pages,
                        processor,
                        db,
                        asset_manager,
                    )
                    async with refs_lock:
                        user_refs.update(page_user_refs)

                pc_result = await coordinator.run(
                    page_numbers=range(2, total_pages + 1),
                    fetch_page=fetch_page,
                    process_page=consume_page,
                )

                for err in pc_result.errors:
                    self._log(f"并发抓取异常: {err}", "warning")

                if pc_result.errors:
                    return False, f"并发抓取失败: {pc_result.errors[0]}"

                expected_pages = set(range(2, total_pages + 1))
                processed_pages = set(pc_result.processed_pages)
                missing_pages = sorted(expected_pages - processed_pages)
                if missing_pages:
                    return False, f"并发抓取不完整，缺失页: {missing_pages[:5]}"

                if self._stopped:
                    self._log("收到停止信号，中止爬取", "warning")
                    return False, "用户中止"

            # 用户信息完善（对齐 TiebaArchiver）
            await self._complete_user_info(db, user_refs)

            db.commit()

        # 保存爬取信息
        await self._save_scrape_info(tid, posts_page.thread)

        return True, ""

    async def _process_posts_page(
        self,
        posts_page,
        tid: int,
        pn: int,
        total_pages: int,
        processor: ContentProcessor,
        db: ContentDatabase,
        asset_manager: AssetManager,
    ) -> set[tuple[int, Optional[str]]]:
        """
        处理一页帖子

        Args:
            posts_page: 帖子页数据
            tid: 帖子 ID
            pn: 页码
            total_pages: 总页数
            processor: 内容处理器
            db: 数据库
            asset_manager: 资产管理器
        """
        thread_author_id = posts_page.thread.author_id
        page_tag = f"[页 {pn}/{total_pages}]"

        # aiotieba 4.x: Posts 对象直接可迭代，不再有 .posts 属性
        posts_list = list(posts_page)
        total_posts = len(posts_list)

        page_user_refs: set[tuple[int, Optional[str]]] = set()

        for i, post in enumerate(posts_list, 1):
            reply_num = getattr(post, "reply_num", 0)
            self._log(
                f"  {page_tag} [{i}/{total_posts}] "
                f"#{post.floor}楼 ({len(post.contents)}个片段, {reply_num}条回复)"
            )
            # 处理用户
            user = self._aiotieba_user_to_entity(post.user)
            db.insert_user(user)
            page_user_refs.add((user.id, user.portrait))

            # 处理内容
            contents_json = await processor.process_contents(
                post.contents, post.pid
            )

            # 创建帖子实体
            post_entity = PostEntity(
                id=post.pid,
                contents=contents_json,
                floor=post.floor,
                user_id=post.user.user_id,
                agree=post.agree,
                disagree=post.disagree,
                create_time=post.create_time,
                is_thread_author=(post.user.user_id == thread_author_id),
                sign=getattr(post, "sign", "") or "",
                reply_num=reply_num,
                parent_id=0,  # 主楼
                reply_to_id=0,
                scrape_batch_id=db.current_batch_id,
            )
            db.insert_post(post_entity)

            # 处理楼中楼
            if reply_num > 0:
                comment_user_refs = await self._process_comments(
                    tid, post.pid, post.floor, reply_num,
                    thread_author_id, processor, db
                )
                page_user_refs.update(comment_user_refs)

        db.commit()
        self._log(f"  {page_tag} 完成，共 {total_posts} 条回复")
        return page_user_refs

    async def _process_comments(
        self,
        tid: int,
        pid: int,
        floor: int,
        reply_num: int,
        thread_author_id: int,
        processor: ContentProcessor,
        db: ContentDatabase,
    ) -> set[tuple[int, Optional[str]]]:
        """
        处理楼中楼评论（支持分页）

        Args:
            tid: 帖子 ID
            pid: 主楼 ID
            floor: 楼层号
            reply_num: 评论总数
            thread_author_id: 楼主用户 ID
            processor: 内容处理器
            db: 数据库
        """
        pn = 1
        processed_count = 0
        user_refs: set[tuple[int, Optional[str]]] = set()

        while processed_count < reply_num:
            if self._client is None:
                break

            comments_page = await self._client.get_comments(tid, pid, pn)
            if comments_page is None:
                logger.warning(f"无法获取楼中楼 [pid={pid}, pn={pn}]")
                break

            comments = list(comments_page)
            if not comments:
                break

            for comment in comments:
                # 处理评论用户
                comment_user = self._aiotieba_user_to_entity(comment.user)
                db.insert_user(comment_user)
                user_refs.add((comment_user.id, comment_user.portrait))

                # 处理评论内容
                comment_contents = await processor.process_contents(
                    comment.contents, comment.pid
                )

                # 创建评论实体
                comment_entity = PostEntity(
                    id=comment.pid,
                    contents=comment_contents,
                    floor=floor,  # 楼中楼使用父楼层号
                    user_id=comment.user.user_id,
                    agree=getattr(comment, "agree", 0),
                    disagree=getattr(comment, "disagree", 0),
                    create_time=comment.create_time,
                    is_thread_author=(comment.user.user_id == thread_author_id),
                    sign="",
                    reply_num=0,
                    parent_id=pid,  # 父帖子 ID
                    reply_to_id=getattr(comment, "reply_to_id", 0),
                    scrape_batch_id=db.current_batch_id,
                )
                db.insert_post(comment_entity)
                processed_count += 1

            # 检查是否有更多页
            if hasattr(comments_page, 'page') and comments_page.page.current_page >= comments_page.page.total_page:
                break
            if hasattr(comments_page, 'has_more') and not comments_page.has_more:
                break

            pn += 1

        return user_refs

    async def _save_forum_info(self, forum, thread_dir: Path):
        """保存贴吧信息"""
        forum_info = ForumInfo(
            id=forum.fid,
            name=forum.fname,
            category=getattr(forum, "category", ""),
            subcategory=getattr(forum, "subcategory", ""),
            member_num=getattr(forum, "member_num", 0),
            post_num=getattr(forum, "post_num", 0),
            thread_num=getattr(forum, "thread_num", 0),
            slogan=getattr(forum, "slogan", ""),
            small_avatar="",
            origin_avatar="",
        )

        forum_path = thread_dir / "forum.json"
        with open(forum_path, "w", encoding="utf-8") as f:
            f.write(forum_info.to_json())

    async def _save_thread_info(self, thread, thread_dir: Path):
        """保存帖子信息"""
        # 处理投票信息
        vote_info = VoteInfo()
        if hasattr(thread, "vote_info") and thread.vote_info:
            vi = thread.vote_info
            vote_info = VoteInfo(
                title=getattr(vi, "title", ""),
                is_multi=getattr(vi, "is_multi", False),
                total_vote=getattr(vi, "total_vote", 0),
                total_user=getattr(vi, "total_user", 0),
                options=[
                    VoteOption(text=opt.text, vote_num=opt.vote_num)
                    for opt in getattr(vi, "options", [])
                ],
            )

        thread_info = ThreadInfo(
            id=thread.tid,
            title=thread.title,
            forum_id=thread.fid,
            forum_name=getattr(thread, "fname", ""),
            post_id=getattr(thread, "pid", 0),
            user_id=thread.author_id,
            type=getattr(thread, "type", 0),
            is_share=getattr(thread, "is_share", False),
            is_help=getattr(thread, "is_help", False),
            vote_info=vote_info,
            share_origin=getattr(thread, "share_origin", 0),
            view_num=getattr(thread, "view_num", 0),
            reply_num=getattr(thread, "reply_num", 0),
            share_num=getattr(thread, "share_num", 0),
            agree=getattr(thread, "agree", 0),
            disagree=getattr(thread, "disagree", 0),
            create_time=getattr(thread, "create_time", 0),
            status=ThreadStatus.NORMAL,
        )

        thread_path = thread_dir / "thread.json"
        with open(thread_path, "w", encoding="utf-8") as f:
            f.write(thread_info.to_json())

    async def _save_scrape_info(self, tid: int, thread):
        """保存 TiebaReader 兼容的 scrape_info.json"""
        info_path = self.output_dir / "scrape_info.json"

        # 加载已有或创建新的
        info = ScrapeInfo.load_or_create(info_path, tid, self.VERSION)

        # 添加本次爬取记录
        info.scrape_records.append(ScrapeRecord(
            scrape_time=int(time.time()),
            scrape_config={},
        ))
        info.update_time = int(time.time())

        with open(info_path, "w", encoding="utf-8") as f:
            f.write(info.to_json())

    def _aiotieba_user_to_entity(self, user) -> UserEntity:
        """将 aiotieba 用户对象转换为 UserEntity"""
        return UserEntity(
            id=user.user_id,
            portrait=getattr(user, "portrait", None),
            username=getattr(user, "user_name", None),
            nickname=user.nick_name_new or getattr(user, "show_name", "") or "",
            tieba_uid=getattr(user, "tieba_uid", None),
            avatar=None,
            glevel=getattr(user, "glevel", 0),
            gender=getattr(user, "gender", 0),
            ip=getattr(user, "ip", ""),
            is_vip=getattr(user, "is_vip", False),
            is_god=getattr(user, "is_god", False),
            age=getattr(user, "tb_age", 0.0),
            sign=getattr(user, "sign", ""),
            post_num=0,
            agree_num=0,
            fan_num=0,
            follow_num=0,
            forum_num=0,
            level=getattr(user, "level", 0),
            is_bawu=getattr(user, "is_bawu", False),
            status=0,
            completed=0,
            scrape_time=int(time.time()),
        )

    def _aiotieba_user_info_to_entity(self, user_info) -> UserEntity:
        """将 aiotieba UserInfo 对象转换为完整 UserEntity。"""
        gender = getattr(user_info, "gender", 0)
        if not isinstance(gender, int) and hasattr(gender, "value"):
            gender = gender.value

        nickname = (
            getattr(user_info, "nick_name", "")
            or getattr(user_info, "nick_name_new", "")
            or getattr(user_info, "nick_name_old", "")
            or getattr(user_info, "user_name", "")
            or ""
        )

        return UserEntity(
            id=getattr(user_info, "user_id", 0),
            portrait=getattr(user_info, "portrait", None),
            username=getattr(user_info, "user_name", None),
            nickname=nickname,
            tieba_uid=getattr(user_info, "tieba_uid", None),
            avatar=None,
            glevel=getattr(user_info, "glevel", 0),
            gender=int(gender),
            ip=getattr(user_info, "ip", ""),
            is_vip=getattr(user_info, "is_vip", False),
            is_god=getattr(user_info, "is_god", False),
            age=getattr(user_info, "age", 0.0),
            sign=getattr(user_info, "sign", ""),
            post_num=getattr(user_info, "post_num", 0),
            agree_num=getattr(user_info, "agree_num", 0),
            fan_num=getattr(user_info, "fan_num", 0),
            follow_num=getattr(user_info, "follow_num", 0),
            forum_num=getattr(user_info, "forum_num", 0),
            level=0,
            is_bawu=False,
            status=int(getattr(user_info, "is_blocked", False)),
            completed=1,
            scrape_time=int(time.time()),
        )

    @staticmethod
    def _merge_user_entity(base: UserEntity, detail: UserEntity) -> UserEntity:
        """合并基础用户信息与详情信息。"""
        return UserEntity(
            id=base.id,
            portrait=detail.portrait or base.portrait,
            username=detail.username or base.username,
            nickname=detail.nickname or base.nickname,
            tieba_uid=detail.tieba_uid or base.tieba_uid,
            avatar=detail.avatar or base.avatar,
            glevel=detail.glevel or base.glevel,
            gender=detail.gender if detail.gender != 0 else base.gender,
            ip=detail.ip or base.ip,
            is_vip=detail.is_vip or base.is_vip,
            is_god=detail.is_god or base.is_god,
            age=detail.age if detail.age != 0 else base.age,
            sign=detail.sign or base.sign,
            post_num=detail.post_num or base.post_num,
            agree_num=detail.agree_num or base.agree_num,
            fan_num=detail.fan_num or base.fan_num,
            follow_num=detail.follow_num or base.follow_num,
            forum_num=detail.forum_num or base.forum_num,
            level=base.level,
            is_bawu=base.is_bawu,
            status=detail.status,
            completed=1,
            scrape_time=int(time.time()),
        )

    async def _complete_user_info(
        self,
        db: ContentDatabase,
        user_refs: set[tuple[int, Optional[str]]],
    ) -> None:
        """补全用户详情信息（用户统计等字段）。"""
        if not user_refs:
            return

        if self._client is None:
            return

        client = self._client

        self._log(f"开始完善用户信息，共 {len(user_refs)} 人")
        completed_count = 0

        for user_id, portrait in sorted(user_refs, key=lambda item: item[0]):
            if self._stopped:
                self._log("收到停止信号，中止用户信息完善", "warning")
                break

            if user_id <= 0 and not portrait:
                continue

            user_info = await client.get_user_info(user_id, portrait=portrait)
            if user_info is None or getattr(user_info, "user_id", 0) == 0:
                continue

            detail = self._aiotieba_user_info_to_entity(user_info)
            existing = db.get_user(detail.id)
            if existing is not None:
                merged = self._merge_user_entity(existing, detail)
            else:
                merged = detail

            db.insert_user(merged)
            completed_count += 1

        db.commit()
        self._log(f"用户信息完善完成: {completed_count}/{len(user_refs)}")


async def scrape_thread(
    tid: int,
    bduss: str,
    output_dir: str | Path,
    download_media: bool = True,
    only_thread_author: bool = False,
    on_log: Optional[Callable[[str, str], None]] = None,
    stop_event: Optional[Any] = None,
) -> tuple[bool, str]:
    """
    爬取帖子的便捷函数

    Args:
        tid: 帖子 ID
        bduss: BDUSS cookie
        output_dir: 输出目录
        download_media: 是否下载媒体
        only_thread_author: 是否只看楼主
        on_log: 日志回调 (message, level)
        stop_event: 停止信号（threading.Event）

    Returns:
        (是否成功, 错误信息)
    """
    scraper = ThreadScraper(
        bduss=bduss,
        output_dir=output_dir,
        download_media=download_media,
        only_thread_author=only_thread_author,
        on_log=on_log,
        stop_event=stop_event,
    )
    return await scraper.scrape(tid)


__all__ = [
    "ThreadScraper",
    "ContentProcessor",
    "scrape_thread",
]
