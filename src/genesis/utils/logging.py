"""
GENESIS Logging Module - 日志管理模块

提供统一的日志配置和获取接口。
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# 默认日志格式
DEFAULT_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日志级别映射
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class ColorFormatter(logging.Formatter):
    """彩色日志格式化器。"""
    
    # ANSI 颜色代码
    COLORS = {
        "DEBUG": "\033[36m",     # 青色
        "INFO": "\033[32m",      # 绿色
        "WARNING": "\033[33m",   # 黄色
        "ERROR": "\033[31m",     # 红色
        "CRITICAL": "\033[35m",  # 紫色
        "RESET": "\033[0m",      # 重置
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录。"""
        # 添加颜色
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        return super().format(record)


def setup_logger(
    name: str = "genesis",
    level: str = "info",
    log_file: Optional[Union[str, Path]] = None,
    console: bool = True,
    color: bool = True,
) -> logging.Logger:
    """
    设置并返回日志记录器。
    
    Args:
        name: 日志记录器名称
        level: 日志级别 (debug, info, warning, error, critical)
        log_file: 日志文件路径，None 表示不写入文件
        console: 是否输出到控制台
        color: 是否使用彩色输出
        
    Returns:
        配置好的日志记录器
        
    Example:
        >>> logger = setup_logger("genesis", level="debug")
        >>> logger.info("System initialized")
    """
    # 获取或创建日志记录器
    logger = logging.getLogger(name)
    
    # 避免重复配置
    if logger.handlers:
        return logger
    
    # 设置日志级别
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    logger.setLevel(log_level)
    
    # 创建格式化器
    if color and console:
        formatter: logging.Formatter = ColorFormatter(
            DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT
        )
    else:
        formatter = logging.Formatter(
            DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT
        )
    
    # 控制台处理器
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 文件处理器
    if log_file is not None:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter(DEFAULT_FORMAT, datefmt=DEFAULT_DATE_FORMAT)
        )
        logger.addHandler(file_handler)
    
    # 防止日志传播到根日志记录器
    logger.propagate = False
    
    return logger


def get_logger(name: str = "genesis") -> logging.Logger:
    """
    获取已配置的日志记录器。
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器
        
    Example:
        >>> logger = get_logger("genesis.world")
        >>> logger.debug("Loading world...")
    """
    return logging.getLogger(name)


# 模块级默认日志记录器
_default_logger: Optional[logging.Logger] = None


def get_default_logger() -> logging.Logger:
    """获取默认日志记录器，如果不存在则创建。"""
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logger("genesis")
    return _default_logger


def log_section(title: str, width: int = 60, char: str = "=") -> None:
    """
    打印分节标题。
    
    Args:
        title: 标题文本
        width: 总宽度
        char: 分隔字符
    """
    logger = get_default_logger()
    border = char * width
    padding = (width - len(title) - 2) // 2
    centered_title = f"{' ' * padding} {title} {' ' * padding}"
    if len(centered_title) < width:
        centered_title += " " * (width - len(centered_title))
    logger.info(border)
    logger.info(centered_title)
    logger.info(border)


# 类型导入
from typing import Union
