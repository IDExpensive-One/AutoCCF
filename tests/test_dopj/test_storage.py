"""
DoPJ Storage Tests

Tests for ContentDatabase from DoPJ/storage.py
"""
import pytest
from pathlib import Path
from DoPJ.storage import ContentDatabase
from AutoCCF.tieba.models import PostEntity, UserEntity


class TestContentDatabase:
    """Test ContentDatabase class"""

    def test_init(self, tmp_path):
        """Test ContentDatabase initialization"""
        db_path = tmp_path / "test.db"
        db = ContentDatabase(db_path)
        
        assert db.db_path == db_path
        assert db._conn is None

    def test_context_manager(self, tmp_path):
        """Test using ContentDatabase as context manager"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            assert db._conn is not None
        
        assert db._conn is None

    def test_creates_parent_directories(self, tmp_path):
        """Test that parent directories are created"""
        db_path = tmp_path / "subdir" / "another" / "test.db"
        db = ContentDatabase(db_path)
        db.connect()
        db.close()
        
        assert db_path.parent.exists()

    def test_init_schema_on_new_db(self, tmp_path):
        """Test that schema is initialized on new database"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            # Check tables exist
            cursor = db.connection.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = {row[0] for row in cursor.fetchall()}
        
        assert "post" in tables
        assert "user" in tables
        assert "db_info" in tables
        assert "scrape_batch" in tables

    def test_set_db_info(self, tmp_path):
        """Test setting database info"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            db.set_db_info(tid=123456789)
            
            cursor = db.connection.cursor()
            cursor.execute("SELECT v FROM db_info WHERE k = 'tid'")
            result = cursor.fetchone()
        
        assert result[0] == "123456789"

    def test_create_scrape_batch(self, tmp_path):
        """Test creating scrape batch"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            batch_id = db.create_scrape_batch('{"config": "test"}')
            
            assert batch_id > 0
            assert db.current_batch_id == batch_id

    def test_insert_and_get_post(self, tmp_path):
        """Test inserting and retrieving a post"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            db.create_scrape_batch()
            
            post = PostEntity(
                id=12345,
                contents='[{"type": 1, "text": "Hello"}]',
                floor=1,
                user_id=100,
                agree=10,
                disagree=1,
                create_time=1700000000,
                is_thread_author=True,
            )
            db.insert_post(post)
            db.commit()
            
            retrieved = db.get_post(12345)
        
        assert retrieved is not None
        assert retrieved.id == 12345
        assert retrieved.floor == 1
        assert retrieved.user_id == 100
        assert retrieved.agree == 10
        assert retrieved.is_thread_author is True

    def test_insert_posts_batch(self, tmp_path):
        """Test batch inserting posts"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            db.create_scrape_batch()
            
            posts = [
                PostEntity(id=1, contents="[]", floor=1, user_id=100, create_time=1),
                PostEntity(id=2, contents="[]", floor=2, user_id=101, create_time=2),
                PostEntity(id=3, contents="[]", floor=3, user_id=102, create_time=3),
            ]
            db.insert_posts(posts)
            
            all_posts = db.get_all_posts()
        
        assert len(all_posts) == 3

    def test_get_all_posts_ordered(self, tmp_path):
        """Test that get_all_posts returns ordered results"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            db.create_scrape_batch()
            
            # Insert out of order
            posts = [
                PostEntity(id=3, contents="[]", floor=3, user_id=100, create_time=3),
                PostEntity(id=1, contents="[]", floor=1, user_id=100, create_time=1),
                PostEntity(id=2, contents="[]", floor=2, user_id=100, create_time=2),
            ]
            db.insert_posts(posts)
            
            all_posts = db.get_all_posts()
        
        # Should be ordered by floor, create_time
        assert all_posts[0].floor == 1
        assert all_posts[1].floor == 2
        assert all_posts[2].floor == 3

    def test_get_nonexistent_post(self, tmp_path):
        """Test getting a post that doesn't exist"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            result = db.get_post(99999)
        
        assert result is None

    def test_insert_and_get_user(self, tmp_path):
        """Test inserting and retrieving a user"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            user = UserEntity(
                id=12345,
                portrait="tb.1.xxx",
                username="testuser",
                nickname="Test User",
                tieba_uid=99999,
                glevel=10,
                gender=1,
                is_vip=True,
                age=5.0,
            )
            db.insert_user(user)
            db.commit()
            
            retrieved = db.get_user(12345)
        
        assert retrieved is not None
        assert retrieved.id == 12345
        assert retrieved.username == "testuser"
        assert retrieved.nickname == "Test User"
        assert retrieved.is_vip is True

    def test_update_existing_user(self, tmp_path):
        """Test updating an existing user"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            # Insert initial user
            user1 = UserEntity(
                id=100,
                nickname="Original",
                age=1.0,
            )
            db.insert_user(user1)
            db.commit()
            
            # Update user
            user2 = UserEntity(
                id=100,
                nickname="Updated",
                age=2.0,
            )
            db.insert_user(user2)
            db.commit()
            
            retrieved = db.get_user(100)
        
        assert retrieved.nickname == "Updated"
        assert retrieved.age == 2.0

    def test_insert_users_batch(self, tmp_path):
        """Test batch inserting users"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            users = [
                UserEntity(id=1, nickname="User 1", age=1.0),
                UserEntity(id=2, nickname="User 2", age=2.0),
            ]
            db.insert_users(users)
            
            u1 = db.get_user(1)
            u2 = db.get_user(2)
        
        assert u1 is not None
        assert u2 is not None

    def test_mark_user_completed(self, tmp_path):
        """Test marking user as completed"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            user = UserEntity(id=100, nickname="Test", age=1.0, completed=0)
            db.insert_user(user)
            db.commit()
            
            db.mark_user_completed(100)
            
            retrieved = db.get_user(100)
        
        assert retrieved.completed == 1
        assert retrieved.scrape_time > 0

    def test_get_incomplete_users(self, tmp_path):
        """Test getting incomplete users"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            users = [
                UserEntity(id=1, nickname="Complete", age=1.0, completed=1),
                UserEntity(id=2, nickname="Incomplete", age=1.0, completed=0),
                UserEntity(id=3, nickname="Also Incomplete", age=1.0, completed=0),
            ]
            db.insert_users(users)
            
            incomplete = db.get_incomplete_users()
        
        assert len(incomplete) == 2
        assert all(u.completed == 0 for u in incomplete)

    def test_insert_origin_src(self, tmp_path):
        """Test inserting origin source record"""
        db_path = tmp_path / "test.db"
        
        with ContentDatabase(db_path) as db:
            db.insert_origin_src(
                filename="image_001.jpg",
                content_frag_type=3,
                origin_src="https://example.com/image.jpg",
            )
            db.commit()
            
            cursor = db.connection.cursor()
            cursor.execute(
                "SELECT * FROM tieba_origin_src WHERE filename = ?",
                ("image_001.jpg",)
            )
            row = cursor.fetchone()
        
        assert row is not None
        assert row["origin_src"] == "https://example.com/image.jpg"


class TestContentDatabaseErrors:
    """Test error handling in ContentDatabase"""

    def test_connection_required_for_operations(self, tmp_path):
        """Test that operations fail without connection"""
        db_path = tmp_path / "test.db"
        db = ContentDatabase(db_path)
        
        with pytest.raises(RuntimeError, match="数据库未连接"):
            _ = db.connection

    def test_version_constant(self):
        """Test VERSION constant"""
        assert ContentDatabase.VERSION == "2.0.0"
