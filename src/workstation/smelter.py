"""
GENESIS Smelter Station - 冶炼站

冶炼站用于将矿石冶炼成金属锭。
主要配方: smelt_iron (3 iron_ore → 2 iron_bar)

特点:
- 高温冶炼过程
- 较长的加工时间
- 消耗大量能量
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from .base_station import WorkStation, StationConfig, StationState
from genesis.world.recipes import RecipeRegistry


@dataclass
class SmelterConfig(StationConfig):
    """
    冶炼站配置
    
    Attributes:
        furnace_temperature: 炉温 (摄氏度)
        heating_rate: 加热速率 (度/秒)
        cooling_rate: 冷却速率 (度/秒)
        smoke_particles: 是否启用烟雾粒子效果
    """
    furnace_temperature: float = 1500.0  # 摄氏度
    heating_rate: float = 50.0  # 度/秒
    cooling_rate: float = 20.0  # 度/秒
    smoke_particles: bool = True
    
    def __post_init__(self):
        """初始化后设置默认值"""
        self.name = self.name or "smelter"
        self.station_type = "smelter"
        self.size = self.size or (3.0, 2.5, 2.0)


class Smelter(WorkStation):
    """
    冶炼站
    
    将矿石冶炼成金属锭的工站。
    
    支持配方:
    - smelt_iron: 3 iron_ore → 2 iron_bar (30秒)
    
    视觉效果:
    - 加工时顶部发光
    - 烟雾粒子效果 (可选)
    
    Attributes:
        config: 冶炼站配置
        current_temperature: 当前炉温
        is_heating: 是否正在加热
    """
    
    def __init__(
        self,
        config: Optional[SmelterConfig] = None,
        recipe_registry: Optional[RecipeRegistry] = None,
    ):
        """
        初始化冶炼站
        
        Args:
            config: 冶炼站配置
            recipe_registry: 配方注册表
        """
        config = config or SmelterConfig()
        super().__init__(config, recipe_registry)
        
        # 冶炼特有属性
        self.current_temperature: float = 25.0  # 室温
        self.is_heating: bool = False
        self.target_temperature: float = config.furnace_temperature
        
        # 视觉效果状态
        self._glow_intensity: float = 0.0
        self._smoke_active: bool = False
    
    def _build_geometry(self, sim_context: Any) -> None:
        """
        构建冶炼站几何体
        
        Args:
            sim_context: 仿真上下文
        """
        # 简化实现 - 实际项目中会创建详细的3D模型
        # 这里只记录构建信息
        self._geometry_info = {
            "type": "smelter",
            "base": {
                "shape": "box",
                "size": list(self.config.size),
                "color": [0.3, 0.3, 0.35],  # 深灰色
            },
            "furnace": {
                "shape": "cylinder",
                "radius": 0.5,
                "height": 1.0,
                "position_offset": [0, 0, 0.5],
                "color": [0.4, 0.2, 0.1],  # 深红棕色
            },
            "chimney": {
                "shape": "cylinder",
                "radius": 0.15,
                "height": 0.8,
                "position_offset": [0, 0, 1.5],
                "color": [0.25, 0.25, 0.25],  # 烟囱灰色
            },
        }
    
    def step(self, dt: float) -> None:
        """
        仿真步进
        
        Args:
            dt: 时间步长 (秒)
        """
        # 调用父类步进
        super().step(dt)
        
        # 更新温度
        self._update_temperature(dt)
        
        # 更新视觉效果
        self._update_visual_effects()
    
    def _update_temperature(self, dt: float) -> None:
        """
        更新炉温
        
        Args:
            dt: 时间步长 (秒)
        """
        if self.state == StationState.PROCESSING:
            # 加热到目标温度
            if self.current_temperature < self.target_temperature:
                self.current_temperature += self.config.heating_rate * dt
                self.current_temperature = min(
                    self.current_temperature,
                    self.target_temperature
                )
            self.is_heating = True
        else:
            # 自然冷却
            if self.current_temperature > 25.0:
                self.current_temperature -= self.config.cooling_rate * dt
                self.current_temperature = max(self.current_temperature, 25.0)
            self.is_heating = False
    
    def _update_visual_effects(self) -> None:
        """更新视觉效果"""
        # 发光强度基于温度
        temp_ratio = (self.current_temperature - 25.0) / (self.target_temperature - 25.0)
        self._glow_intensity = max(0.0, min(1.0, temp_ratio))
        
        # 烟雾效果
        self._smoke_active = (
            self.state == StationState.PROCESSING and
            self.config.smoke_particles and
            self.current_temperature > 500.0
        )
    
    def get_temperature(self) -> float:
        """获取当前炉温"""
        return self.current_temperature
    
    def get_glow_intensity(self) -> float:
        """获取发光强度 (0-1)"""
        return self._glow_intensity
    
    def is_smoke_active(self) -> bool:
        """是否启用烟雾效果"""
        return self._smoke_active
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取冶炼站状态
        
        Returns:
            状态字典
        """
        status = super().get_status()
        # 添加冶炼站特有信息
        status.temperature = self.current_temperature
        status.is_heating = self.is_heating
        return status
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data = super().to_dict()
        data["smelter"] = {
            "current_temperature": self.current_temperature,
            "is_heating": self.is_heating,
            "glow_intensity": self._glow_intensity,
        }
        return data
    
    def reset(self) -> None:
        """重置冶炼站状态"""
        super().reset()
        self.current_temperature = 25.0
        self.is_heating = False
        self._glow_intensity = 0.0
        self._smoke_active = False


__all__ = [
    "SmelterConfig",
    "Smelter",
]
