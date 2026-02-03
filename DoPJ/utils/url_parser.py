"""
URL 解析工具
从贴吧链接中提取 tid 和 pid
"""
import re
from typing import Optional, Tuple


def parse_tieba_url(url: str) -> Optional[Tuple[int, Optional[int]]]:
    """
    解析贴吧 URL，提取 tid 和 pid

    Args:
        url: 贴吧帖子链接，例如 https://tieba.baidu.com/p/5052759887?pid=105910715857#105910715857

    Returns:
        (tid, pid) 元组，如果解析失败返回 None
        - tid: 帖子 ID (必有)
        - pid: 回复 ID (可选，主帖时为 None)
    """
    try:
        # 提取 tid (格式: /p/数字)
        tid_match = re.search(r'/p/(\d+)', url)
        if not tid_match:
            return None

        tid = int(tid_match.group(1))

        # 提取 pid (格式: ?pid=数字 或 &pid=数字)
        pid_match = re.search(r'[?&]pid=(\d+)', url)
        pid = int(pid_match.group(1)) if pid_match else None

        return (tid, pid)
    except Exception as e:
        print(f"解析 URL 失败: {url}, 错误: {e}")
        return None


def extract_tid_from_url(url: str) -> Optional[int]:
    """
    从 URL 中仅提取 tid

    Args:
        url: 贴吧帖子链接

    Returns:
        tid 或 None
    """
    result = parse_tieba_url(url)
    return result[0] if result else None


def extract_pid_from_url(url: str) -> Optional[int]:
    """
    从 URL 中仅提取 pid

    Args:
        url: 贴吧帖子链接

    Returns:
        pid 或 None
    """
    result = parse_tieba_url(url)
    return result[1] if result else None


if __name__ == "__main__":
    # 测试代码
    test_urls = [
        "https://tieba.baidu.com/p/5052759887?pid=105910715857#105910715857",
        "https://tieba.baidu.com/p/5043594059?pid=105666571465#105666571465",
        "https://tieba.baidu.com/p/8173224373",  # 主帖，没有 pid
    ]

    for url in test_urls:
        result = parse_tieba_url(url)
        print(f"URL: {url}")
        print(f"Result: {result}")
        print()
