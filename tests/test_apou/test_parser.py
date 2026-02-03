"""
APoU Parser Tests

Tests for PostParser and Post from APoU/parser.py
"""
import pytest
from APoU.parser import PostParser, Post


class TestPost:
    """Test Post dataclass"""

    def test_post_creation(self):
        """Test creating a Post"""
        post = Post(
            id=1,
            title="Test Title",
            content="Test Content",
            href="/p/123456",
            forum="testbar",
        )
        
        assert post.id == 1
        assert post.title == "Test Title"
        assert post.content == "Test Content"
        assert post.href == "/p/123456"
        assert post.forum == "testbar"

    def test_post_to_dict(self):
        """Test Post.to_dict() method"""
        post = Post(
            id=1,
            title="Title",
            content="Content",
            href="/p/999",
            forum="bar",
        )
        
        d = post.to_dict()
        
        assert isinstance(d, dict)
        assert d["id"] == 1
        assert d["title"] == "Title"
        assert d["content"] == "Content"
        assert d["href"] == "/p/999"
        assert d["forum"] == "bar"


class TestPostParser:
    """Test PostParser class"""

    def test_page_size_constant(self):
        """Test PAGE_SIZE constant"""
        assert PostParser.PAGE_SIZE == 20

    def test_parse_response_basic(self):
        """Test parsing basic response"""
        parser = PostParser()
        data = {
            "posts": [
                {"title": "Post 1", "content": "Content 1", "href": "/p/111"},
                {"title": "Post 2", "content": "Content 2", "href": "/p/222"},
            ]
        }
        
        posts = parser.parse_response(data, page=1)
        
        assert len(posts) == 2
        assert posts[0].id == 1
        assert posts[0].title == "Post 1"
        assert posts[1].id == 2
        assert posts[1].title == "Post 2"

    def test_parse_response_with_start_id(self):
        """Test parsing with custom start_id"""
        parser = PostParser()
        data = {
            "posts": [
                {"title": "Post A", "content": "", "href": "/p/100"},
            ]
        }
        
        posts = parser.parse_response(data, page=2, start_id=20)
        
        assert posts[0].id == 21  # start_id + 1

    def test_parse_response_empty_posts(self):
        """Test parsing response with empty posts"""
        parser = PostParser()
        data = {"posts": []}
        
        posts = parser.parse_response(data, page=1)
        
        assert posts == []

    def test_parse_response_missing_posts_key(self):
        """Test parsing response without posts key"""
        parser = PostParser()
        data = {"other": "data"}
        
        posts = parser.parse_response(data, page=1)
        
        assert posts == []

    def test_parse_response_invalid_data_type(self):
        """Test parsing non-dict data"""
        parser = PostParser()
        
        posts = parser.parse_response("invalid", page=1)
        
        assert posts == []

    def test_parse_response_skips_invalid_posts(self):
        """Test that invalid post entries are skipped"""
        parser = PostParser()
        data = {
            "posts": [
                {"title": "Valid", "content": "", "href": "/p/1"},
                "invalid_entry",
                123,
                {"title": "Also Valid", "content": "", "href": "/p/2"},
            ]
        }
        
        posts = parser.parse_response(data, page=1)
        
        assert len(posts) == 2

    def test_extract_forum_name_returns_placeholder(self):
        """Test that forum name returns placeholder"""
        parser = PostParser()
        
        result = parser._extract_forum_name("/p/123")
        
        assert result == "贴吧"

    def test_extract_forum_name_empty_href(self):
        """Test forum name extraction with empty href"""
        parser = PostParser()
        
        result = parser._extract_forum_name("")
        
        assert result == ""

    def test_has_more_data_true(self):
        """Test has_more_data returns True when posts exist"""
        parser = PostParser()
        data = {
            "posts": [{"title": "Test", "content": "", "href": "/p/1"}]
        }
        
        assert parser.has_more_data(data) is True

    def test_has_more_data_false(self):
        """Test has_more_data returns False when no posts"""
        parser = PostParser()
        
        assert parser.has_more_data({"posts": []}) is False
        assert parser.has_more_data({}) is False

    def test_get_posts_count(self):
        """Test get_posts_count"""
        parser = PostParser()
        
        data1 = {"posts": [1, 2, 3]}
        data2 = {"posts": []}
        data3 = {}
        
        assert parser.get_posts_count(data1) == 3
        assert parser.get_posts_count(data2) == 0
        assert parser.get_posts_count(data3) == 0

    def test_parse_single_post_with_missing_fields(self):
        """Test parsing post with missing optional fields"""
        parser = PostParser()
        data = {
            "posts": [
                {"href": "/p/123"}  # Missing title and content
            ]
        }
        
        posts = parser.parse_response(data, page=1)
        
        assert len(posts) == 1
        assert posts[0].title == ""
        assert posts[0].content == ""
        assert posts[0].href == "/p/123"
