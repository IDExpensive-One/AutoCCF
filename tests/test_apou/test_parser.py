"""
APoU Parser Tests

Tests for PostParser and Post from APoU/parser.py
"""
from APoU.parser import PostParser, Post


class TestPost:
    """Test Post dataclass"""

    def test_post_creation(self):
        """Test creating a Post"""
        post = Post(
            id=1,
            tid=100,
            pid=200,
            title="Test Title",
            content="Test Content",
            forum="testbar",
            href="/p/123456",
        )
        
        assert post.id == 1
        assert post.tid == 100
        assert post.pid == 200
        assert post.title == "Test Title"
        assert post.content == "Test Content"
        assert post.href == "/p/123456"
        assert post.forum == "testbar"

    def test_post_to_dict(self):
        """Test Post.to_dict() method"""
        post = Post(
            id=1,
            tid=100,
            pid=200,
            title="Title",
            content="Content",
            forum="bar",
            href="/p/999",
        )
        
        d = post.to_dict()
        
        assert isinstance(d, dict)
        assert d["id"] == 1
        assert d["tid"] == 100
        assert d["pid"] == 200
        assert d["title"] == "Title"
        assert d["content"] == "Content"
        assert d["href"] == "/p/999"
        assert d["forum"] == "bar"

    def test_post_build_href(self):
        """Test Post.build_href() method"""
        assert Post.build_href(123) == "https://tieba.baidu.com/p/123"
        assert Post.build_href(123, 456) == "https://tieba.baidu.com/p/123?pid=456"


class TestPostParser:
    """Test PostParser class"""

    def test_from_dict_basic(self):
        """Test PostParser.from_dict() with full data"""
        data = {
            "id": 1,
            "tid": 123,
            "pid": 456,
            "title": "Post Title",
            "content": "Post Content",
            "forum": "testbar",
            "href": "https://tieba.baidu.com/p/123?pid=456",
            "fid": 789,
            "create_time": 1700000000,
            "is_comment": True,
            "is_thread": False,
        }

        post = PostParser.from_dict(data)

        assert post.id == 1
        assert post.tid == 123
        assert post.pid == 456
        assert post.title == "Post Title"
        assert post.content == "Post Content"
        assert post.forum == "testbar"
        assert post.href == "https://tieba.baidu.com/p/123?pid=456"
        assert post.fid == 789
        assert post.create_time == 1700000000
        assert post.is_comment is True
        assert post.is_thread is False

    def test_from_dict_with_post_id(self):
        """Test post_id overrides dict id"""
        data = {
            "id": 1,
            "tid": 123,
            "pid": 456,
            "title": "Post Title",
            "content": "Post Content",
            "forum": "testbar",
            "href": "https://tieba.baidu.com/p/123?pid=456",
        }

        post = PostParser.from_dict(data, post_id=99)

        assert post.id == 99
        assert post.tid == 123
        assert post.pid == 456

    def test_from_dict_minimal(self):
        """Test PostParser.from_dict() with minimal data"""
        data = {
            "href": "https://tieba.baidu.com/p/123",
        }

        post = PostParser.from_dict(data)

        assert post.id == 0
        assert post.tid == 123
        assert post.pid == 0
        assert post.title == ""
        assert post.content == ""
        assert post.forum == ""
        assert post.href == "https://tieba.baidu.com/p/123"
        assert post.fid == 0
        assert post.create_time == 0
        assert post.is_comment is False
        assert post.is_thread is False

    def test_from_dict_legacy_href(self):
        """Test legacy href parsing for tid and pid"""
        data = {
            "tid": 0,
            "pid": 0,
            "href": "https://tieba.baidu.com/p/123?pid=456",
        }

        post = PostParser.from_dict(data)

        assert post.tid == 123
        assert post.pid == 456
