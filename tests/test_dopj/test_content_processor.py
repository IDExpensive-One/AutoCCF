"""DoPJ content processor media tests."""
import asyncio
import sqlite3

from AutoCCF.tieba.downloader import AssetManager, MediaDownloader
from DoPJ.scraper import ContentProcessor
from DoPJ.storage import ContentDatabase


class FragImage:
    """Mock aiotieba image fragment."""

    def __init__(self):
        self.origin_src = "https://example.com/image.jpg"
        self.hash = "img_hash"
        self.origin_size = 100
        self.show_width = 10
        self.show_height = 20


class FragVideo:
    """Mock aiotieba video fragment."""

    def __init__(self):
        self.src = "https://example.com/video.mp4"
        self.cover_src = "https://example.com/cover.jpg"
        self.duration = 10
        self.width = 100
        self.height = 200
        self.view_num = 5


class FragVoice:
    """Mock aiotieba voice fragment."""

    def __init__(self):
        self.md5 = "abcd1234"
        self.duration = 9


class FakeDownloader(MediaDownloader):
    """Fake media downloader for deterministic tests."""

    def __init__(self):
        pass

    async def download_file(self, url, save_dir, filename, fallback_ext=""):
        ext = fallback_ext or "bin"
        return f"{filename}.{ext}", True


class TestContentProcessorMedia:
    """Test media fragment processing and origin-src persistence."""

    def test_process_media_frags_persists_origin_src_records(self, tmp_path):
        """Test image/video/voice fragments persist media and origin mapping."""
        thread_dir = tmp_path / "threads" / "123"
        thread_dir.mkdir(parents=True, exist_ok=True)

        asset_manager = AssetManager(thread_dir)
        asset_manager.ensure_dirs()

        db_path = thread_dir / "content.db"
        with ContentDatabase(db_path) as db:
            db.create_scrape_batch()
            processor = ContentProcessor(FakeDownloader(), asset_manager, db)

            asyncio.run(processor.process_frag(FragImage(), pid=11, idx=0))
            asyncio.run(processor.process_frag(FragVideo(), pid=12, idx=1))
            asyncio.run(processor.process_frag(FragVoice(), pid=13, idx=2))
            db.commit()

        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                "SELECT content_frag_type, origin_src FROM tieba_origin_src ORDER BY id"
            ).fetchall()

        # image + video + video_cover(image) + voice
        assert len(rows) == 4
        origins = {row[1] for row in rows}
        assert "https://example.com/image.jpg" in origins
        assert "https://example.com/video.mp4" in origins
        assert "https://example.com/cover.jpg" in origins
        assert any("voice_md5=abcd1234" in origin for origin in origins)
