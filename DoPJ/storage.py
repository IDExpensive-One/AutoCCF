"""
DoPJ SQLite 存储层

与 TiebaReader 兼容的 SQLite 数据库存储实现。
"""
import sqlite3
import time
import logging
from pathlib import Path
from typing import Optional, Any

# 添加父目录到路径以导入 autoccf
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from AutoCCF.tieba.models import (
    PostEntity,
    UserEntity,
    ScrapeBatch,
)

logger = logging.getLogger(__name__)


# TiebaReader 兼容的 DDL
DDL_SCRIPT = """
-- 数据库信息表
DROP TABLE IF EXISTS db_info;
CREATE TABLE db_info (
    k TEXT PRIMARY KEY,
    v TEXT NOT NULL
);
INSERT INTO db_info VALUES ('scraper_version', ''), ('tid', '');

-- 爬取批次表
DROP TABLE IF EXISTS scrape_batch;
CREATE TABLE scrape_batch (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scraper_version TEXT    NOT NULL,
    scrape_config   TEXT    NOT NULL,
    scrape_time     INTEGER NOT NULL
);

-- 帖子表
DROP TABLE IF EXISTS post;
CREATE TABLE post (
    id               INTEGER PRIMARY KEY,
    contents         TEXT               NOT NULL,
    floor            INTEGER            NOT NULL,
    user_id          INTEGER            NOT NULL,
    agree            INTEGER DEFAULT 0  NOT NULL,
    disagree         INTEGER DEFAULT 0  NOT NULL,
    create_time      INTEGER            NOT NULL,
    is_thread_author BOOLEAN DEFAULT 0  NOT NULL,
    sign             TEXT    DEFAULT '' NOT NULL,
    reply_num        INTEGER DEFAULT 0  NOT NULL,
    parent_id        INTEGER DEFAULT 0  NOT NULL,
    reply_to_id      INTEGER DEFAULT 0  NOT NULL,
    scrape_batch_id  INTEGER DEFAULT 0  NOT NULL
);
CREATE INDEX IF NOT EXISTS 'idx_post(floor)' ON post (floor);
CREATE INDEX IF NOT EXISTS 'idx_post(user_id)' ON post (user_id);
CREATE INDEX IF NOT EXISTS 'idx_post(agree)' ON post (agree);
CREATE INDEX IF NOT EXISTS 'idx_post(create_time)' ON post (create_time);
CREATE INDEX IF NOT EXISTS 'idx_post(is_thread_author)' ON post (is_thread_author);
CREATE INDEX IF NOT EXISTS 'idx_post(parent_id)' ON post (parent_id);
CREATE INDEX IF NOT EXISTS 'idx_post(scrape_batch_id)' ON post (scrape_batch_id);

-- 用户表
DROP TABLE IF EXISTS 'user';
CREATE TABLE user (
    id          INTEGER PRIMARY KEY,
    portrait    TEXT    DEFAULT NULL,
    username    TEXT    DEFAULT NULL,
    nickname    TEXT               NOT NULL,
    tieba_uid   INTEGER DEFAULT NULL,
    avatar      TEXT    DEFAULT NULL,
    glevel      INTEGER DEFAULT 0  NOT NULL,
    gender      INTEGER DEFAULT 0  NOT NULL,
    ip          TEXT    DEFAULT '' NOT NULL,
    is_vip      BOOLEAN DEFAULT 0  NOT NULL,
    is_god      BOOLEAN DEFAULT 0  NOT NULL,
    age         FLOAT              NOT NULL,
    sign        TEXT    DEFAULT '' NOT NULL,
    post_num    INTEGER DEFAULT 0  NOT NULL,
    agree_num   INTEGER DEFAULT 0  NOT NULL,
    fan_num     INTEGER DEFAULT 0  NOT NULL,
    follow_num  INTEGER DEFAULT 0  NOT NULL,
    forum_num   INTEGER DEFAULT 0  NOT NULL,
    level       INTEGER DEFAULT 0  NOT NULL,
    is_bawu     BOOLEAN DEFAULT 0  NOT NULL,
    status      INTEGER DEFAULT 0  NOT NULL,
    completed   BOOLEAN DEFAULT 0  NOT NULL,
    scrape_time INTEGER DEFAULT 0  NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS 'uk_user(portrait)' ON 'user'(portrait);
CREATE UNIQUE INDEX IF NOT EXISTS 'uk_user(tieba_uid)' ON 'user'(tieba_uid);
CREATE INDEX IF NOT EXISTS 'idx_user(completed)' ON 'user'(completed);

-- 用户信息历史表
DROP TABLE IF EXISTS user_info_history;
CREATE TABLE user_info_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    portrait    TEXT    DEFAULT NULL,
    username    TEXT    DEFAULT NULL,
    tieba_uid   INTEGER DEFAULT NULL,
    field_name  TEXT              NOT NULL,
    field_value TEXT              NOT NULL,
    scrape_time INTEGER DEFAULT 0 NOT NULL
);
CREATE INDEX IF NOT EXISTS 'idx_user_info_history(tieba_uid)' ON user_info_history (tieba_uid);
CREATE INDEX IF NOT EXISTS 'idx_user_info_history(portrait)' ON user_info_history (portrait);
CREATE INDEX IF NOT EXISTS 'idx_user_info_history(field_name)' ON user_info_history (field_name);

-- 内容片段类型表
DROP TABLE IF EXISTS content_fragment_type;
CREATE TABLE content_fragment_type (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL
);

-- 贴吧原始链接表
DROP TABLE IF EXISTS tieba_origin_src;
CREATE TABLE tieba_origin_src (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    filename          TEXT    NOT NULL,
    content_frag_type INTEGER NOT NULL,
    origin_src        TEXT    NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS 'uk_tieba_origin_src(filename)' ON tieba_origin_src (filename);
CREATE INDEX IF NOT EXISTS 'idx_tieba_origin_src(content_frag_type)' ON tieba_origin_src (content_frag_type);
"""


class ContentDatabase:
    """
    内容数据库

    与 TiebaReader 兼容的 SQLite 数据库封装。
    """

    VERSION = "2.0.0"

    def __init__(self, db_path: str | Path):
        """
        初始化数据库

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None
        self._current_batch_id: int = 0

    def connect(self) -> None:
        """连接数据库"""
        is_new = not self.db_path.exists()
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row

        if is_new:
            self._init_schema()

    def _init_schema(self) -> None:
        """初始化数据库表结构"""
        if self._conn is None:
            raise RuntimeError("数据库未连接")

        self._conn.executescript(DDL_SCRIPT)
        self._conn.commit()
        logger.info(f"数据库初始化完成: {self.db_path}")

    def close(self) -> None:
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "ContentDatabase":
        """上下文管理器入口"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

    @property
    def connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            raise RuntimeError("数据库未连接")
        return self._conn

    # =========================================================================
    # 数据库信息
    # =========================================================================

    def set_db_info(self, tid: int) -> None:
        """
        设置数据库信息

        Args:
            tid: 帖子 ID
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE db_info SET v = ? WHERE k = 'scraper_version'",
            (self.VERSION,)
        )
        cursor.execute(
            "UPDATE db_info SET v = ? WHERE k = 'tid'",
            (str(tid),)
        )
        self.connection.commit()

    # =========================================================================
    # 爬取批次
    # =========================================================================

    def create_scrape_batch(self, config: str = "{}") -> int:
        """
        创建爬取批次

        Args:
            config: 爬取配置（JSON 字符串）

        Returns:
            批次 ID
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT INTO scrape_batch (scraper_version, scrape_config, scrape_time)
            VALUES (?, ?, ?)
            """,
            (self.VERSION, config, int(time.time()))
        )
        self.connection.commit()
        self._current_batch_id = cursor.lastrowid or 0
        return self._current_batch_id

    @property
    def current_batch_id(self) -> int:
        """获取当前批次 ID"""
        return self._current_batch_id

    # =========================================================================
    # 帖子操作
    # =========================================================================

    def insert_post(self, post: PostEntity) -> None:
        """
        插入帖子

        Args:
            post: 帖子实体
        """
        cursor = self.connection.cursor()

        # 设置批次 ID
        if post.scrape_batch_id == 0:
            post.scrape_batch_id = self._current_batch_id

        cursor.execute(
            """
            INSERT OR REPLACE INTO post
            (id, contents, floor, user_id, agree, disagree, create_time,
             is_thread_author, sign, reply_num, parent_id, reply_to_id, scrape_batch_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            post.to_db_tuple()
        )

    def insert_posts(self, posts: list[PostEntity]) -> None:
        """
        批量插入帖子

        Args:
            posts: 帖子列表
        """
        for post in posts:
            self.insert_post(post)
        self.connection.commit()

    def get_post(self, pid: int) -> Optional[PostEntity]:
        """
        获取帖子

        Args:
            pid: 帖子 ID

        Returns:
            帖子实体或 None
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM post WHERE id = ?", (pid,))
        row = cursor.fetchone()
        if row:
            return self._row_to_post(row)
        return None

    def get_all_posts(self) -> list[PostEntity]:
        """
        获取所有帖子

        Returns:
            帖子列表
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM post ORDER BY floor, create_time")
        return [self._row_to_post(row) for row in cursor.fetchall()]

    @staticmethod
    def _row_to_post(row: sqlite3.Row) -> PostEntity:
        """将数据库行转换为帖子实体"""
        return PostEntity(
            id=row["id"],
            contents=row["contents"],
            floor=row["floor"],
            user_id=row["user_id"],
            agree=row["agree"],
            disagree=row["disagree"],
            create_time=row["create_time"],
            is_thread_author=bool(row["is_thread_author"]),
            sign=row["sign"],
            reply_num=row["reply_num"],
            parent_id=row["parent_id"],
            reply_to_id=row["reply_to_id"],
            scrape_batch_id=row["scrape_batch_id"],
        )

    # =========================================================================
    # 用户操作
    # =========================================================================

    def insert_user(self, user: UserEntity) -> None:
        """
        插入用户

        Args:
            user: 用户实体
        """
        cursor = self.connection.cursor()

        # 检查用户是否已存在
        cursor.execute("SELECT id FROM user WHERE id = ?", (user.id,))
        if cursor.fetchone():
            # 更新现有用户
            cursor.execute(
                """
                UPDATE user SET
                    portrait = COALESCE(?, portrait),
                    username = COALESCE(?, username),
                    nickname = ?,
                    tieba_uid = COALESCE(?, tieba_uid),
                    avatar = COALESCE(?, avatar),
                    glevel = ?,
                    gender = ?,
                    ip = ?,
                    is_vip = ?,
                    is_god = ?,
                    age = ?,
                    sign = ?,
                    post_num = ?,
                    agree_num = ?,
                    fan_num = ?,
                    follow_num = ?,
                    forum_num = ?,
                    level = ?,
                    is_bawu = ?,
                    status = ?,
                    completed = ?,
                    scrape_time = ?
                WHERE id = ?
                """,
                (
                    user.portrait,
                    user.username,
                    user.nickname,
                    user.tieba_uid,
                    user.avatar,
                    user.glevel,
                    user.gender,
                    user.ip,
                    int(user.is_vip),
                    int(user.is_god),
                    user.age,
                    user.sign,
                    user.post_num,
                    user.agree_num,
                    user.fan_num,
                    user.follow_num,
                    user.forum_num,
                    user.level,
                    int(user.is_bawu),
                    user.status,
                    user.completed,
                    user.scrape_time,
                    user.id,
                )
            )
        else:
            # 插入新用户
            cursor.execute(
                """
                INSERT INTO user
                (id, portrait, username, nickname, tieba_uid, avatar, glevel, gender,
                 ip, is_vip, is_god, age, sign, post_num, agree_num, fan_num,
                 follow_num, forum_num, level, is_bawu, status, completed, scrape_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                user.to_db_tuple()
            )

    def insert_users(self, users: list[UserEntity]) -> None:
        """
        批量插入用户

        Args:
            users: 用户列表
        """
        for user in users:
            self.insert_user(user)
        self.connection.commit()

    def get_user(self, user_id: int) -> Optional[UserEntity]:
        """
        获取用户

        Args:
            user_id: 用户 ID

        Returns:
            用户实体或 None
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM user WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_user(row)
        return None

    def get_incomplete_users(self) -> list[UserEntity]:
        """
        获取未完成信息的用户

        Returns:
            用户列表
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM user WHERE completed = 0")
        return [self._row_to_user(row) for row in cursor.fetchall()]

    def mark_user_completed(self, user_id: int) -> None:
        """
        标记用户信息已完成

        Args:
            user_id: 用户 ID
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE user SET completed = 1, scrape_time = ? WHERE id = ?",
            (int(time.time()), user_id)
        )
        self.connection.commit()

    @staticmethod
    def _row_to_user(row: sqlite3.Row) -> UserEntity:
        """将数据库行转换为用户实体"""
        return UserEntity(
            id=row["id"],
            portrait=row["portrait"],
            username=row["username"],
            nickname=row["nickname"],
            tieba_uid=row["tieba_uid"],
            avatar=row["avatar"],
            glevel=row["glevel"],
            gender=row["gender"],
            ip=row["ip"],
            is_vip=bool(row["is_vip"]),
            is_god=bool(row["is_god"]),
            age=row["age"],
            sign=row["sign"],
            post_num=row["post_num"],
            agree_num=row["agree_num"],
            fan_num=row["fan_num"],
            follow_num=row["follow_num"],
            forum_num=row["forum_num"],
            level=row["level"],
            is_bawu=bool(row["is_bawu"]),
            status=row["status"],
            completed=row["completed"],
            scrape_time=row["scrape_time"],
        )

    # =========================================================================
    # 原始链接
    # =========================================================================

    def insert_origin_src(
        self,
        filename: str,
        content_frag_type: int,
        origin_src: str
    ) -> None:
        """
        插入原始链接记录

        Args:
            filename: 本地文件名
            content_frag_type: 内容片段类型
            origin_src: 原始链接
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO tieba_origin_src
            (filename, content_frag_type, origin_src)
            VALUES (?, ?, ?)
            """,
            (filename, content_frag_type, origin_src)
        )

    def commit(self) -> None:
        """提交事务"""
        self.connection.commit()


__all__ = ["ContentDatabase", "DDL_SCRIPT"]
