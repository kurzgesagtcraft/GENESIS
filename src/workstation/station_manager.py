"""
GENESIS Station Manager - 工站管理器

统一管理所有工站，提供工站注册、查询、步进等功能。
与 WorldManager 集成，管理工站的生命周期。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type
import yaml
from pathlib import Path

from .base_station import WorkStation, StationConfig, StationState, StationStatus
from .smelter import Smelter, SmelterConfig
from .fabricator import Fabricator, FabricatorConfig
from .assembler import Assembler, AssemblerConfig
from .station_interface import StationInterface
from genesis.world.recipes import RecipeRegistry
from genesis.world.items import ItemRegistry


@dataclass
class StationManagerConfig:
    """
    工站管理器配置
    
    Attributes:
        stations: 工站配置列表
        auto_build: 是否自动构建
    """
    stations: List[Dict[str, Any]] = field(default_factory=list)
    auto_build: bool = True


class StationManager:
    """
    工站管理器
    
    统一管理所有工站。
    
    功能:
    - 工站注册与创建
    - 工站查询
    - 仿真步进
    - 状态汇总
    
    Attributes:
        config: 管理器配置
        stations: 工站字典 {name: WorkStation}
        interface: 统一接口
        recipe_registry: 配方注册表
        item_registry: 物品注册表
    """
    
    # 工站类型注册表
    _station_types: Dict[str, Type[WorkStation]] = {
        "smelter": Smelter,
        "cnc_3dprint": Fabricator,
        "assembly": Assembler,
    }
    
    _config_types: Dict[str, Type[StationConfig]] = {
        "smelter": SmelterConfig,
        "cnc_3dprint": FabricatorConfig,
        "assembly": AssemblerConfig,
    }
    
    def __init__(
        self,
        config: Optional[StationManagerConfig] = None,
        recipe_registry: Optional[RecipeRegistry] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        """
        初始化工站管理器
        
        Args:
            config: 管理器配置
            recipe_registry: 配方注册表
            item_registry: 物品注册表
        """
        self.config = config or StationManagerConfig()
        self.recipe_registry = recipe_registry or RecipeRegistry()
        self.item_registry = item_registry or ItemRegistry()
        
        # 工站字典
        self.stations: Dict[str, WorkStation] = {}
        
        # 统一接口
        self.interface = StationInterface(self)
        
        # 仿真上下文
        self._sim_context: Optional[Any] = None
        self._is_built: bool = False
        
        # 统计
        self.total_processing_time: float = 0.0
    
    def load_config(self, config_path: str) -> None:
        """
        从配置文件加载工站配置
        
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
        """
        解析配置字典
        
        Args:
            config_dict: 配置字典
        """
        stations_config = config_dict.get("stations", [])
        
        for station_dict in stations_config:
            self._create_station_from_config(station_dict)
    
    def _create_station_from_config(
        self,
        station_config: Dict[str, Any],
    ) -> Optional[WorkStation]:
        """
        从配置创建工站
        
        Args:
            station_config: 工站配置字典
            
        Returns:
            创建的工站实例
        """
        station_type = station_config.get("type")
        if station_type not in self._station_types:
            return None
        
        # 获取配置类
        config_class = self._config_types.get(station_type, StationConfig)
        
        # 创建配置
        config = config_class(
            name=station_config.get("name", f"{station_type}_0"),
            station_type=station_type,
            position=tuple(station_config.get("position", [0, 0, 0])),
            size=tuple(station_config.get("size", [2, 2, 1.5])),
        )
        
        # 创建工站
        station_class = self._station_types[station_type]
        station = station_class(
            config=config,
            recipe_registry=self.recipe_registry,
            item_registry=self.item_registry,
        )
        
        # 注册
        self.register_station(station)
        
        return station
    
    def register_station(self, station: WorkStation) -> None:
        """
        注册工站
        
        Args:
            station: 工站实例
        """
        self.stations[station.config.name] = station
    
    def unregister_station(self, station_name: str) -> bool:
        """
        注销工站
        
        Args:
            station_name: 工站名称
            
        Returns:
            是否成功注销
        """
        if station_name in self.stations:
            del self.stations[station_name]
            return True
        return False
    
    def get_station(self, station_name: str) -> Optional[WorkStation]:
        """
        获取工站
        
        Args:
            station_name: 工站名称
            
        Returns:
            工站实例
        """
        return self.stations.get(station_name)
    
    def get_all_stations(self) -> Dict[str, WorkStation]:
        """获取所有工站"""
        return dict(self.stations)
    
    def get_stations_by_type(self, station_type: str) -> List[WorkStation]:
        """
        按类型获取工站
        
        Args:
            station_type: 工站类型
            
        Returns:
            工站列表
        """
        return [
            station for station in self.stations.values()
            if station.config.station_type == station_type
        ]
    
    def get_available_stations(
        self,
        station_type: Optional[str] = None,
    ) -> List[WorkStation]:
        """
        获取可用工站 (空闲或等待输入)
        
        Args:
            station_type: 工站类型 (可选)
            
        Returns:
            可用工站列表
        """
        available = [
            station for station in self.stations.values()
            if station.state in [StationState.IDLE, StationState.WAITING_INPUT]
        ]
        
        if station_type:
            available = [
                s for s in available
                if s.config.station_type == station_type
            ]
        
        return available
    
    def build_all(self, sim_context: Any) -> None:
        """
        构建所有工站
        
        Args:
            sim_context: 仿真上下文
        """
        self._sim_context = sim_context
        
        for station in self.stations.values():
            station.build(sim_context)
        
        self._is_built = True
    
    def step(self, dt: float) -> None:
        """
        仿真步进
        
        Args:
            dt: 时间步长 (秒)
        """
        for station in self.stations.values():
            station.step(dt)
        
        # 更新统计
        self.total_processing_time += dt
    
    def get_all_status(self) -> Dict[str, StationStatus]:
        """
        获取所有工站状态
        
        Returns:
            状态字典 {station_name: status}
        """
        return {
            name: station.get_status()
            for name, station in self.stations.items()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取汇总信息
        
        Returns:
            汇总信息字典
        """
        total_stations = len(self.stations)
        idle = sum(1 for s in self.stations.values() if s.state == StationState.IDLE)
        processing = sum(1 for s in self.stations.values() if s.state == StationState.PROCESSING)
        waiting = sum(1 for s in self.stations.values() if s.state == StationState.WAITING_INPUT)
        done = sum(1 for s in self.stations.values() if s.state == StationState.DONE)
        error = sum(1 for s in self.stations.values() if s.state == StationState.ERROR)
        
        total_processed = sum(s.total_processed for s in self.stations.values())
        
        return {
            "total_stations": total_stations,
            "idle": idle,
            "processing": processing,
            "waiting_input": waiting,
            "done": done,
            "error": error,
            "total_processed": total_processed,
            "total_processing_time": self.total_processing_time,
        }
    
    def find_station_for_recipe(self, recipe_name: str) -> Optional[WorkStation]:
        """
        查找可执行配方的工站
        
        Args:
            recipe_name: 配方名称
            
        Returns:
            可用工站，如果没有返回 None
        """
        recipe = self.recipe_registry.get_recipe(recipe_name)
        if recipe is None:
            return None
        
        # 获取对应类型的可用工站
        available = self.get_available_stations(recipe.station_type)
        
        if available:
            return available[0]
        
        return None
    
    def reset_all(self) -> None:
        """重置所有工站"""
        for station in self.stations.values():
            station.reset()
        
        self.total_processing_time = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "stations": {
                name: station.to_dict()
                for name, station in self.stations.items()
            },
            "summary": self.get_summary(),
        }
    
    @classmethod
    def from_config_dict(
        cls,
        config_dict: Dict[str, Any],
        recipe_registry: Optional[RecipeRegistry] = None,
        item_registry: Optional[ItemRegistry] = None,
    ) -> StationManager:
        """
        从配置字典创建管理器
        
        Args:
            config_dict: 配置字典
            recipe_registry: 配方注册表
            item_registry: 物品注册表
            
        Returns:
            管理器实例
        """
        manager = cls(
            recipe_registry=recipe_registry,
            item_registry=item_registry,
        )
        manager._parse_config(config_dict)
        return manager
    
    @classmethod
    def register_station_type(
        cls,
        type_name: str,
        station_class: Type[WorkStation],
        config_class: Type[StationConfig],
    ) -> None:
        """
        注册新的工站类型
        
        Args:
            type_name: 类型名称
            station_class: 工站类
            config_class: 配置类
        """
        cls._station_types[type_name] = station_class
        cls._config_types[type_name] = config_class


__all__ = [
    "StationManagerConfig",
    "StationManager",
]
