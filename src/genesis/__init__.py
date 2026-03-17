"""
GENESIS - Generalized Embodied Neural Entity for Self-Iterating Synthesis

机器人自复制最小闭环模拟系统
"""

__version__ = "0.1.0"
__author__ = "GENESIS Team"

from genesis.utils.config import load_config
from genesis.utils.logging import setup_logger

__all__ = [
    "__version__",
    "__author__",
    "load_config",
    "setup_logger",
]
