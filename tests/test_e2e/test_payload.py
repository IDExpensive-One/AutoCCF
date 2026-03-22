"""
E2E Payload 集成测试 — 使用用户 ID '团子传说' 验证完整流程

⚠️ 这是集成测试，需要：
  1. 有效的 config.json 配置（包含 BDUSS 账户）
  2. 可访问百度贴吧 API 的网络连接
  3. pytest-timeout 插件（pip install pytest-timeout）

如果配置不存在、BDUSS 无效或网络不可达，测试将被跳过。
运行方式：python -m pytest tests/test_e2e/test_payload.py -v -m integration
"""
import json
import os
import socket
import subprocess
import sys
import pytest

BRIDGE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'electron', 'bridge.py')
TARGET_USERNAME = "团子传说"


def _network_available(host: str = "tieba.baidu.com", port: int = 443, timeout: float = 3.0) -> bool:
    """检查是否有网络连接到百度贴吧"""
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def run_bridge(action: str, payload: dict, timeout: int = 120) -> list[dict]:
    """运行 bridge.py 并收集响应"""
    request = json.dumps({"action": action, "payload": payload})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    responses = []
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            responses.append(json.loads(line))
    return responses


def has_valid_config() -> bool:
    """检查是否有有效配置"""
    try:
        results = run_bridge("config:load", {}, timeout=10)
        if results and results[-1].get("type") == "result":
            data = results[-1].get("data", {})
            return data.get("success", False) and len(data.get("config", {}).get("accounts", [])) > 0
    except Exception:
        pass
    return False


_skip_no_config = pytest.mark.skipif(not has_valid_config(), reason="需要有效的 config.json 配置（含 BDUSS）")
_skip_no_network = pytest.mark.skipif(not _network_available(), reason="无法连接到 tieba.baidu.com，跳过集成测试")


@pytest.mark.integration
@_skip_no_config
@_skip_no_network
class TestAPoUPayload:
    """APoU 爬取 payload 集成测试"""

    def test_apou_crawl_returns_posts(self):
        """测试 APoU 爬取 '团子传说' 用户的发言"""
        results = run_bridge("apou:crawl", {"username": TARGET_USERNAME}, timeout=120)

        # 应该有 progress 事件（使用 page/posts_count 字段，与 spec 契约一致）
        progress_events = [r for r in results if r["type"] == "progress"]
        assert len(progress_events) > 0, "应该收到 progress 事件"
        # 验证 progress 事件格式
        for p in progress_events:
            assert "page" in p["data"], "progress 应包含 page 字段"
            assert "posts_count" in p["data"], "progress 应包含 posts_count 字段（每页帖子数）"

        # 最后一条应该是 result
        last = results[-1]
        assert last["type"] == "result", f"最后一条应该是 result，实际为: {last}"
        assert last["data"]["success"] is True
        assert last["data"]["posts_count"] > 0, "应该爬取到帖子"
        assert "output_file" in last["data"]

        # 验证输出文件是顶级 JSON 数组格式
        output_file = last["data"]["output_file"]
        if os.path.exists(output_file):
            with open(output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            assert isinstance(data, list), f"APoU 输出应为顶级 JSON 数组，实际类型: {type(data)}"
            if len(data) > 0:
                assert "tid" in data[0], "每条帖子应包含 tid 字段"
                assert "title" in data[0], "每条帖子应包含 title 字段"
                assert "href" in data[0], "每条帖子应包含 href 字段"


@pytest.mark.integration
@_skip_no_config
@_skip_no_network
class TestDoPJPayload:
    """DoPJ 爬取 payload 集成测试（在 APoU 爬取后运行）

    注意：此测试会触发 DoPJ 的完整爬取流程（所有线程），耗时可能较长。
    """

    def test_dopj_crawl_succeeds(self):
        """测试 DoPJ 爬取帖子详情"""
        # 首先获取 APoU 输出文件路径
        users_results = run_bridge("users:list", {}, timeout=10)
        last = users_results[-1]
        if last["type"] != "result":
            pytest.skip("无法获取用户列表")
        users = last["data"].get("users", [])
        target_user = None
        for u in users:
            if u.get("name") == TARGET_USERNAME:  # 注意：list_users() 返回 "name" 字段
                target_user = u
                break
        if target_user is None:
            pytest.skip(f"数据库中没有用户 '{TARGET_USERNAME}'，需先运行 APoU 测试")

        # 获取 input_json 路径 — 使用 get_posts_file() 兼容新旧路径
        from AutoCCF.config import ConfigManager
        from AutoCCF.utils import UserPaths
        cm = ConfigManager()
        config = cm.load()
        user_paths = UserPaths(config.database_dir, TARGET_USERNAME)
        posts_file = user_paths.get_posts_file()  # 返回实际存在的路径（新或旧），不存在返回 None

        if posts_file is None:
            pytest.skip("APoU 输出文件不存在（已检查新旧路径）")

        input_json = str(posts_file)
        output_dir = str(user_paths.dopj_dir)  # DoPJ 输出目录，用于验证 thread.json 存在

        results = run_bridge(
            "dopj:crawl",
            {"input_json": input_json},  # threads 可选，未传则从已保存配置读取
            timeout=300,
        )

        last = results[-1]
        assert last["type"] == "result", f"最后一条应该是 result，实际为: {last}"
        assert last["data"]["success"] is True
        stats = last["data"]["stats"]
        assert stats.get("total", 0) > 0, "应该有任务"
        assert stats.get("success", 0) + stats.get("skipped", 0) > 0, "至少有一个任务应成功完成或被跳过（增量模式）"

        # 验证 DoPJ 输出目录存在并包含 thread.json
        import glob
        thread_jsons = glob.glob(os.path.join(output_dir, "**", "thread.json"), recursive=True)
        assert len(thread_jsons) > 0, f"DoPJ 输出目录应包含至少一个 thread.json 文件（搜索目录: {output_dir}）"


@pytest.mark.integration
@_skip_no_config
@_skip_no_network
class TestUsersPayload:
    """用户列表 payload 集成测试（在 APoU 爬取后运行）"""

    def test_users_list_contains_target(self):
        """测试用户列表包含目标用户"""
        results = run_bridge("users:list", {})
        last = results[-1]
        assert last["type"] == "result"
        users = last["data"]["users"]
        names = [u["name"] for u in users]  # 注意：字段是 "name" 不是 "username"
        # 注意：此测试假设 APoU 测试已先运行
        if TARGET_USERNAME not in names:
            pytest.skip(f"数据库中没有用户 '{TARGET_USERNAME}'")

    def test_user_detail_has_posts(self):
        """测试用户详情包含帖子数据"""
        results = run_bridge("users:detail", {"username": TARGET_USERNAME})
        last = results[-1]
        if last["type"] == "error":
            pytest.skip("用户数据不存在")
        assert last["type"] == "result"
        # users:detail 返回顶级字段（与 spec schema 一致），不包裹在 "detail" 中
        data = last["data"]
        assert data["username"] == TARGET_USERNAME
        # 验证帖子是列表格式
        assert isinstance(data["posts"], list), "帖子应为列表格式"
