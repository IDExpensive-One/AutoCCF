import json
import subprocess
import sys
import os

def run_bridge(action: str, payload: dict) -> list[dict]:
    """启动 bridge.py 子进程，发送请求，收集所有响应行"""
    bridge_path = os.path.join(os.path.dirname(__file__), '..', '..', 'electron', 'bridge.py')
    request = json.dumps({"action": action, "payload": payload})
    proc = subprocess.run(
        [sys.executable, bridge_path],
        input=request,
        capture_output=True,
        text=True,
        timeout=30,
    )
    responses = []
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            responses.append(json.loads(line))
    return responses

def test_unknown_action_returns_error():
    results = run_bridge("unknown:action", {})
    assert len(results) == 1
    assert results[0]["type"] == "error"
    assert "unknown" in results[0]["data"]["message"].lower()

def test_config_load_returns_result():
    results = run_bridge("config:load", {})
    assert len(results) >= 1
    last = results[-1]
    assert last["type"] in ("result", "error")

def test_invalid_json_handled():
    bridge_path = os.path.join(os.path.dirname(__file__), '..', '..', 'electron', 'bridge.py')
    proc = subprocess.run(
        [sys.executable, bridge_path],
        input="not valid json",
        capture_output=True,
        text=True,
        timeout=10,
    )
    responses = []
    for line in proc.stdout.strip().splitlines():
        if line.strip():
            responses.append(json.loads(line))
    assert len(responses) >= 1
    assert responses[0]["type"] == "error"
