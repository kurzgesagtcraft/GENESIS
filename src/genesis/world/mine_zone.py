"""
GENESIS Mine Zone Module
矿区构建与管理

实现:
- 矿区地面 (凹凸不平的 heightfield 地形)
- 矿石对象生成 (不规则多面体)
- Poisson 分布随机散布
- RigidBody 物理属性
- Semantic Label (用于视觉识别)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from enum import Enum
import uuid

from genesis.utils.types import Position3D, Color
from genesis.utils.config import Configurable


class OreType(Enum):
  """矿石类型"""
  IRON = "iron_ore"
  SILICON = "silicon_ore"
  COPPER = "copper_ore"
  GOLD = "gold_ore"


@dataclass
class OreProperties:
  """矿石物理属性"""
  ore_type: OreType
  mass: float  # kg
  size: Tuple[float, float, float]  # bounding box (m)
  color: Color
  friction: float = 0.8
  restitution: float = 0.2
  value: float = 1.0  # 基础价值
  
  @classmethod
  def get_defaults(cls) -> Dict[OreType, "OreProperties"]:
    """获取默认矿石属性"""
    return {
      OreType.IRON: cls(
        ore_type=OreType.IRON,
        mass=2.0,
        size=(0.1, 0.1, 0.1),
        color=Color(0.6, 0.3, 0.2, 1.0),  # 棕红色
        friction=0.8,
        restitution=0.2,
        value=1.0
      ),
      OreType.SILICON: cls(
        ore_type=OreType.SILICON,
        mass=1.5,
        size=(0.08, 0.08, 0.08),
        color=Color(0.5, 0.5, 0.55, 1.0),  # 灰色
        friction=0.7,
        restitution=0.15,
        value=1.5
      ),
    }


@dataclass
class OreObject:
  """单个矿石对象"""
  ore_id: str
  ore_type: OreType
  position: Position3D
  rotation: Tuple[float, float, float, float]  # quaternion (w, x, y, z)
  properties: OreProperties
  is_collected: bool = False
  rigid_body_id: Optional[int] = None
  
  def to_dict(self) -> Dict[str, Any]:
    return {
      "ore_id": self.ore_id,
      "ore_type": self.ore_type.value,
      "position": [self.position.x, self.position.y, self.position.z],
      "rotation": list(self.rotation),
      "is_collected": self.is_collected,
    }


@dataclass
class MineZoneConfig:
  """矿区配置"""
  name: str
  position: Tuple[float, float, float]  # 中心位置
  size: Tuple[float, float, float]  # 区域尺寸
  ore_type: OreType
  total_units: int  # 总矿石数量
  terrain_roughness: float = 0.3  # 地形粗糙度
  respawn: bool = False  # 是否重生
  respawn_interval: float = 60.0  # 重生间隔 (秒)


class MineZone(Configurable):
  """
  矿区类 - 管理矿石生成和状态
  
  功能:
  - 生成矿区地形 (heightfield)
  - 随机散布矿石 (Poisson 分布)
  - 管理矿石状态 (已采集/剩余)
  - 提供矿石查询接口
  
  Attributes:
    config: 矿区配置
    ores: 矿石对象列表
    remaining_count: 剩余矿石数量
  """
  
  def __init__(self, config: MineZoneConfig):
    self.config = config
    self.ores: List[OreObject] = []
    self.remaining_count: int = config.total_units
    self._sim_context: Optional[Any] = None
    
    # 地形数据
    self._heightfield: Optional[np.ndarray] = None
    
    # 统计数据
    self.total_collected: int = 0
    self.collection_history: List[Dict[str, Any]] = []
    
  def build(self, sim_context: Any) -> None:
    """
    在仿真环境中构建矿区
    
    Args:
      sim_context: 仿真上下文
    """
    self._sim_context = sim_context
    
    # 生成地形
    self._generate_heightfield()
    
    # 生成矿石
    self._generate_ores()
    
    # 根据引擎类型构建
    engine_type = getattr(sim_context, 'engine_type', 'unknown')
    
    if engine_type == 'isaac_sim':
      self._build_isaac_sim()
    elif engine_type == 'mujoco':
      self._build_mujoco()
    else:
      self._build_abstract()
  
  def _generate_heightfield(self) -> None:
    """生成 heightfield 地形数据"""
    # 网格分辨率
    resolution = 50
    x = np.linspace(0, self.config.size[0], resolution)
    y = np.linspace(0, self.config.size[1], resolution)
    xx, yy = np.meshgrid(x, y)
    
    # 使用 Perlin 噪声或简单正弦叠加
    roughness = self.config.terrain_roughness
    
    # 多频率叠加模拟自然地形
    height = (
      np.sin(xx * 0.5) * np.cos(yy * 0.5) * roughness * 0.3 +
      np.sin(xx * 1.5 + 0.5) * np.cos(yy * 1.5 + 0.3) * roughness * 0.15 +
      np.sin(xx * 3.0) * np.cos(yy * 3.0) * roughness * 0.05
    )
    
    # 添加随机噪声
    height += np.random.randn(resolution, resolution) * roughness * 0.02
    
    self._heightfield = height
  
  def _generate_ores(self) -> None:
    """使用 Poisson 分布生成矿石位置"""
    # Poisson 圆盘采样参数
    min_distance = 0.3  # 矿石最小间距 (m)
    width = self.config.size[0]
    height = self.config.size[1]
    
    # 生成采样点
    points = self._poisson_disk_sampling(
      width, height, min_distance, self.config.total_units
    )
    
    # 获取矿石属性
    ore_props = OreProperties.get_defaults()[self.config.ore_type]
    
    # 创建矿石对象
    for i, (px, py) in enumerate(points[:self.config.total_units]):
      # 计算高度 (基于 heightfield)
      pz = self._get_height_at_local(px, py) + ore_props.size[2] / 2
      
      # 随机旋转
      rotation = self._random_rotation()
      
      ore = OreObject(
        ore_id=f"{self.config.name}_ore_{i:04d}",
        ore_type=self.config.ore_type,
        position=Position3D(
          self.config.position[0] + px - width/2,
          self.config.position[1] + py - height/2,
          self.config.position[2] + pz
        ),
        rotation=rotation,
        properties=ore_props
      )
      self.ores.append(ore)
  
  def _poisson_disk_sampling(
    self,
    width: float,
    height: float,
    min_dist: float,
    num_points: int
  ) -> List[Tuple[float, float]]:
    """
    Poisson 圆盘采样
    
    生成均匀分布但不过于规则的点集
    """
    points = []
    cell_size = min_dist / np.sqrt(2)
    grid_w = int(np.ceil(width / cell_size))
    grid_h = int(np.ceil(height / cell_size))
    grid = np.full((grid_w, grid_h), -1)
    
    # 初始点
    first_point = (
      np.random.uniform(0, width),
      np.random.uniform(0, height)
    )
    points.append(first_point)
    
    # 活跃列表
    active = [0]
    
    while active and len(points) < num_points * 2:  # 多生成一些备用
      rand_idx = np.random.randint(len(active))
      point_idx = active[rand_idx]
      point = points[point_idx]
      
      found = False
      for _ in range(30):  # 每个点尝试30次
        # 在环形区域随机采样
        angle = np.random.uniform(0, 2 * np.pi)
        dist = np.random.uniform(min_dist, 2 * min_dist)
        new_point = (
          point[0] + dist * np.cos(angle),
          point[1] + dist * np.sin(angle)
        )
        
        # 检查边界
        if not (0 <= new_point[0] < width and 0 <= new_point[1] < height):
          continue
        
        # 检查最小距离
        grid_x = int(new_point[0] / cell_size)
        grid_y = int(new_point[1] / cell_size)
        
        # 检查邻近格子
        valid = True
        for dx in [-1, 0, 1]:
          for dy in [-1, 0, 1]:
            nx, ny = grid_x + dx, grid_y + dy
            if 0 <= nx < grid_w and 0 <= ny < grid_h:
              neighbor_idx = grid[nx, ny]
              if neighbor_idx >= 0:
                neighbor = points[neighbor_idx]
                dist_to_neighbor = np.sqrt(
                  (new_point[0] - neighbor[0])**2 +
                  (new_point[1] - neighbor[1])**2
                )
                if dist_to_neighbor < min_dist:
                  valid = False
                  break
            if not valid:
              break
          if not valid:
            break
        
        if valid:
          points.append(new_point)
          grid[grid_x, grid_y] = len(points) - 1
          active.append(len(points) - 1)
          found = True
          break
      
      if not found:
        active.pop(rand_idx)
    
    return points[:num_points]
  
  def _get_height_at_local(self, x: float, y: float) -> float:
    """获取局部坐标的高度"""
    if self._heightfield is None:
      return 0.0
    
    # 双线性插值
    resolution = self._heightfield.shape[0]
    width = self.config.size[0]
    height = self.config.size[1]
    
    # 归一化坐标
    nx = x / width * (resolution - 1)
    ny = y / height * (resolution - 1)
    
    # 边界检查
    nx = np.clip(nx, 0, resolution - 2)
    ny = np.clip(ny, 0, resolution - 2)
    
    # 整数和小数部分
    ix, iy = int(nx), int(ny)
    fx, fy = nx - ix, ny - iy
    
    # 双线性插值
    h00 = self._heightfield[iy, ix]
    h10 = self._heightfield[iy, ix + 1]
    h01 = self._heightfield[iy + 1, ix]
    h11 = self._heightfield[iy + 1, ix + 1]
    
    h = (
      h00 * (1 - fx) * (1 - fy) +
      h10 * fx * (1 - fy) +
      h01 * (1 - fx) * fy +
      h11 * fx * fy
    )
    
    return h
  
  def _random_rotation(self) -> Tuple[float, float, float, float]:
    """生成随机四元数旋转"""
    # 均匀分布的随机四元数
    u1 = np.random.uniform(0, 1)
    u2 = np.random.uniform(0, 2 * np.pi)
    u3 = np.random.uniform(0, 2 * np.pi)
    
    w = np.sqrt(1 - u1)
    x = np.sqrt(u1) * np.cos(u2)
    y = np.sqrt(u1) * np.sin(u2)
    z = np.sqrt(1 - u1) * np.sin(u3)
    
    return (w, x, y, z)
  
  def _build_isaac_sim(self) -> None:
    """Isaac Sim 构建"""
    try:
      from omni.isaac.core.objects import DynamicSphere
      from omni.isaac.core.utils.stage import get_current_stage
      from pxr import UsdGeom, Gf
      
      stage = get_current_stage()
      
      # 创建矿区地形 (简化: 使用 GroundPlane + heightfield)
      # TODO: 实现完整的 heightfield 地形
      
      # 创建矿石
      for ore in self.ores:
        if ore.is_collected:
          continue
        
        # 创建不规则几何体 (简化为球体)
        # TODO: 使用更真实的矿石网格
        prim_path = f"/World/Mines/{self.config.name}/{ore.ore_id}"
        
        # 使用 DynamicSphere 作为简化模型
        # 实际应使用自定义网格
        ore.rigid_body_id = hash(prim_path)
        
    except ImportError:
      self._build_abstract()
  
  def _build_mujoco(self) -> None:
    """MuJoCo 构建"""
    self._build_abstract()
  
  def _build_abstract(self) -> None:
    """抽象构建"""
    for i, ore in enumerate(self.ores):
      ore.rigid_body_id = i
  
  def collect_ore(self, ore_id: str) -> Optional[OreObject]:
    """
    采集矿石
    
    Args:
      ore_id: 矿石ID
      
    Returns:
      被采集的矿石对象, 如果不存在返回 None
    """
    for ore in self.ores:
      if ore.ore_id == ore_id and not ore.is_collected:
        ore.is_collected = True
        self.remaining_count -= 1
        self.total_collected += 1
        
        # 记录采集历史
        self.collection_history.append({
          "ore_id": ore_id,
          "ore_type": ore.ore_type.value,
          "timestamp": getattr(self._sim_context, 'sim_time', 0),
        })
        
        return ore
    return None
  
  def get_nearest_ore(
    self,
    position: Position3D,
    max_distance: float = 5.0
  ) -> Optional[OreObject]:
    """
    获取最近的未采集矿石
    
    Args:
      position: 查询位置
      max_distance: 最大搜索距离
      
    Returns:
      最近的矿石对象, 如果没有返回 None
    """
    nearest = None
    min_dist = max_distance
    
    for ore in self.ores:
      if ore.is_collected:
        continue
      
      dist = np.sqrt(
        (ore.position.x - position.x)**2 +
        (ore.position.y - position.y)**2 +
        (ore.position.z - position.z)**2
      )
      
      if dist < min_dist:
        min_dist = dist
        nearest = ore
    
    return nearest
  
  def get_ores_in_radius(
    self,
    position: Position3D,
    radius: float
  ) -> List[OreObject]:
    """
    获取指定半径内的所有未采集矿石
    
    Args:
      position: 查询位置
      radius: 搜索半径
      
    Returns:
    矿石对象列表
    """
    ores_in_radius = []
    
    for ore in self.ores:
      if ore.is_collected:
        continue
      
      dist = np.sqrt(
        (ore.position.x - position.x)**2 +
        (ore.position.y - position.y)**2 +
        (ore.position.z - position.z)**2
      )
      
      if dist <= radius:
        ores_in_radius.append(ore)
    
    return ores_in_radius
  
  def step(self, dt: float) -> None:
    """
    仿真步进
    
    Args:
      dt: 时间步长
    """
    # 处理重生逻辑
    if self.config.respawn:
      # TODO: 实现矿石重生
      pass
  
  def get_status(self) -> Dict[str, Any]:
    """获取矿区状态"""
    return {
      "name": self.config.name,
      "ore_type": self.config.ore_type.value,
      "total_units": self.config.total_units,
      "remaining": self.remaining_count,
      "collected": self.total_collected,
      "position": list(self.config.position),
      "size": list(self.config.size),
    }
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "config": {
        "name": self.config.name,
        "position": list(self.config.position),
        "size": list(self.config.size),
        "ore_type": self.config.ore_type.value,
        "total_units": self.config.total_units,
        "terrain_roughness": self.config.terrain_roughness,
        "respawn": self.config.respawn,
      },
      "status": self.get_status(),
    }
  
  @classmethod
  def from_config(cls, config_dict: Dict[str, Any]) -> "MineZone":
    """从配置字典创建"""
    ore_type = OreType(config_dict.get("resource_type", "iron_ore"))
    
    zone_config = MineZoneConfig(
      name=config_dict.get("name", "mine"),
      position=tuple(config_dict.get("position", [0, 0, 0])),
      size=tuple(config_dict.get("size", [8, 8, 0.5])),
      ore_type=ore_type,
      total_units=config_dict.get("total_units", 100),
      terrain_roughness=config_dict.get("terrain_roughness", 0.3),
      respawn=config_dict.get("respawn", False),
    )
    
    return cls(zone_config)
