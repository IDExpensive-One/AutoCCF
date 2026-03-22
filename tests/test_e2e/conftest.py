"""E2E 集成测试配置 — 注册自定义 marker"""
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: 需要网络连接和有效 BDUSS 配置的集成测试"
    )
