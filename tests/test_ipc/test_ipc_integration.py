"""
Bridge 协议集成测试 — 验证 bridge.py 的 NDJSON 协议和进程生命周期

通过 subprocess 直接测试 bridge.py（模拟 Electron main.js 的 spawn 行为），
验证协议层正确性（JSON 格式、退出码、stdout/stderr 隔离）。
不需要 Electron 环境。
"""
import json
import os
import subprocess
import sys
import time
import pytest

BRIDGE_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'electron', 'bridge.py')

def test_ndjson_format_validity():
    """验证所有输出行都是有效的 NDJSON"""
    request = json.dumps({"action": "config:load", "payload": {}})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=10,
    )
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            parsed = json.loads(line)  # 如果不是有效 JSON 会抛异常
            assert "type" in parsed, "每行必须包含 type 字段"
            assert "data" in parsed, "每行必须包含 data 字段"
            assert parsed["type"] in ("result", "error", "progress", "log")

def test_process_exits_cleanly():
    """验证 bridge.py 处理完请求后正常退出"""
    request = json.dumps({"action": "config:load", "payload": {}})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert proc.returncode == 0, f"进程应正常退出，实际退出码: {proc.returncode}"

def test_stderr_does_not_contain_ndjson():
    """验证 stderr 不包含 NDJSON（stdout 专用）"""
    request = json.dumps({"action": "config:load", "payload": {}})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=10,
    )
    for line in proc.stderr.strip().splitlines():
        if line.strip():
            # stderr 行不应该是 NDJSON 格式
            try:
                parsed = json.loads(line)
                if "type" in parsed and "data" in parsed:
                    pytest.fail(f"stderr 不应包含 NDJSON: {line}")
            except json.JSONDecodeError:
                pass  # stderr 可以包含非 JSON 内容（如 Python warnings）

def test_stdout_not_polluted_by_print():
    """验证 stdout 拦截器将裸 print() 包装为 log 事件"""
    request = json.dumps({"action": "config:load", "payload": {}})
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input=request,
        capture_output=True,
        text=True,
        timeout=10,
    )
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            # 所有 stdout 行必须是有效 JSON
            try:
                json.loads(line)
            except json.JSONDecodeError:
                pytest.fail(f"stdout 中发现非 JSON 行（stdout 污染）: {line[:100]}")

def test_timeout_handling():
    """验证进程在收到空输入时快速退出"""
    start = time.time()
    proc = subprocess.run(
        [sys.executable, BRIDGE_PATH],
        input="",
        capture_output=True,
        text=True,
        timeout=10,
    )
    elapsed = time.time() - start
    assert elapsed < 5, f"空输入应快速退出，实际耗时: {elapsed:.1f}s"
    responses = [json.loads(line) for line in proc.stdout.strip().splitlines() if line.strip()]
    assert len(responses) >= 1
    assert responses[0]["type"] == "error"
