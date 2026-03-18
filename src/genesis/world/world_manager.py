"""
GENESIS World Manager Module
世界管理器 - 统一管理仿真世界

实现:
- WorldManager 主类
- 世界构建与初始化
- 仿真步进控制
- 状态查询接口
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
import yaml
import numpy as np
from pathlib import Path

from genesis.utils.config import Configurable
from genesis.utils.types import Position3D

from .terrain import Terrain, TerrainConfig
from .mine_zone import MineZone, MineZoneConfig, OreType
from .solar_array import SolarArray, SolarArrayConfig
from .charging_dock import ChargingDock, ChargingDockConfig
from .path_network import PathNetwork, PathNetworkConfig
from .warehouse import Warehouse, WarehouseConfig
from .items import ItemRegistry
from .recipes import RecipeRegistry
from .recipe_graph import RecipeGraph


@dataclass
class WorldConfig:
  """世界配置"""
  name: str = "genesis_world"
  size: Tuple[float, float] = (50.0, 50.0)
  gravity: Tuple[float, float, float] = (0, 0, -9.81)
  time_step: float = 0.002  # 500Hz physics
  render_fps: int = 30
  
  terrain: Optional[TerrainConfig] = None
  zones: Dict[str, Any] = field(default_factory=dict)
  path_network: Optional[PathNetworkConfig] = None


class WorldManager(Configurable):
  """
  世界管理器 - 统一管理仿真世界
  
  功能:
  - 加载世界配置
  - 构建世界元素
  - 管理仿真步进
  - 提供状态查询接口
  
  Attributes:
    config: 世界配置
    terrain: 地形
    mines: 矿区列表
    solar_array: 太阳能阵列
    charging_dock: 充电站
    path_network: 道路网络
    warehouse: 仓库
    item_registry: 物品注册表
    recipe_registry: 配方注册表
    recipe_graph: 配方依赖图
  """
  
  def __init__(self, config_path: Optional[str] = None):
    """
    初始化世界管理器
    
    Args:
      config_path: 配置文件路径 (可选)
    """
    # 配置
    self.config: WorldConfig = WorldConfig()
    
    # 仿真上下文
    self._sim_context: Optional[Any] = None
    
    # 世界元素
    self.terrain: Optional[Terrain] = None
    self.mines: Dict[str, MineZone] = {}
    self.solar_array: Optional[SolarArray] = None
    self.charging_dock: Optional[ChargingDock] = None
    self.path_network: Optional[PathNetwork] = None
    self.warehouse: Optional[Warehouse] = None
    
    # 注册表
    self.item_registry: ItemRegistry = ItemRegistry()
    self.recipe_registry: RecipeRegistry = RecipeRegistry()
    self.recipe_graph: RecipeGraph = RecipeGraph(self.recipe_registry)
    
    # 仿真状态
    self.sim_time: float = 0.0
    self.energy_balance: float = 0.0  # 总能量收支 (Wh)
    self.is_built: bool = False
    
    # 加载配置
    if config_path:
      self.load_config(config_path)
  
  def load_config(self, config_path: str) -> None:
    """
    加载世界配置
    
    Args:
      config_path: 配置文件路径
    """
    path = Path(config_path)
    if not path.exists():
      raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
      config_dict = yaml.safe_load(f)
    
    self._parse_config(config_dict)
  
  def _parse_config(self, config_dict: Dict[str, Any]) -> None:
    """解析配置字典"""
    world = config_dict.get("world", {})
    
    # 基本配置
    self.config.name = world.get("name", "genesis_world")
    self.config.size = tuple(world.get("size", [50.0, 50.0]))
    self.config.gravity = tuple(world.get("gravity", [0, 0, -9.81]))
    self.config.time_step = world.get("time_step", 0.002)
    self.config.render_fps = world.get("render_fps", 30)
    
    # 地形配置
    terrain_dict = world.get("terrain", {})
    self.config.terrain = TerrainConfig(
      type=terrain_dict.get("type", "flat"),
      friction=terrain_dict.get("friction", 0.7),
      restitution=terrain_dict.get("restitution", 0.1),
    )
    
    # 区域配置
    zones = config_dict.get("zones", {})
    self.config.zones = zones
    
    # 道路网络配置
    path_dict = config_dict.get("path_network", {})
    if path_dict:
      self.config.path_network = PathNetworkConfig(
        name=path_dict.get("name", "path_network"),
        type=path_dict.get("type", "grid"),
        width=path_dict.get("width", 1.5),
        nodes=path_dict.get("nodes", []),
        edges=[tuple(e) for e in path_dict.get("edges", [])],
      )
  
  def build_world(self, sim_context: Any) -> None:
    """
    在仿真环境中构建完整世界
    
    Args:
      sim_context: 仿真上下文 (Isaac Sim 或 MuJoCo)
    """
    self._sim_context = sim_context
    
    # 1. 构建地形
    self._build_terrain()
    
    # 2. 构建矿区
    self._build_mines()
    
    # 3. 构建太阳能阵列
    self._build_solar_array()
    
    # 4. 构建充电站
    self._build_charging_dock()
    
    # 5. 构建道路网络
    self._build_path_network()
    
    # 6. 构建仓库
    self._build_warehouse()
    
    self.is_built = True
  
  def _build_terrain(self) -> None:
    """构建地形"""
    if self.config.terrain is None:
      self.config.terrain = TerrainConfig()
    
    self.terrain = Terrain(config=self.config.terrain)
    self.terrain.build(self._sim_context)
  
  def _build_mines(self) -> None:
    """构建矿区"""
    for zone_name, zone_config in self.config.zones.items():
      if zone_config.get("type") != "mine":
        continue
      
      mine_config = MineZoneConfig(
        name=zone_name,
        position=tuple(zone_config.get("position", [0, 0, 0])),
        size=tuple(zone_config.get("size", [8, 8, 0.5])),
        ore_type=OreType(zone_config.get("resource_type", "iron_ore")),
        total_units=zone_config.get("total_units", 100),
        terrain_roughness=zone_config.get("terrain_roughness", 0.3),
        respawn=zone_config.get("respawn", False),
      )
      
      mine = MineZone(mine_config)
      mine.build(self._sim_context)
      self.mines[zone_name] = mine
  
  def _build_solar_array(self) -> None:
    """构建太阳能阵列"""
    for zone_name, zone_config in self.config.zones.items():
      if zone_config.get("type") != "energy_source":
        continue
      
      solar_config = SolarArrayConfig(
        name=zone_name,
        position=tuple(zone_config.get("position", [0, 0, 0])),
        size=tuple(zone_config.get("size", [10, 5, 3])),
        energy_output_per_sec=zone_config.get("energy_output_per_sec", 100.0),
        efficiency=zone_config.get("efficiency", 0.85),
        day_night_cycle=zone_config.get("day_night_cycle", True),
        day_length=zone_config.get("day_length", 86400.0),
      )
      
      self.solar_array = SolarArray(solar_config)
      self.solar_array.build(self._sim_context)
      break  # 只有一个太阳能阵列
  
  def _build_charging_dock(self) -> None:
    """构建充电站"""
    for zone_name, zone_config in self.config.zones.items():
      if zone_config.get("type") != "charging":
        continue
      
      dock_config = ChargingDockConfig(
        name=zone_name,
        position=tuple(zone_config.get("position", [0, 0, 0])),
        size=tuple(zone_config.get("size", [2, 2, 1.5])),
        charge_rate=zone_config.get("charge_rate", 50.0),
        detection_radius=zone_config.get("detection_radius", 0.5),
      )
      
      self.charging_dock = ChargingDock(dock_config)
      self.charging_dock.build(self._sim_context)
      break  # 只有一个充电站
  
  def _build_path_network(self) -> None:
    """构建道路网络"""
    if self.config.path_network:
      self.path_network = PathNetwork(self.config.path_network)
      self.path_network.build(self._sim_context)
  
  def _build_warehouse(self) -> None:
    """构建仓库"""
    for zone_name, zone_config in self.config.zones.items():
      if zone_config.get("type") != "storage":
        continue
      
      warehouse_config = WarehouseConfig(
        name=zone_name,
        position=tuple(zone_config.get("position", [0, 0, 0])),
        size=tuple(zone_config.get("size", [8, 6, 4])),
        capacity=zone_config.get("capacity", 200),
        slot_grid=tuple(zone_config.get("slot_grid", [4, 3, 2])),
      )
      
      self.warehouse = Warehouse(warehouse_config)
      self.warehouse.build(self._sim_context)
      break  # 只有一个仓库
  
  def step(self, dt: float) -> None:
    """
    仿真步进
    
    Args:
      dt: 时间步长 (秒)
    """
    self.sim_time += dt
    
    # 更新太阳能发电
    if self.solar_array:
      energy = self.solar_array.step(dt, self.sim_time)
      self.energy_balance += energy
    
    # 更新矿区
    for mine in self.mines.values():
      mine.step(dt)
    
    # 更新充电站
    if self.charging_dock:
      self.charging_dock.step(dt)
    
    # 更新仓库
    if self.warehouse:
      self.warehouse.step(dt)
  
  def get_world_state(self) -> Dict[str, Any]:
    """
    获取完整世界状态 (供 Brain 使用)
    
    Returns:
      世界状态字典
    """
    return {
      "sim_time": self.sim_time,
      "energy_balance_wh": self.energy_balance,
      "mines": {
        name: mine.get_status()
        for name, mine in self.mines.items()
      },
      "solar_array": self.solar_array.get_status() if self.solar_array else None,
      "charging_dock": self.charging_dock.get_status() if self.charging_dock else None,
      "warehouse": self.warehouse.get_status() if self.warehouse else None,
      "path_network": self.path_network.get_status() if self.path_network else None,
      "inventory": self.warehouse.get_inventory() if self.warehouse else {},
    }
  
  def get_mine_remaining(self, mine_name: str) -> int:
    """
    获取矿区剩余矿石数量
    
    Args:
      mine_name: 矿区名称
      
    Returns:
      剩余数量
    """
    mine = self.mines.get(mine_name)
    if mine:
      return mine.remaining_count
    return 0
  
  def get_all_mine_remaining(self) -> Dict[str, int]:
    """获取所有矿区剩余数量"""
    return {
      name: mine.remaining_count
      for name, mine in self.mines.items()
    }
  
  def get_zone_position(self, zone_name: str) -> Optional[Tuple[float, float, float]]:
    """
    获取区域位置
    
    Args:
      zone_name: 区域名称
      
    Returns:
      位置坐标, 如果不存在返回 None
    """
    zone_config = self.config.zones.get(zone_name)
    if zone_config:
      return tuple(zone_config.get("position", [0, 0, 0]))
    
    # 检查道路网络节点
    if self.path_network:
      node = self.path_network.get_node_by_zone(zone_name)
      if node:
        return (node.position[0], node.position[1], 0.0)
    
    return None
  
  def plan_path(
    self,
    start_zone: str,
    end_zone: str
  ) -> List[Tuple[float, float]]:
    """
    规划路径
    
    Args:
      start_zone: 起点区域
      end_zone: 终点区域
      
    Returns:
      路径点列表 [(x, y), ...]
    """
    if not self.path_network:
      return []
    
    path = self.path_network.plan_path(start_zone, end_zone)
    return self.path_network.get_path_positions(path)
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "config": {
        "name": self.config.name,
        "size": list(self.config.size),
        "gravity": list(self.config.gravity),
        "time_step": self.config.time_step,
        "render_fps": self.config.render_fps,
      },
      "state": {
        "sim_time": self.sim_time,
        "energy_balance_wh": self.energy_balance,
        "is_built": self.is_built,
      },
      "elements": {
        "terrain": self.terrain.to_dict() if self.terrain else None,
        "mines": {
          name: mine.to_dict()
          for name, mine in self.mines.items()
        },
        "solar_array": self.solar_array.to_dict() if self.solar_array else None,
        "charging_dock": self.charging_dock.to_dict() if self.charging_dock else None,
        "path_network": self.path_network.to_dict() if self.path_network else None,
        "warehouse": self.warehouse.to_dict() if self.warehouse else None,
      },
      "registries": {
        "items": self.item_registry.to_dict(),
        "recipes": self.recipe_registry.to_dict(),
      },
    }
  
  @classmethod
  def from_config(cls, config_dict: Dict[str, Any]) -> "WorldManager":
    """从配置字典创建"""
    manager = cls()
    manager._parse_config(config_dict)
    return manager
