"""
贴吧 API 客户端封装

基于 aiotieba 库提供简化的异步 API 调用接口。
"""
import asyncio
from dataclasses import dataclass
from typing import Optional, Any, AsyncIterator
from contextlib import asynccontextmanager
import logging
import re

try:
    import aiotieba as tb
    from aiotieba.api.get_posts import _api as get_posts_api
except ImportError:
    raise ImportError(
        "aiotieba 未安装，请运行: pip install aiotieba>=4.4.9"
    )


logger = logging.getLogger(__name__)


def _parse_version(version: str) -> tuple[int, ...]:
    """解析版本号中的数字部分。"""
    parts = re.findall(r"\d+", version)
    return tuple(int(part) for part in parts)


def _should_patch_aiotieba_get_posts(version: str) -> bool:
    """判断是否需要修补 aiotieba 4.6.3 的 get_posts protobuf 兼容问题。"""
    parsed = _parse_version(version)
    return parsed != () and parsed < (4, 6, 4)


def _patch_aiotieba_get_posts_api() -> None:
    """为旧版 aiotieba 修补 bool 写入 int protobuf 字段的问题。"""
    if getattr(get_posts_api, "_AUTOCCF_BOOL_INT_PATCHED", False):
        return

    version = getattr(tb, "__version__", "")
    if not _should_patch_aiotieba_get_posts(version):
        return

    def patched_pack_proto(
        account,
        tid: int,
        pn: int,
        rn: int,
        sort: int,
        only_thread_author: bool,
        with_comments: bool,
        comment_sort_by_agree: bool,
        comment_rn: int,
    ) -> bytes:
        req_proto = getattr(get_posts_api.PbPageReqIdl_pb2, "PbPageReqIdl")()
        req_proto.data.common._client_type = 2
        req_proto.data.common._client_version = get_posts_api.MAIN_VERSION
        req_proto.data.kz = tid
        req_proto.data.pn = pn
        req_proto.data.rn = rn if rn > 1 else 2
        req_proto.data.r = sort
        req_proto.data.lz = int(only_thread_author)
        if with_comments:
            req_proto.data.common.BDUSS = account.BDUSS
            req_proto.data.with_floor = int(with_comments)
            req_proto.data.floor_sort_type = int(comment_sort_by_agree)
            req_proto.data.floor_rn = comment_rn

        return req_proto.SerializeToString()

    get_posts_api.pack_proto = patched_pack_proto
    setattr(get_posts_api, "_AUTOCCF_BOOL_INT_PATCHED", True)


_patch_aiotieba_get_posts_api()


@dataclass
class ClientConfig:
    """客户端配置"""

    bduss: str  # 百度账号的 BDUSS cookie
    retry: int = 3  # 失败重试次数
    timeout: float = 10.0  # 请求超时时间（秒）


class TiebaClient:
    """
    贴吧 API 客户端

    封装 aiotieba 库，提供简化的异步 API 调用接口。

    使用示例：
    ```python
    async with TiebaClient(bduss="your_bduss") as client:
        posts = await client.get_posts(tid=12345)
        if posts:
            for post in posts.posts:
                print(post.contents)
    ```
    """

    def __init__(
        self,
        bduss: str,
        retry: int = 3,
        timeout: float = 10.0,
    ):
        """
        初始化客户端

        Args:
            bduss: 百度账号的 BDUSS cookie
            retry: 失败重试次数
            timeout: 请求超时时间（秒）
        """
        self.bduss = bduss
        self.retry = retry
        self.timeout = timeout
        self._client: Optional[tb.Client] = None

    async def __aenter__(self) -> "TiebaClient":
        """异步上下文管理器入口"""
        self._client = tb.Client(self.bduss)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if self._client:
            await self._client.__aexit__(exc_type, exc_val, exc_tb)
            self._client = None

    @asynccontextmanager
    async def _get_client(self) -> AsyncIterator[tb.Client]:
        """
        获取客户端实例

        如果已在上下文中，使用现有客户端；否则创建新的。
        """
        if self._client:
            yield self._client
        else:
            async with tb.Client(self.bduss) as client:
                yield client

    async def _retry_request(
        self,
        func,
        *args,
        validate=None,
        operation: str = "",
        **kwargs,
    ) -> Optional[Any]:
        """
        带重试的请求包装器

        Args:
            func: 要调用的异步函数
            *args: 位置参数
            validate: 验证函数，返回 True 表示成功
            operation: 操作名称（用于日志）
            **kwargs: 关键字参数

        Returns:
            请求结果或 None
        """
        for attempt in range(1, self.retry + 1):
            try:
                async with self._get_client() as client:
                    method = getattr(client, func.__name__ if callable(func) else func)
                    result = await asyncio.wait_for(
                        method(*args, **kwargs),
                        timeout=self.timeout,
                    )

                    if validate is None or validate(result):
                        return result

                    logger.warning(
                        f"{operation} 验证失败 (第 {attempt}/{self.retry} 次)"
                    )

            except asyncio.TimeoutError:
                logger.warning(
                    f"{operation} 超时 (第 {attempt}/{self.retry} 次)"
                )
            except Exception as e:
                logger.error(
                    f"{operation} 错误 (第 {attempt}/{self.retry} 次): {e}"
                )

            if attempt < self.retry:
                await asyncio.sleep(0.5 * attempt)

        return None

    async def get_forum(self, fname_or_fid: str | int) -> Optional[Any]:
        """
        获取贴吧基本信息

        Args:
            fname_or_fid: 贴吧名或贴吧 ID

        Returns:
            贴吧信息对象或 None
        """
        return await self._retry_request(
            "get_forum",
            fname_or_fid,
            validate=lambda r: r and r.fid != 0,
            operation=f"获取贴吧 [{fname_or_fid}]",
        )

    async def get_forum_detail(self, fname_or_fid: str | int) -> Optional[Any]:
        """
        获取贴吧详细信息

        Args:
            fname_or_fid: 贴吧名或贴吧 ID

        Returns:
            贴吧详细信息对象或 None
        """
        return await self._retry_request(
            "get_forum_detail",
            fname_or_fid,
            validate=lambda r: r and r.fid != 0,
            operation=f"获取贴吧详情 [{fname_or_fid}]",
        )

    async def get_posts(
        self,
        tid: int,
        pn: int = 1,
        with_comments: bool = True,
        only_thread_author: bool = False,
    ) -> Optional[Any]:
        """
        获取帖子列表

        Args:
            tid: 帖子 ID
            pn: 页码
            with_comments: 是否包含楼中楼
            only_thread_author: 是否只看楼主

        Returns:
            帖子列表对象或 None
        """
        return await self._retry_request(
            "get_posts",
            tid,
            pn,
            with_comments=with_comments,
            only_thread_author=only_thread_author,
            validate=lambda r: r and r.thread.tid != 0,
            operation=f"获取帖子 [tid={tid}, pn={pn}]",
        )

    async def get_comments(
        self,
        tid: int,
        pid: int,
        pn: int = 1,
    ) -> Optional[Any]:
        """
        获取楼中楼评论

        Args:
            tid: 帖子 ID
            pid: 楼层 ID
            pn: 页码

        Returns:
            评论列表对象或 None
        """
        return await self._retry_request(
            "get_comments",
            tid,
            pid,
            pn,
            validate=lambda r: r and r.post.pid != 0,
            operation=f"获取评论 [tid={tid}, pid={pid}, pn={pn}]",
        )

    async def get_user_posts(
        self,
        id_: str | int,
        pn: int = 1,
        rn: int = 20,
    ) -> Optional[Any]:
        """
        获取用户发布的回复列表

        Args:
            id_: 用户 ID / 用户名 / portrait
            pn: 页码
            rn: 每页条数（最大 50）

        Returns:
            UserPostss 对象或 None
        """
        return await self._retry_request(
            "get_user_posts",
            id_,
            pn,
            rn=rn,
            validate=lambda r: r is not None and r.err is None,
            operation=f"获取用户回复 [id={id_}, pn={pn}]",
        )

    async def get_user_threads(
        self,
        id_: str | int,
        pn: int = 1,
    ) -> Optional[Any]:
        """
        获取用户发布的主题帖列表

        Args:
            id_: 用户 ID / 用户名 / portrait
            pn: 页码

        Returns:
            UserThreads 对象或 None
        """
        return await self._retry_request(
            "get_user_threads",
            id_,
            pn,
            validate=lambda r: r is not None and r.err is None,
            operation=f"获取用户主题帖 [id={id_}, pn={pn}]",
        )

    async def get_user_info(
        self,
        user_id: str | int,
        portrait: Optional[str] = None,
    ) -> Optional[Any]:
        """
        获取用户信息

        Args:
            user_id: 用户 ID
            portrait: 用户 portrait（当 user_id 无效时回退）

        Returns:
            用户信息对象或 None
        """
        target: str | int = user_id
        if (
            isinstance(user_id, int)
            and user_id <= 0
            and portrait
            and portrait.strip()
        ):
            target = portrait.strip()

        return await self._retry_request(
            "get_user_info",
            target,
            validate=lambda r: r and r.user_id != 0,
            operation=f"获取用户信息 [id={target}]",
        )


class AccountPool:
    """
    账户池

    管理多个 BDUSS，支持轮换使用以避免风控。
    """

    def __init__(self, bduss_list: list[str], retry: int = 3):
        """
        初始化账户池

        Args:
            bduss_list: BDUSS 列表
            retry: 每个账户的重试次数
        """
        if not bduss_list:
            raise ValueError("BDUSS 列表不能为空")

        self.bduss_list = bduss_list
        self.retry = retry
        self._index = 0
        self._lock = asyncio.Lock()
        self._banned: set[int] = set()  # 被封禁的账户索引

    @property
    def available_count(self) -> int:
        """可用账户数量"""
        return len(self.bduss_list) - len(self._banned)

    def _get_next_index(self) -> Optional[int]:
        """获取下一个可用账户索引"""
        for _ in range(len(self.bduss_list)):
            if self._index not in self._banned:
                return self._index
            self._index = (self._index + 1) % len(self.bduss_list)
        return None

    async def get_client(self) -> Optional[TiebaClient]:
        """
        获取下一个可用的客户端

        Returns:
            TiebaClient 实例或 None（如果没有可用账户）
        """
        async with self._lock:
            index = self._get_next_index()
            if index is None:
                return None

            bduss = self.bduss_list[index]
            self._index = (index + 1) % len(self.bduss_list)
            return TiebaClient(bduss=bduss, retry=self.retry)

    async def mark_banned(self, bduss: str) -> None:
        """
        标记账户被封禁

        Args:
            bduss: 被封禁的 BDUSS
        """
        async with self._lock:
            try:
                index = self.bduss_list.index(bduss)
                self._banned.add(index)
                logger.warning(
                    f"账户 #{index + 1} 被标记为封禁 "
                    f"(剩余可用: {self.available_count})"
                )
            except ValueError:
                pass

    async def reset_banned(self) -> None:
        """重置所有封禁状态"""
        async with self._lock:
            self._banned.clear()
            logger.info("已重置所有账户封禁状态")


@asynccontextmanager
async def create_client(bduss: str, retry: int = 3) -> AsyncIterator[TiebaClient]:
    """
    创建客户端的便捷函数

    Args:
        bduss: BDUSS cookie
        retry: 重试次数

    Yields:
        TiebaClient 实例
    """
    client = TiebaClient(bduss=bduss, retry=retry)
    async with client:
        yield client


__all__ = [
    "TiebaClient",
    "ClientConfig",
    "AccountPool",
    "create_client",
]
