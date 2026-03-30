"""DoPJ scraper integration tests."""
import asyncio
import sqlite3

import pytest

from AutoCCF.config import config_manager
from DoPJ.scraper import scrape_thread


TEST_TID = 5043246514


class TestThreadScraperIntegration:
    """Test DoPJ scraper end-to-end persistence."""

    def test_scrape_thread_persists_content_db_and_metadata(self, tmp_path):
        """Test single-thread scrape writes complete local content artifacts."""
        config = config_manager.load()
        account = next((acc for acc in config.accounts if acc.bduss and acc.bduss.strip()), None)
        if account is None:
            pytest.skip("未配置可用 BDUSS，跳过真实 DoPJ 集成测试")

        success, error = asyncio.run(
            scrape_thread(TEST_TID, account.bduss, tmp_path, download_media=False)
        )

        assert success is True
        assert error == ""

        thread_dir = tmp_path / "threads" / str(TEST_TID)
        assert (tmp_path / "scrape_info.json").exists()
        assert (thread_dir / "forum.json").exists()
        assert (thread_dir / "thread.json").exists()

        db_path = thread_dir / "content.db"
        assert db_path.exists()

        with sqlite3.connect(db_path) as conn:
            post_count = conn.execute("SELECT COUNT(*) FROM post").fetchone()[0]
            contents = conn.execute(
                "SELECT contents FROM post WHERE contents != '' ORDER BY floor, create_time LIMIT 1"
            ).fetchone()

        assert post_count > 0
        assert contents is not None
        assert contents[0].strip().startswith("[")
