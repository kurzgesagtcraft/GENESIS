"""
GENESIS Workstation Module
工站系统模块

实现:
- WorkStation 基类
- Smelter 冶炼站
- Fabricator 加工站
- Assembler 装配站
- StationInterface 统一接口
- StationManager 管理器
"""

from .base_station import (
    WorkStation,
    StationState,
    StationConfig,
    StationStatus,
)
from .smelter import Smelter, SmelterConfig
from .fabricator import Fabricator, FabricatorConfig
from .assembler import Assembler, AssemblerConfig
from .station_interface import StationInterface
from .station_manager import StationManager

__all__ = [
    # 基类
    "WorkStation",
    "StationState",
    "StationConfig",
    "StationStatus",
    # 冶炼站
    "Smelter",
    "SmelterConfig",
    # 加工站
    "Fabricator",
    "FabricatorConfig",
    # 装配站
    "Assembler",
    "AssemblerConfig",
    # 接口
    "StationInterface",
    # 管理器
    "StationManager",
]
