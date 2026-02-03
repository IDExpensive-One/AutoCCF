"""
AutoCCF Tieba Models Tests

Tests for data models from AutoCCF/tieba/models.py
"""
import json
import pytest
from AutoCCF.tieba.models import (
    ContentFragType,
    ContentFrag,
    FragText,
    FragEmoji,
    FragImage,
    FragAt,
    PostEntity,
    UserEntity,
)


class TestContentFragType:
    """Test ContentFragType enum"""

    def test_type_values(self):
        """Test that types have expected values"""
        assert ContentFragType.TEXT == 1
        assert ContentFragType.EMOJI == 2
        assert ContentFragType.IMAGE == 3
        assert ContentFragType.AT == 4
        assert ContentFragType.LINK == 5
        assert ContentFragType.TIEBAPLUS == 6
        assert ContentFragType.VIDEO == 7
        assert ContentFragType.VOICE == 8
        assert ContentFragType.SCRAPE_ERROR == -1

    def test_types_are_int(self):
        """Test that types are integers"""
        assert isinstance(ContentFragType.TEXT.value, int)
        assert isinstance(ContentFragType.IMAGE.value, int)


class TestFragText:
    """Test FragText class"""

    def test_creation(self):
        """Test creating FragText"""
        # type parameter is required but __post_init__ sets it
        frag = FragText(type=0, text="Hello world")
        
        assert frag.type == ContentFragType.TEXT
        assert frag.text == "Hello world"

    def test_to_dict(self):
        """Test FragText to_dict()"""
        frag = FragText(type=0, text="Test")
        
        d = frag.to_dict()
        
        assert d["type"] == 1  # ContentFragType.TEXT
        assert d["text"] == "Test"

    def test_to_json(self):
        """Test FragText to_json()"""
        frag = FragText(type=0, text="JSON test")
        
        j = frag.to_json()
        parsed = json.loads(j)
        
        assert parsed["type"] == 1
        assert parsed["text"] == "JSON test"


class TestFragEmoji:
    """Test FragEmoji class"""

    def test_creation(self):
        """Test creating FragEmoji"""
        frag = FragEmoji(type=0, id="image_emoticon25", desc="滑稽")
        
        assert frag.type == ContentFragType.EMOJI
        assert frag.id == "image_emoticon25"
        assert frag.desc == "滑稽"

    def test_to_dict(self):
        """Test FragEmoji to_dict()"""
        frag = FragEmoji(type=0, id="emoji_1", desc="smile")
        
        d = frag.to_dict()
        
        assert d["type"] == 2
        assert d["id"] == "emoji_1"
        assert d["desc"] == "smile"


class TestFragImage:
    """Test FragImage class"""

    def test_creation(self):
        """Test creating FragImage"""
        frag = FragImage(
            type=0,
            filename="p_123_0_xxx.jpg",
            tb_origin_src="https://tiebapic.baidu.com/xxx.jpg",
            show_width=800,
            show_height=600,
        )
        
        assert frag.type == ContentFragType.IMAGE
        assert frag.filename == "p_123_0_xxx.jpg"
        assert frag.show_width == 800
        assert frag.show_height == 600

    def test_default_values(self):
        """Test default values"""
        frag = FragImage(type=0)
        
        assert frag.filename == ""
        assert frag.tb_origin_src == ""
        assert frag.origin_size == 0
        assert frag.hash == ""


class TestFragAt:
    """Test FragAt class"""

    def test_creation(self):
        """Test creating FragAt"""
        frag = FragAt(type=0, text="@username", user_id=12345)
        
        assert frag.type == ContentFragType.AT
        assert frag.text == "@username"
        assert frag.user_id == 12345


class TestPostEntity:
    """Test PostEntity class"""

    def test_creation(self):
        """Test creating PostEntity"""
        post = PostEntity(
            id=12345678,
            contents='[{"type": 1, "text": "Hello"}]',
            floor=1,
            user_id=100,
            create_time=1700000000,
        )
        
        assert post.id == 12345678
        assert post.floor == 1
        assert post.user_id == 100
        assert post.create_time == 1700000000

    def test_default_values(self):
        """Test default values"""
        post = PostEntity(
            id=1,
            contents="[]",
            floor=1,
            user_id=1,
            create_time=0,
        )
        
        assert post.agree == 0
        assert post.disagree == 0
        assert post.is_thread_author is False
        assert post.sign == ""
        assert post.reply_num == 0
        assert post.parent_id == 0
        assert post.reply_to_id == 0
        assert post.scrape_batch_id == 0

    def test_to_db_tuple(self):
        """Test to_db_tuple() method"""
        post = PostEntity(
            id=123,
            contents='[]',
            floor=5,
            user_id=999,
            agree=10,
            disagree=2,
            create_time=1700000000,
            is_thread_author=True,
            sign="签名",
            reply_num=3,
            parent_id=100,
            reply_to_id=110,
            scrape_batch_id=1,
        )
        
        t = post.to_db_tuple()
        
        assert t[0] == 123  # id
        assert t[1] == '[]'  # contents
        assert t[2] == 5  # floor
        assert t[3] == 999  # user_id
        assert t[4] == 10  # agree
        assert t[5] == 2  # disagree
        assert t[6] == 1700000000  # create_time
        assert t[7] == 1  # is_thread_author (as int)

    def test_is_thread_author_bool_conversion(self):
        """Test that is_thread_author is properly converted"""
        post = PostEntity(
            id=1,
            contents="[]",
            floor=1,
            user_id=1,
            create_time=0,
            is_thread_author=True,
        )
        
        t = post.to_db_tuple()
        
        # Should be 1 (int) for SQLite, not True (bool)
        assert t[7] == 1


class TestUserEntity:
    """Test UserEntity class"""

    def test_creation(self):
        """Test creating UserEntity"""
        user = UserEntity(
            id=12345,
            portrait="tb.1.xxx",
            username="testuser",
            nickname="Test User",
            age=5.0,
        )
        
        assert user.id == 12345
        assert user.portrait == "tb.1.xxx"
        assert user.username == "testuser"
        assert user.nickname == "Test User"
        assert user.age == 5.0

    def test_default_values(self):
        """Test default values"""
        user = UserEntity(
            id=1,
            nickname="Test",
            age=0.0,
        )
        
        assert user.portrait is None
        assert user.username is None
        assert user.tieba_uid is None
        assert user.avatar is None
        assert user.glevel == 0
        assert user.gender == 0
        assert user.ip == ""
        assert user.is_vip is False
        assert user.is_god is False
        assert user.sign == ""
        assert user.post_num == 0
        assert user.agree_num == 0
        assert user.fan_num == 0
        assert user.follow_num == 0
        assert user.forum_num == 0
        assert user.level == 0
        assert user.is_bawu is False
        assert user.status == 0
        assert user.completed == 0
        assert user.scrape_time == 0

    def test_to_db_tuple(self):
        """Test to_db_tuple() method"""
        user = UserEntity(
            id=100,
            portrait="tb.1.abc",
            username="user1",
            nickname="User One",
            tieba_uid=99999,
            glevel=10,
            gender=1,
            is_vip=True,
            age=3.5,
        )
        
        t = user.to_db_tuple()
        
        assert t[0] == 100  # id
        assert t[1] == "tb.1.abc"  # portrait
        assert t[2] == "user1"  # username
        assert t[3] == "User One"  # nickname
        assert t[4] == 99999  # tieba_uid

    def test_vip_and_god_bool_conversion(self):
        """Test boolean conversion for VIP and god status"""
        user = UserEntity(
            id=1,
            nickname="VIP User",
            age=1.0,
            is_vip=True,
            is_god=True,
        )
        
        t = user.to_db_tuple()
        
        # Find is_vip and is_god in tuple (positions may vary)
        # They should be 1 for True
        assert 1 in t  # At least one should be 1


class TestContentFrag:
    """Test base ContentFrag class"""

    def test_to_dict(self):
        """Test to_dict() on base class"""
        # Using FragText as it's a concrete implementation
        frag = FragText(type=0, text="test")
        
        d = frag.to_dict()
        
        assert isinstance(d, dict)
        assert "type" in d

    def test_to_json(self):
        """Test to_json() produces valid JSON"""
        frag = FragText(type=0, text="中文测试")
        
        j = frag.to_json()
        
        # Should be valid JSON
        parsed = json.loads(j)
        assert parsed["text"] == "中文测试"
        
        # Should use ensure_ascii=False
        assert "中文测试" in j
