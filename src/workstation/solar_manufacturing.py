"""
光伏制造工站模块

实现光伏组件制造全产业链的工站类:
- SiliconPurifier: 硅料提纯站
- CrystalGrower: 晶体生长站
- WaferSlicer: 硅片切割站
- SolarCellFab: 电池片制造站
- PanelAssembler: 组件封装站

文件: src/workstation/solar_manufacturing.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math

from workstation.base_station import WorkStation, StationConfig, StationState
from genesis.utils.geometry import SE3
from genesis.world.items import Item, ItemRegistry
from genesis.world.solar_recipes import (
    SOLAR_RECIPES,
    SolarRecipe,
    SolarRecipeType,
    get_recipes_by_station,
)


# ============================================================================
# 配置类
# ============================================================================

@dataclass
class SiliconPurifierConfig(StationConfig):
    """硅料提纯站配置"""
    station_type: str = "silicon_purifier"
    size: Tuple[float, float, float] = (3.0, 2.5, 2.0)
    max_input_buffer: int = 20
    max_output_buffer: int = 10
    
    # 工艺参数
    max_temperature: float = 1500.0  # 最高温度 °C
    target_purity: float = 99.9999   # 目标纯度 %
    heating_rate: float = 50.0       # 加热速率 °C/s


@dataclass
class CrystalGrowerConfig(StationConfig):
    """晶体生长站配置"""
    station_type: str = "crystal_grower"
    size: Tuple[float, float, float] = (4.0, 3.0, 3.5)
    max_input_buffer: int = 15
    max_output_buffer: int = 5
    
    # 工艺参数
    max_temperature: float = 1500.0  # 熔化温度 °C
    pull_speed: float = 1.5          # 提拉速度 mm/min
    crystal_diameter: float = 200.0  # 晶棒直径 mm
    rotation_speed: float = 15.0     # 转速 rpm


@dataclass
class WaferSlicerConfig(StationConfig):
    """硅片切割站配置"""
    station_type: str = "wafer_slicer"
    size: Tuple[float, float, float] = (3.5, 2.5, 2.0)
    max_input_buffer: int = 10
    max_output_buffer: int = 100
    
    # 工艺参数
    wire_speed: float = 15.0         # 线速度 m/s
    wafer_thickness: float = 180.0   # 硅片厚度 μm
    kerf_loss: float = 120.0         # 切割损耗 μm
    wafers_per_ingot: int = 50       # 每根晶棒切片数


@dataclass
class SolarCellFabConfig(StationConfig):
    """电池片制造站配置"""
    station_type: str = "solar_cell_fab"
    size: Tuple[float, float, float] = (5.0, 4.0, 2.5)
    max_input_buffer: int = 100
    max_output_buffer: int = 100
    
    # 工艺参数
    diffusion_temp: float = 850.0    # 扩散温度 °C
    coating_thickness: float = 80.0  # 减反射膜厚度 nm
    firing_temp: float = 850.0       # 烧结温度 °C
    target_efficiency: float = 23.0  # 目标效率 %


@dataclass
class PanelAssemblerConfig(StationConfig):
    """组件封装站配置"""
    station_type: str = "panel_assembler"
    size: Tuple[float, float, float] = (6.0, 4.0, 1.5)
    max_input_buffer: int = 200
    max_output_buffer: int = 10
    
    # 工艺参数
    lamination_temp: float = 150.0   # 层压温度 °C
    lamination_time: float = 600.0   # 层压时间 s
    curing_temp: float = 80.0        # 固化温度 °C
    cell_count: int = 72             # 电池片数量


# ============================================================================
# 硅料提纯站
# ============================================================================

class SiliconPurifier(WorkStation):
    """
    硅料提纯工站
    
    将硅矿提纯为多晶硅料，采用改进西门子法。
    
    工艺流程:
    1. 硅矿破碎 → 2. 酸洗除杂 → 3. 高温熔炼 → 4. 定向凝固
    
    状态扩展:
    - HEATING: 加热中
    - REACTING: 反应中
    - COOLING: 冷却中
    """
    
    def __init__(
        self,
        config: Optional[SiliconPurifierConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or SiliconPurifierConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        # 工艺状态
        self.temperature: float = 25.0      # 当前温度 °C
        self.purity_level: float = 0.0      # 当前纯度 %
        self.process_stage: int = 0         # 工艺阶段
        
        # 加载配方
        self._load_solar_recipes()
    
    def _load_solar_recipes(self) -> None:
        """加载光伏配方"""
        self._available_recipes = get_recipes_by_station("silicon_purifier")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        # TODO: 在仿真环境中创建3D模型
        # 1. 炉体主体 (圆柱形)
        # 2. 加热元件
        # 3. 进料口/出料口
        # 4. 控制面板
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        # 调用基类处理配方逻辑
        super().step(dt)
        
        # 温度模拟
        if self.state == StationState.PROCESSING:
            # 加热阶段
            if self.temperature < self.config.max_temperature:
                self.temperature += self.config.heating_rate * dt
            else:
                self.temperature = self.config.max_temperature
            
            # 纯度随时间提升
            if self.temperature > 1000:
                purity_rate = 0.001 * (self.temperature / 1000)
                self.purity_level = min(
                    self.config.target_purity,
                    self.purity_level + purity_rate * dt
                )
        else:
            # 冷却
            cooling_rate = 10.0  # °C/s
            self.temperature = max(25.0, self.temperature - cooling_rate * dt)
            if self.temperature <= 25.0:
                self.purity_level = 0.0
    
    def get_temperature(self) -> float:
        """获取当前温度"""
        return self.temperature
    
    def get_purity(self) -> float:
        """获取当前纯度"""
        return self.purity_level
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = super().get_status()
        return {
            "name": status.name,
            "state": status.state.value,
            "input_buffer": status.input_buffer,
            "output_count": status.output_count,
            "current_recipe": status.current_recipe,
            "process_remaining": status.process_remaining,
            "temperature": self.temperature,
            "purity": self.purity_level,
        }


# ============================================================================
# 晶体生长站
# ============================================================================

class CrystalGrower(WorkStation):
    """
    单晶硅棒拉制工站
    
    采用直拉法(CZ)生长单晶硅棒。
    
    工艺流程:
    1. 多晶硅熔化 → 2. 籽晶引入 → 3. 缓慢提拉 → 4. 冷却成型
    
    状态扩展:
    - MELTING: 熔化中
    - PULLING: 提拉中
    - COOLING: 冷却中
    """
    
    def __init__(
        self,
        config: Optional[CrystalGrowerConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or CrystalGrowerConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        # 工艺状态
        self.furnace_temp: float = 25.0     # 炉温 °C
        self.pull_distance: float = 0.0     # 已提拉距离 mm
        self.crystal_diameter: float = 0.0  # 当前晶体直径 mm
        self.rotation_angle: float = 0.0    # 旋转角度 °
        
        # 加载配方
        self._load_solar_recipes()
    
    def _load_solar_recipes(self) -> None:
        """加载光伏配方"""
        self._available_recipes = get_recipes_by_station("crystal_grower")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        # TODO: 在仿真环境中创建3D模型
        # 1. 坩埚和加热炉
        # 2. 提拉机构
        # 3. 籽晶夹持器
        # 4. 晶棒接收台
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            # 加热熔化
            if self.furnace_temp < self.config.max_temperature:
                self.furnace_temp += 20.0 * dt
            
            # 提拉生长
            if self.furnace_temp >= self.config.max_temperature:
                self.pull_distance += self.config.pull_speed * dt / 60.0
                self.crystal_diameter = self.config.crystal_diameter
                self.rotation_angle += self.config.rotation_speed * 6.0 * dt
            
            # 检查是否完成
            target_length = 1500.0  # mm
            if self.pull_distance >= target_length:
                self.pull_distance = target_length
        else:
            # 冷却
            self.furnace_temp = max(25.0, self.furnace_temp - 15.0 * dt)
            if self.furnace_temp <= 25.0:
                self.pull_distance = 0.0
                self.crystal_diameter = 0.0
    
    def get_crystal_length(self) -> float:
        """获取当前晶体长度"""
        return self.pull_distance
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = super().get_status()
        return {
            "name": status.name,
            "state": status.state.value,
            "input_buffer": status.input_buffer,
            "output_count": status.output_count,
            "current_recipe": status.current_recipe,
            "process_remaining": status.process_remaining,
            "furnace_temp": self.furnace_temp,
            "pull_distance": self.pull_distance,
            "crystal_diameter": self.crystal_diameter,
        }


# ============================================================================
# 硅片切割站
# ============================================================================

class WaferSlicer(WorkStation):
    """
    硅片切割工站
    
    采用多线切割技术将硅棒切割为硅片。
    
    工艺流程:
    1. 晶棒粘接 → 2. 多线切割 → 3. 清洗烘干 → 4. 检测分选
    """
    
    def __init__(
        self,
        config: Optional[WaferSlicerConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or WaferSlicerConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        # 工艺状态
        self.wire_position: float = 0.0     # 切割线位置 mm
        self.wafers_cut: int = 0            # 已切硅片数
        self.wire_speed: float = 0.0        # 当前线速度
        
        # 加载配方
        self._load_solar_recipes()
    
    def _load_solar_recipes(self) -> None:
        """加载光伏配方"""
        self._available_recipes = get_recipes_by_station("wafer_slicer")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        # TODO: 在仿真环境中创建3D模型
        # 1. 切割线绕组系统
        # 2. 工件夹持台
        # 3. 切割液喷淋系统
        # 4. 硅片收集槽
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            # 切割进行中
            self.wire_speed = self.config.wire_speed
            
            # 计算切割进度
            ingot_length = 1500.0  # mm
            cut_per_wafer = (self.config.wafer_thickness + self.config.kerf_loss) / 1000.0  # mm
            
            # 更新切割位置
            cut_speed = 0.5  # mm/s 切割速度
            self.wire_position += cut_speed * dt
            
            # 计算已切硅片数
            self.wafers_cut = int(self.wire_position / cut_per_wafer)
            self.wafers_cut = min(self.wafers_cut, self.config.wafers_per_ingot)
        else:
            self.wire_speed = 0.0
            self.wire_position = 0.0
            self.wafers_cut = 0
    
    def get_cut_progress(self) -> float:
        """获取切割进度 (0-1)"""
        return self.wafers_cut / self.config.wafers_per_ingot
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = super().get_status()
        return {
            "name": status.name,
            "state": status.state.value,
            "input_buffer": status.input_buffer,
            "output_count": status.output_count,
            "current_recipe": status.current_recipe,
            "process_remaining": status.process_remaining,
            "wafers_cut": self.wafers_cut,
            "wire_speed": self.wire_speed,
            "progress": self.get_cut_progress(),
        }


# ============================================================================
# 电池片制造站
# ============================================================================

class SolarCellFab(WorkStation):
    """
    太阳能电池片制造工站
    
    实现PERC/TOPCon/HJT等工艺的电池片制造。
    
    工艺流程:
    1. 制绒清洗 → 2. 扩散制结 → 3. 刻蚀清洗 → 4. 镀减反射膜
    5. 丝印电极 → 6. 烧结 → 7. 测试分选
    """
    
    def __init__(
        self,
        config: Optional[SolarCellFabConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or SolarCellFabConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        # 工艺状态
        self.process_stage: int = 0         # 当前工序阶段 (0-6)
        self.cell_efficiency: float = 0.0   # 电池效率 %
        self.voc: float = 0.0               # 开路电压 mV
        self.isc: float = 0.0               # 短路电流 A
        
        # 加载配方
        self._load_solar_recipes()
    
    def _load_solar_recipes(self) -> None:
        """加载光伏配方"""
        self._available_recipes = get_recipes_by_station("solar_cell_fab")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        # TODO: 在仿真环境中创建3D模型
        # 1. 制绒槽
        # 2. 扩散炉
        # 3. PECVD镀膜机
        # 4. 丝网印刷机
        # 5. 烧结炉
        # 6. 测试分选机
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            # 模拟工艺阶段
            total_stages = 7
            if self.current_recipe:
                progress = 1.0 - (self.process_timer / self.current_recipe.process_time)
                self.process_stage = int(progress * total_stages)
                self.process_stage = min(self.process_stage, total_stages - 1)
                
                # 根据配方类型设置效率
                if "PERC" in str(self.current_recipe.quality_params.get("type", "")):
                    self.cell_efficiency = 23.0 * progress
                    self.voc = 685.0 * progress
                elif "TOPCon" in str(self.current_recipe.quality_params.get("type", "")):
                    self.cell_efficiency = 25.0 * progress
                    self.voc = 710.0 * progress
                elif "HJT" in str(self.current_recipe.quality_params.get("type", "")):
                    self.cell_efficiency = 26.0 * progress
                    self.voc = 740.0 * progress
        else:
            self.process_stage = 0
            self.cell_efficiency = 0.0
            self.voc = 0.0
    
    def get_process_stage_name(self) -> str:
        """获取当前工序名称"""
        stages = [
            "制绒清洗",
            "扩散制结",
            "刻蚀清洗",
            "镀减反射膜",
            "丝印电极",
            "烧结",
            "测试分选",
        ]
        if 0 <= self.process_stage < len(stages):
            return stages[self.process_stage]
        return "未知"
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = super().get_status()
        return {
            "name": status.name,
            "state": status.state.value,
            "input_buffer": status.input_buffer,
            "output_count": status.output_count,
            "current_recipe": status.current_recipe,
            "process_remaining": status.process_remaining,
            "process_stage": self.process_stage,
            "process_stage_name": self.get_process_stage_name(),
            "cell_efficiency": self.cell_efficiency,
            "voc": self.voc,
        }


# ============================================================================
# 组件封装站
# ============================================================================

class PanelAssembler(WorkStation):
    """
    光伏组件封装工站
    
    将电池片串焊并封装为完整光伏组件。
    
    工艺流程:
    1. 电池片串焊 → 2. EVA铺设 → 3. 层压 → 4. 装框
    5. 接线盒安装 → 6. 固化 → 7. 测试
    """
    
    def __init__(
        self,
        config: Optional[PanelAssemblerConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or PanelAssemblerConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        # 工艺状态
        self.process_stage: int = 0         # 当前工序阶段 (0-6)
        self.cells_soldered: int = 0        # 已焊接电池片数
        self.panel_power: float = 0.0       # 组件功率 W
        self.lamination_temp: float = 25.0  # 层压温度
        
        # 加载配方
        self._load_solar_recipes()
    
    def _load_solar_recipes(self) -> None:
        """加载光伏配方"""
        self._available_recipes = get_recipes_by_station("panel_assembler")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        # TODO: 在仿真环境中创建3D模型
        # 1. 串焊机
        # 2. EVA铺设台
        # 3. 层压机
        # 4. 装框机
        # 5. 接线盒安装台
        # 6. 固化炉
        # 7. 测试台
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            # 模拟工艺阶段
            total_stages = 7
            if self.current_recipe:
                progress = 1.0 - (self.process_timer / self.current_recipe.process_time)
                self.process_stage = int(progress * total_stages)
                self.process_stage = min(self.process_stage, total_stages - 1)
                
                # 串焊阶段
                if self.process_stage == 0:
                    cells_per_second = 2.0
                    self.cells_soldered = int(progress * total_stages * self.config.cell_count)
                
                # 层压阶段
                if self.process_stage == 2:
                    self.lamination_temp = self.config.lamination_temp
                else:
                    self.lamination_temp = 25.0
                
                # 计算功率
                if self.current_recipe.quality_params.get("power"):
                    power_str = self.current_recipe.quality_params["power"]
                    if isinstance(power_str, str) and power_str.endswith("W"):
                        self.panel_power = float(power_str[:-1]) * progress
        else:
            self.process_stage = 0
            self.cells_soldered = 0
            self.panel_power = 0.0
            self.lamination_temp = 25.0
    
    def get_process_stage_name(self) -> str:
        """获取当前工序名称"""
        stages = [
            "电池片串焊",
            "EVA铺设",
            "层压",
            "装框",
            "接线盒安装",
            "固化",
            "测试",
        ]
        if 0 <= self.process_stage < len(stages):
            return stages[self.process_stage]
        return "未知"
    
    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        status = super().get_status()
        return {
            "name": status.name,
            "state": status.state.value,
            "input_buffer": status.input_buffer,
            "output_count": status.output_count,
            "current_recipe": status.current_recipe,
            "process_remaining": status.process_remaining,
            "process_stage": self.process_stage,
            "process_stage_name": self.get_process_stage_name(),
            "cells_soldered": self.cells_soldered,
            "panel_power": self.panel_power,
            "lamination_temp": self.lamination_temp,
        }


# ============================================================================
# 工站工厂函数
# ============================================================================

def create_solar_station(
    station_type: str,
    name: str,
    position: Tuple[float, float, float],
    **kwargs,
) -> WorkStation:
    """
    创建光伏制造工站
    
    Args:
        station_type: 工站类型
        name: 工站名称
        position: 位置
        **kwargs: 其他配置参数
    
    Returns:
        工站实例
    """
    station_map = {
        "silicon_purifier": (SiliconPurifier, SiliconPurifierConfig),
        "crystal_grower": (CrystalGrower, CrystalGrowerConfig),
        "wafer_slicer": (WaferSlicer, WaferSlicerConfig),
        "solar_cell_fab": (SolarCellFab, SolarCellFabConfig),
        "panel_assembler": (PanelAssembler, PanelAssemblerConfig),
    }
    
    if station_type not in station_map:
        raise ValueError(f"Unknown station type: {station_type}")
    
    station_class, config_class = station_map[station_type]
    config = config_class(name=name, position=position, **kwargs)
    
    return station_class(config)


# ============================================================================
# 导出
# ============================================================================

__all__ = [
    # 配置类
    "SiliconPurifierConfig",
    "CrystalGrowerConfig",
    "WaferSlicerConfig",
    "SolarCellFabConfig",
    "PanelAssemblerConfig",
    # 工站类
    "SiliconPurifier",
    "CrystalGrower",
    "WaferSlicer",
    "SolarCellFab",
    "PanelAssembler",
    # 工厂函数
    "create_solar_station",
]
