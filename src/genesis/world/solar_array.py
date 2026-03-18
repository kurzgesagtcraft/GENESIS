"""
GENESIS Solar Array Module
太阳能发电区构建与管理

实现:
- 太阳能板3D模型
- EnergySource 逻辑类
- 日照周期模拟
- 发电效率计算
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from enum import Enum

from genesis.utils.types import Position3D, Color
from genesis.utils.config import Configurable


@dataclass
class SolarPanelConfig:
  """太阳能板配置"""
  position: Tuple[float, float, float]
  size: Tuple[float, float, float]  # (width, height, thickness)
  efficiency: float = 0.85  # 转换效率
  max_output_watts: float = 100.0  # 最大输出功率
  tilt_angle: float = 30.0  # 倾斜角度 (度)
  azimuth: float = 180.0  # 方位角 (度, 正南为180)


class EnergySource:
  """
  能源源类 - 管理能源输出
  
  功能:
  - 计算当前发电功率
  - 模拟日照周期
  - 跟踪累计发电量
  
  Attributes:
    config: 太阳能板配置
    current_output: 当前输出功率 (W)
    total_generated: 累计发电量 (Wh)
  """
  
  def __init__(self, config: SolarPanelConfig):
    self.config = config
    self.current_output: float = 0.0
    self.total_generated: float = 0.0  # Wh
    
    # 日照周期参数
    self.day_length: float = 86400.0  # 秒 (24小时)
    self.sunrise_hour: float = 6.0  # 日出时间
    self.sunset_hour: float = 18.0  # 日落时间
    self.peak_hour: float = 12.0  # 正午
    
    # 天气影响因子 (0-1)
    self.weather_factor: float = 1.0
    
  def get_current_output(self, sim_time: float) -> float:
    """
    获取当前发电功率
    
    考虑因素:
    - 日照周期 (日夜变化)
    - 太阳高度角
    - 天气影响
    - 面板效率
    
    Args:
      sim_time: 仿真时间 (秒)
      
    Returns:
      当前输出功率 (W)
    """
    # 计算一天中的时间 (小时)
    hour = (sim_time % self.day_length) / 3600.0
    
    # 检查是否在日照时间
    if hour < self.sunrise_hour or hour > self.sunset_hour:
      self.current_output = 0.0
      return 0.0
    
    # 计算太阳高度角因子
    # 使用正弦曲线模拟日出日落
    day_progress = (hour - self.sunrise_hour) / (self.sunset_hour - self.sunrise_hour)
    sun_factor = np.sin(day_progress * np.pi)
    
    # 考虑倾斜角度的影响
    # 简化模型: 假设倾斜角为最优角度时效率最高
    tilt_rad = np.radians(self.config.tilt_angle)
    tilt_factor = np.cos(tilt_rad - np.radians(30))  # 30度为理想角度
    
    # 综合计算输出
    output = (
      self.config.max_output_watts *
      self.config.efficiency *
      sun_factor *
      tilt_factor *
      self.weather_factor
    )
    
    # 添加随机波动 (模拟云遮挡等)
    noise = np.random.normal(1.0, 0.05)
    output *= max(0.5, min(1.2, noise))
    
    self.current_output = max(0.0, output)
    return self.current_output
  
  def step(self, dt: float, sim_time: float) -> float:
    """
    仿真步进
    
    Args:
      dt: 时间步长 (秒)
      sim_time: 当前仿真时间 (秒)
      
    Returns:
      本步产生的能量 (Wh)
    """
    output = self.get_current_output(sim_time)
    energy = output * dt / 3600.0  # 转换为 Wh
    self.total_generated += energy
    return energy
  
  def set_weather_factor(self, factor: float) -> None:
    """
    设置天气影响因子
    
    Args:
      factor: 天气因子 (0-1)
        - 1.0: 晴天
        - 0.7: 多云
        - 0.3: 阴天
        - 0.0: 夜晚/暴雨
    """
    self.weather_factor = np.clip(factor, 0.0, 1.0)
  
  def get_status(self) -> Dict[str, Any]:
    """获取状态"""
    return {
      "current_output_watts": self.current_output,
      "total_generated_wh": self.total_generated,
      "efficiency": self.config.efficiency,
      "weather_factor": self.weather_factor,
    }


@dataclass
class SolarArrayConfig:
  """太阳能阵列配置"""
  name: str = "solar_array"
  position: Tuple[float, float, float] = (0, 0, 0)
  size: Tuple[float, float, float] = (10, 5, 3)
  energy_output_per_sec: float = 100.0  # Watts
  efficiency: float = 0.85
  day_night_cycle: bool = True
  day_length: float = 86400.0  # seconds
  num_panels: int = 4  # 面板数量


class SolarArray(Configurable):
  """
  太阳能阵列类 - 管理多个太阳能板
  
  功能:
  - 创建太阳能板3D模型
  - 管理多个 EnergySource
  - 汇总发电数据
  
  Attributes:
    config: 阵列配置
    panels: 太阳能板列表
    energy_sources: 能源源列表
  """
  
  def __init__(self, config: SolarArrayConfig):
    self.config = config
    self.panels: List[SolarPanelConfig] = []
    self.energy_sources: List[EnergySource] = []
    
    self._sim_context: Optional[Any] = None
    
    # 总发电统计
    self.total_output: float = 0.0
    self.total_generated: float = 0.0
    
    # 初始化面板
    self._init_panels()
  
  def _init_panels(self) -> None:
    """初始化太阳能板"""
    # 计算单个面板尺寸
    panel_width = self.config.size[0] / 2
    panel_height = self.config.size[1] / 2
    
    # 创建面板网格
    for i in range(self.config.num_panels):
      row = i // 2
      col = i % 2
      
      panel_config = SolarPanelConfig(
        position=(
          self.config.position[0] + col * panel_width,
          self.config.position[1] + row * panel_height,
          self.config.position[2] + 0.1  # 略高于地面
        ),
        size=(panel_width * 0.9, panel_height * 0.9, 0.05),
        efficiency=self.config.efficiency,
        max_output_watts=self.config.energy_output_per_sec / self.config.num_panels,
        tilt_angle=30.0,
        azimuth=180.0  # 朝南
      )
      
      self.panels.append(panel_config)
      self.energy_sources.append(EnergySource(panel_config))
  
  def build(self, sim_context: Any) -> None:
    """
    在仿真环境中构建太阳能阵列
    
    Args:
      sim_context: 仿真上下文
    """
    self._sim_context = sim_context
    
    engine_type = getattr(sim_context, 'engine_type', 'unknown')
    
    if engine_type == 'isaac_sim':
      self._build_isaac_sim()
    elif engine_type == 'mujoco':
      self._build_mujoco()
    else:
      self._build_abstract()
  
  def _build_isaac_sim(self) -> None:
    """Isaac Sim 构建"""
    try:
      from omni.isaac.core.objects import DynamicCuboid
      from pxr import UsdGeom, Gf
      
      # 创建太阳能板几何体
      for i, panel in enumerate(self.panels):
        prim_path = f"/World/SolarArray/Panel_{i}"
        
        # 创建面板 (简化为蓝色平板)
        # TODO: 添加更详细的模型
        pass
        
    except ImportError:
      self._build_abstract()
  
  def _build_mujoco(self) -> None:
    """MuJoCo 构建"""
    self._build_abstract()
  
  def _build_abstract(self) -> None:
    """抽象构建"""
    pass
  
  def get_total_output(self, sim_time: float) -> float:
    """
    获取总发电功率
    
    Args:
      sim_time: 仿真时间 (秒)
      
    Returns:
      总输出功率 (W)
    """
    total = 0.0
    for source in self.energy_sources:
      total += source.get_current_output(sim_time)
    
    self.total_output = total
    return total
  
  def step(self, dt: float, sim_time: float) -> float:
    """
    仿真步进
    
    Args:
      dt: 时间步长
      sim_time: 仿真时间
      
    Returns:
      本步产生的总能量 (Wh)
    """
    total_energy = 0.0
    for source in self.energy_sources:
      energy = source.step(dt, sim_time)
      total_energy += energy
    
    self.total_generated += total_energy
    return total_energy
  
  def set_weather(self, weather_factor: float) -> None:
    """
    设置天气影响
    
    Args:
      weather_factor: 天气因子 (0-1)
    """
    for source in self.energy_sources:
      source.set_weather_factor(weather_factor)
  
  def get_status(self) -> Dict[str, Any]:
    """获取状态"""
    return {
      "name": self.config.name,
      "current_output_watts": self.total_output,
      "total_generated_wh": self.total_generated,
      "num_panels": self.config.num_panels,
      "efficiency": self.config.efficiency,
      "day_night_cycle": self.config.day_night_cycle,
    }
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "config": {
        "name": self.config.name,
        "position": list(self.config.position),
        "size": list(self.config.size),
        "energy_output_per_sec": self.config.energy_output_per_sec,
        "efficiency": self.config.efficiency,
        "day_night_cycle": self.config.day_night_cycle,
      },
      "status": self.get_status(),
    }
  
  @classmethod
  def from_config(cls, config_dict: Dict[str, Any]) -> "SolarArray":
    """从配置字典创建"""
    array_config = SolarArrayConfig(
      name=config_dict.get("name", "solar_array"),
      position=tuple(config_dict.get("position", [0, 0, 0])),
      size=tuple(config_dict.get("size", [10, 5, 3])),
      energy_output_per_sec=config_dict.get("energy_output_per_sec", 100.0),
      efficiency=config_dict.get("efficiency", 0.85),
      day_night_cycle=config_dict.get("day_night_cycle", True),
      day_length=config_dict.get("day_length", 86400.0),
    )
    
    return cls(array_config)
