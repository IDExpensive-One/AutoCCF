"""
AutoCCF 统一日志模块

提供标准化的日志配置和预配置的 logger 实例。
"""
import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console_output: bool = True,
) -> logging.Logger:
    """
    配置并返回 logger

    Args:
        name: logger 名称
        level: 日志级别
        log_file: 日志文件路径（可选）
        console_output: 是否输出到控制台

    Returns:
        配置好的 logger 实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台处理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # 文件处理器（可选）
    if log_file:
        # 确保日志目录存在
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger

    Args:
        name: logger 名称

    Returns:
        logger 实例
    """
    return logging.getLogger(name)


def configure_root_logger(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
) -> None:
    """
    配置根 logger

    Args:
        level: 日志级别
        log_file: 日志文件路径（可选）
    """
    setup_logger('AutoCCF', level, log_file)


# 预配置的模块 logger（延迟初始化）
def get_apou_logger() -> logging.Logger:
    """获取 APoU 模块的 logger"""
    return logging.getLogger('AutoCCF.APoU')


def get_dopj_logger() -> logging.Logger:
    """获取 DoPJ 模块的 logger"""
    return logging.getLogger('AutoCCF.DoPJ')


def get_config_logger() -> logging.Logger:
    """获取配置模块的 logger"""
    return logging.getLogger('AutoCCF.Config')


# 便捷的日志级别常量
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL
