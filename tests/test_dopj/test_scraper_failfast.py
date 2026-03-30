"""DoPJ scraper fail-fast behavior tests."""
import asyncio

from DoPJ.scraper import ThreadScraper, ContentProcessor
from DoPJ.storage import ContentDatabase
from AutoCCF.tieba.downloader import AssetManager, MediaDownloader
from AutoCCF.tieba.client import TiebaClient


class _FakePage:
    def __init__(self, total_page: int):
        self.page = type("Page", (), {"total_page": total_page})
        self.thread = type("Thread", (), {"tid": 123, "author_id": 1})
        self.forum = type("Forum", (), {"fid": 1, "fname": "test"})

    def __iter__(self):
        return iter([])


class _FakeClient(TiebaClient):
    def __init__(self):
        pass

    async def get_posts(self, tid, pn=1, with_comments=True, only_thread_author=False):
        if pn == 1:
            return _FakePage(total_page=2)
        return None

    async def get_user_info(self, user_id, portrait=None):
        return None


class _CountingDownloader(MediaDownloader):
    def __init__(self):
        self.calls = 0

    async def download_file(self, url, save_dir, filename, fallback_ext=""):
        self.calls += 1
        return f"{filename}.{fallback_ext or 'bin'}", True


class _FragImage:
    def __init__(self):
        self.origin_src = "https://example.com/image.jpg"
        self.hash = "hash"


class _FragVideo:
    def __init__(self):
        self.src = "https://example.com/video.mp4"
        self.cover_src = "https://example.com/cover.jpg"


class _FragVoice:
    def __init__(self):
        self.md5 = "abcd1234"


class TestThreadScraperFailFast:
    """Test fail-fast behavior for incomplete producer-consumer fetch."""

    def test_do_scrape_fails_when_parallel_pages_missing(self, tmp_path, monkeypatch):
        """Test scraper returns failure when pages after page 1 are missing."""
        scraper = ThreadScraper(bduss="test", output_dir=tmp_path)
        scraper._client = _FakeClient()
        scraper._downloader = _CountingDownloader()

        async def noop(*args, **kwargs):
            return None

        async def fake_process_posts_page(*args, **kwargs):
            return set()

        monkeypatch.setattr(scraper, "_save_forum_info", noop)
        monkeypatch.setattr(scraper, "_save_thread_info", noop)
        monkeypatch.setattr(scraper, "_save_scrape_info", noop)
        monkeypatch.setattr(scraper, "_process_posts_page", fake_process_posts_page)
        monkeypatch.setattr(scraper, "_complete_user_info", noop)

        success, error = asyncio.run(scraper._do_scrape(123))

        assert success is False
        assert "缺失页" in error


class TestContentProcessorDownloadSwitch:
    """Test media download switch behavior."""

    def test_download_media_false_skips_downloader_calls(self, tmp_path):
        """Test disabling media download avoids all download invocations."""
        downloader = _CountingDownloader()
        thread_dir = tmp_path / "threads" / "321"
        thread_dir.mkdir(parents=True, exist_ok=True)

        asset_manager = AssetManager(thread_dir)
        asset_manager.ensure_dirs()

        with ContentDatabase(thread_dir / "content.db") as db:
            db.create_scrape_batch()
            processor = ContentProcessor(
                downloader,
                asset_manager,
                db,
                download_media=False,
            )

            asyncio.run(processor.process_frag(_FragImage(), pid=1, idx=0))
            asyncio.run(processor.process_frag(_FragVideo(), pid=2, idx=1))
            asyncio.run(processor.process_frag(_FragVoice(), pid=3, idx=2))

        assert downloader.calls == 0
