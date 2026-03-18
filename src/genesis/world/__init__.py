"""
GENESIS World Module
仿真世界构建模块

包含:
- terrain: 地形与天空
- mine_zone: 矿区
- solar_array: 太阳能发电区
- charging_dock: 充电站
- path_network: 道路网络
- warehouse: 仓库
- items: 物品系统
- recipes: 配方系统
- world_manager: 世界管理器
"""

from .terrain import Terrain
from .mine_zone import MineZone
from .solar_array import SolarArray, EnergySource
from .charging_dock import ChargingDock
from .path_network import PathNetwork
from .warehouse import Warehouse
from .items import Item, ItemRegistry
from .recipes import Recipe, RecipeRegistry
from .world_manager import WorldManager

__all__ = [
    "Terrain",
    "MineZone",
    "SolarArray",
    "EnergySource",
    "ChargingDock",
    "PathNetwork",
    "Warehouse",
    "Item",
    "ItemRegistry",
    "Recipe",
    "RecipeRegistry",
    "WorldManager",
]
