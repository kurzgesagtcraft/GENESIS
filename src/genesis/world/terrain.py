"""
GENESIS Terrain Module
地形与天空构建

实现:
- 地面平面 (GroundPlane)
- 摩擦系数材质
- 天空盒
- 平行光源 (太阳)
- 环境光
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any
import numpy as np

from genesis.utils.types import Position3D, Color
from genesis.utils.config import Configurable


@dataclass
class TerrainConfig:
  """地形配置"""
  type: str = "flat"  # flat / heightfield / mesh
  friction: float = 0.7
  restitution: float = 0.1
  size: Tuple[float, float] = (50.0, 50.0)
  color: Color = field(default_factory=lambda: Color(0.6, 0.6, 0.6, 1.0))
  heightfield_data: Optional[np.ndarray] = None  # for heightfield type
  height_scale: float = 1.0


@dataclass
class LightingConfig:
  """光照配置"""
  type: str = "outdoor"  # outdoor / indoor
  sun_intensity: float = 1.0
  ambient_intensity: float = 0.3
  sun_direction: Tuple[float, float, float] = (0.5, 0.5, -1.0)
  sun_color: Color = field(default_factory=lambda: Color(1.0, 0.95, 0.8, 1.0))
  ambient_color: Color = field(default_factory=lambda: Color(0.4, 0.45, 0.5, 1.0))


class Terrain(Configurable):
  """
  地形类 - 管理地面和天空
  
  支持多种地形类型:
  - flat: 平坦地面
  - heightfield: 高度场地形 (用于矿区凹凸地形)
  - mesh: 网格地形 (自定义模型)
  
  Attributes:
    config: 地形配置
    lighting_config: 光照配置
    ground_id: 地面物理体ID (仿真引擎返回)
    sky_id: 天空盒ID
  """
  
  def __init__(
    self,
    config: Optional[TerrainConfig] = None,
    lighting_config: Optional[LightingConfig] = None
  ):
    self.config = config or TerrainConfig()
    self.lighting_config = lighting_config or LightingConfig()
    
    # 仿真引擎引用 (由 WorldManager 注入)
    self._sim_context: Optional[Any] = None
    
    # 物理体ID
    self.ground_id: Optional[int] = None
    self.sky_id: Optional[int] = None
    
    # 材质ID
    self.ground_material_id: Optional[int] = None
    
  def build(self, sim_context: Any) -> None:
    """
    在仿真环境中构建地形
    
    Args:
      sim_context: 仿真上下文 (Isaac Sim 或 MuJoCo)
    """
    self._sim_context = sim_context
    
    # 根据引擎类型选择构建方法
    engine_type = getattr(sim_context, 'engine_type', 'unknown')
    
    if engine_type == 'isaac_sim':
      self._build_isaac_sim()
    elif engine_type == 'mujoco':
      self._build_mujoco()
    else:
      # 默认使用抽象构建 (用于测试)
      self._build_abstract()
  
  def _build_isaac_sim(self) -> None:
    """Isaac Sim 构建实现"""
    try:
      from omni.isaac.core.objects import GroundPlane
      from omni.isaac.core.utils.stage import add_reference_to_stage
      import omni.replicator.core as rep
      
      # 创建地面平面
      ground = GroundPlane(
        prim_path="/World/Ground",
        name="ground",
        size=self.config.size[0],  # 正方形
        z_position=0.0,
        color=np.array([
          self.config.color.r,
          self.config.color.g,
          self.config.color.b
        ])
      )
      
      # 设置摩擦系数
      # TODO: 通过 PhysX 材质设置摩擦
      
      # 添加天空盒
      self._add_skybox_isaac()
      
      # 添加光照
      self._add_lighting_isaac()
      
      self.ground_id = id(ground)
      
    except ImportError:
      # Isaac Sim 未安装,使用抽象构建
      self._build_abstract()
  
  def _build_mujoco(self) -> None:
    """MuJoCo 构建实现"""
    # MuJoCo 中地形通过 XML 定义
    # 这里创建一个简单的平面
    self.ground_id = 0  # MuJoCo 默认地面
    self._build_abstract()
  
  def _build_abstract(self) -> None:
    """抽象构建 (用于测试和无引擎环境)"""
    self.ground_id = -1  # 抽象ID
    self.sky_id = -1
  
  def _add_skybox_isaac(self) -> None:
    """添加 Isaac Sim 天空盒"""
    try:
      import omni.replicator.core as rep
      
      # 使用内置天空盒
      rep.create.skybox(
        texture="assets/textures/sky.hdr",  # 可选自定义纹理
        prim_path="/World/Sky"
      )
      self.sky_id = -1
      
    except Exception:
      pass
  
  def _add_lighting_isaac(self) -> None:
    """添加 Isaac Sim 光照"""
    try:
      from omni.isaac.core.utils.stage import get_current_stage
      from pxr import UsdLux
      
      stage = get_current_stage()
      
      # 创建平行光 (太阳)
      sun_path = "/World/Sun"
      UsdLux.DistantLight.Define(stage, sun_path)
      sun_prim = stage.GetPrimAtPath(sun_path)
      
      sun_prim.GetAttribute('intensity').Set(
        self.lighting_config.sun_intensity * 1000
      )
      sun_prim.GetAttribute('angle').Set(0.53)  # 太阳角度
      
      # 设置方向
      direction = self.lighting_config.sun_direction
      sun_prim.GetAttribute('xformOp:rotateXYZ').Set(
        self._direction_to_euler(direction)
      )
      
      # 环境光
      UsdLux.DomeLight.Define(stage, "/World/AmbientLight")
      ambient = stage.GetPrimAtPath("/World/AmbientLight")
      ambient.GetAttribute('intensity').Set(
        self.lighting_config.ambient_intensity * 100
      )
      
    except Exception:
      pass
  
  def _direction_to_euler(
    self,
    direction: Tuple[float, float, float]
  ) -> Tuple[float, float, float]:
    """将方向向量转换为欧拉角"""
    dx, dy, dz = direction
    # 简化计算
    azimuth = np.arctan2(dy, dx)
    elevation = np.arcsin(-dz / np.linalg.norm(direction))
    return (np.degrees(elevation), np.degrees(azimuth), 0.0)
  
  def get_height_at(self, x: float, y: float) -> float:
    """
    获取指定位置的地形高度
    
    Args:
      x: X 坐标
      y: Y 坐标
      
    Returns:
      地形高度 (flat 类型返回 0)
    """
    if self.config.type == "flat":
      return 0.0
    elif self.config.type == "heightfield":
      if self.config.heightfield_data is None:
        return 0.0
      # 插值计算高度
      # TODO: 实现双线性插值
      return 0.0
    return 0.0
  
  def get_friction(self) -> float:
    """获取摩擦系数"""
    return self.config.friction
  
  def get_restitution(self) -> float:
    """获取弹性系数"""
    return self.config.restitution
  
  def get_sun_intensity(self, sim_time: float) -> float:
    """
    获取当前太阳光照强度 (考虑日夜循环)
    
    Args:
      sim_time: 仿真时间 (秒)
      
    Returns:
      光照强度 (0-1)
    """
    # 简化的日夜循环模型
    # 假设一天 = 86400 秒
    day_length = 86400.0
    phase = (sim_time % day_length) / day_length
    
    # 日出 6:00 (0.25), 日落 18:00 (0.75)
    # 白天强度高, 夜晚强度低
    if 0.25 <= phase <= 0.75:
      # 白天
      # 正弦曲线模拟日出日落
      day_phase = (phase - 0.25) / 0.5  # 0-1
      intensity = np.sin(day_phase * np.pi)
    else:
      # 夜晚
      intensity = 0.1  # 月光
    
    return intensity * self.lighting_config.sun_intensity
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "type": self.config.type,
      "friction": self.config.friction,
      "restitution": self.config.restitution,
      "size": self.config.size,
      "lighting": {
        "sun_intensity": self.lighting_config.sun_intensity,
        "ambient_intensity": self.lighting_config.ambient_intensity,
        "sun_direction": self.lighting_config.sun_direction,
      }
    }
  
  @classmethod
  def from_config(cls, config_dict: Dict[str, Any]) -> "Terrain":
    """从配置字典创建"""
    terrain_config = TerrainConfig(
      type=config_dict.get("type", "flat"),
      friction=config_dict.get("friction", 0.7),
      restitution=config_dict.get("restitution", 0.1),
    )
    
    lighting_dict = config_dict.get("lighting", {})
    lighting_config = LightingConfig(
      type=lighting_dict.get("type", "outdoor"),
      sun_intensity=lighting_dict.get("sun_intensity", 1.0),
      ambient_intensity=lighting_dict.get("ambient_intensity", 0.3),
      sun_direction=tuple(lighting_dict.get("sun_direction", [0.5, 0.5, -1.0])),
    )
    
    return cls(config=terrain_config, lighting_config=lighting_config)
