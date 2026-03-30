"""
APoU Anova client tests.
"""
import asyncio

import aiohttp

from APoU.anova_client import AnovaAPIClient
from APoU.config import CrawlerConfig


class _FakeResponse:
    """模拟 aiohttp 响应对象。"""

    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

    async def json(self, content_type=None):
        return self._payload


class _FakeSession:
    """模拟 aiohttp ClientSession。"""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params):
        self.calls.append({"url": url, "params": params})
        return self.response


class TestAnovaAPIClient:
    """Test AnovaAPIClient class."""

    def test_aenter_sets_safe_accept_encoding_without_brotli(self, monkeypatch):
        """Test session avoids Brotli-only decoding failures."""
        captured = {}

        class _DummyClientSession:
            def __init__(self, *args, **kwargs):
                captured["headers"] = kwargs.get("headers")
                captured["timeout"] = kwargs.get("timeout")

            async def close(self):
                return None

        monkeypatch.setattr(aiohttp, "ClientSession", _DummyClientSession)

        config = CrawlerConfig(anova_request_timeout=12)
        client = AnovaAPIClient(config)

        asyncio.run(client.__aenter__())

        assert captured["headers"] == {"Accept-Encoding": "gzip, deflate"}
        assert isinstance(captured["timeout"], aiohttp.ClientTimeout)
        assert captured["timeout"].total == 12

    def test_fetch_page_sends_empty_fname_before_username_and_page(self):
        """Test anova request includes empty fname parameter."""
        config = CrawlerConfig(anova_max_retries=1)
        client = AnovaAPIClient(config)
        session = _FakeSession(
            _FakeResponse(
                200,
                {
                    "msg": "Success.",
                    "posts": [],
                    "hasNext": 0,
                    "user": {"name": "团子传说"},
                },
            )
        )
        client.__dict__["_session"] = session

        asyncio.run(client.fetch_page("团子传说", 3))

        assert len(session.calls) == 1
        assert session.calls[0]["url"] == config.anova_base_url
        assert session.calls[0]["params"] == {
            "fname": "",
            "username": "团子传说",
            "page": "3",
        }

    def test_fetch_page_returns_posts_and_user_info_on_success(self):
        """Test successful anova response parsing."""
        config = CrawlerConfig(anova_max_retries=1)
        client = AnovaAPIClient(config)
        session = _FakeSession(
            _FakeResponse(
                200,
                {
                    "msg": "Success.",
                    "posts": [{"title": "test"}],
                    "hasNext": 1,
                    "user": {"name": "test_user"},
                },
            )
        )
        client.__dict__["_session"] = session

        posts, has_next, user_info = asyncio.run(client.fetch_page("test_user", 1))

        assert posts == [{"title": "test"}]
        assert has_next is True
        assert user_info == {"name": "test_user"}

    def test_fetch_page_returns_empty_result_on_http_error(self):
        """Test non-200 response returns empty result."""
        config = CrawlerConfig(anova_max_retries=1)
        client = AnovaAPIClient(config)
        session = _FakeSession(_FakeResponse(500, {"msg": "Server error"}))
        client.__dict__["_session"] = session

        posts, has_next, user_info = asyncio.run(client.fetch_page("test_user", 2))

        assert posts == []
        assert has_next is False
        assert user_info is None
