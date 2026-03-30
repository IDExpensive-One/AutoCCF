"""
AutoCCF Tieba client tests.
"""
import asyncio

from AutoCCF.tieba.client import TiebaClient, _should_patch_aiotieba_get_posts


class TestTiebaClient:
    """Test TiebaClient wrapper behavior."""

    def test_get_posts_keeps_public_with_comments_argument(self, monkeypatch):
        """Test get_posts keeps aiotieba public API contract."""
        captured = {}

        async def fake_retry_request(self, func, *args, **kwargs):
            captured["func"] = func
            captured["args"] = args
            captured["kwargs"] = kwargs
            return object()

        monkeypatch.setattr(TiebaClient, "_retry_request", fake_retry_request)

        client = TiebaClient("test_bduss")
        asyncio.run(client.get_posts(123456, pn=2, with_comments=True, only_thread_author=False))

        assert captured["func"] == "get_posts"
        assert captured["args"] == (123456, 2)
        assert captured["kwargs"]["with_comments"] is True
        assert "with_floor" not in captured["kwargs"]
        assert captured["kwargs"]["only_thread_author"] is False

    def test_should_patch_aiotieba_get_posts_for_463(self):
        """Test version gate for buggy aiotieba releases."""
        assert _should_patch_aiotieba_get_posts("4.6.3") is True
        assert _should_patch_aiotieba_get_posts("4.6.4") is False
        assert _should_patch_aiotieba_get_posts("4.7.0") is False

    def test_get_user_info_fallbacks_to_portrait_when_user_id_invalid(self, monkeypatch):
        """Test get_user_info uses portrait when user_id <= 0."""
        captured = {}

        async def fake_retry_request(self, func, *args, **kwargs):
            captured["func"] = func
            captured["args"] = args
            captured["kwargs"] = kwargs
            return object()

        monkeypatch.setattr(TiebaClient, "_retry_request", fake_retry_request)

        client = TiebaClient("test_bduss")
        asyncio.run(client.get_user_info(0, portrait="tb.1.demo"))

        assert captured["func"] == "get_user_info"
        assert captured["args"] == ("tb.1.demo",)
