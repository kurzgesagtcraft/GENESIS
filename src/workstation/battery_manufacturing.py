"""
储能电池制造工站模块

实现储能电池系统制造全产业链的工站类:
- LithiumRefinery: 锂提炼站
- CathodeSynthesizer: 正极材料合成站
- AnodeProcessor: 负极材料加工站
- ElectrodeCoater: 电极涂布站
- CellAssembler: 电芯组装站
- CellFormation: 化成分容站
- ModuleAssembler: 模组组装站
- PackAssembler: 电池包组装站
- ESSIntegrator: 储能系统集成站

文件: src/workstation/battery_manufacturing.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import math

from workstation.base_station import WorkStation, StationConfig, StationState
from genesis.utils.geometry import SE3
from genesis.world.items import Item, ItemRegistry
from genesis.world.battery_recipes import (
    BATTERY_RECIPES,
    BatteryRecipe,
    BatteryRecipeType,
    get_recipes_by_station as get_battery_recipes_by_station,
)


# ============================================================================
# 配置类
# ============================================================================

@dataclass
class LithiumRefineryConfig(StationConfig):
    """锂提炼站配置"""
    station_type: str = "lithium_refinery"
    size: Tuple[float, float, float] = (4.0, 3.0, 2.5)
    max_input_buffer: int = 30
    max_output_buffer: int = 15
    
    # 工艺参数
    roasting_temp: float = 950.0      # 焙烧温度 °C
    leaching_temp: float = 80.0       # 浸出温度 °C
    target_purity: float = 99.5       # 目标纯度 %


@dataclass
class CathodeSynthesizerConfig(StationConfig):
    """正极材料合成站配置"""
    station_type: str = "cathode_synthesizer"
    size: Tuple[float, float, float] = (5.0, 4.0, 3.0)
    max_input_buffer: int = 20
    max_output_buffer: int = 10
    
    # 工艺参数
    sintering_temp: float = 800.0     # 烧结温度 °C
    sintering_time: float = 7200.0    # 烧结时间 s
    cooling_rate: float = 5.0         # 冷却速率 °C/min


@dataclass
class AnodeProcessorConfig(StationConfig):
    """负极材料加工站配置"""
    station_type: str = "anode_processor"
    size: Tuple[float, float, float] = (4.5, 3.5, 3.5)
    max_input_buffer: int = 15
    max_output_buffer: int = 10
    
    # 工艺参数
    graphitization_temp: float = 2800.0  # 石墨化温度 °C
    holding_time: float = 3600.0         # 保温时间 s


@dataclass
class ElectrodeCoaterConfig(StationConfig):
    """电极涂布站配置"""
    station_type: str = "electrode_coater"
    size: Tuple[float, float, float] = (6.0, 4.0, 2.0)
    max_input_buffer: int = 50
    max_output_buffer: int = 100
    
    # 工艺参数
    coating_speed: float = 50.0       # 涂布速度 m/min
    drying_temp: float = 120.0        # 烘干温度 °C
    calender_pressure: float = 300.0  # 辊压压力 kN/m


@dataclass
class CellAssemblerConfig(StationConfig):
    """电芯组装站配置"""
    station_type: str = "cell_assembler"
    size: Tuple[float, float, float] = (5.0, 4.0, 2.5)
    max_input_buffer: int = 50
    max_output_buffer: int = 30
    
    # 工艺参数
    winding_speed: float = 10.0       # 卷绕速度 m/min
    electrolyte_volume: float = 50.0  # 注液量 mL
    sealing_temp: float = 200.0       # 封口温度 °C


@dataclass
class CellFormationConfig(StationConfig):
    """化成分容站配置"""
    station_type: str = "cell_formation"
    size: Tuple[float, float, float] = (8.0, 6.0, 2.5)
    max_input_buffer: int = 100
    max_output_buffer: int = 100
    
    # 工艺参数
    formation_cycles: int = 3         # 化成循环次数
    charge_rate: float = 0.1          # 充电倍率 C
    discharge_rate: float = 0.1       # 放电倍率 C
    target_capacity: float = 280.0    # 目标容量 Ah


@dataclass
class ModuleAssemblerConfig(StationConfig):
    """模组组装站配置"""
    station_type: str = "module_assembler"
    size: Tuple[float, float, float] = (4.0, 3.0, 2.0)
    max_input_buffer: int = 30
    max_output_buffer: int = 10
    
    # 工艺参数
    welding_current: float = 2000.0   # 焊接电流 A
    welding_time: float = 0.1         # 焊接时间 s
    torque: float = 5.0               # 螺栓扭矩 N·m


@dataclass
class PackAssemblerConfig(StationConfig):
    """电池包组装站配置"""
    station_type: str = "pack_assembler"
    size: Tuple[float, float, float] = (6.0, 4.0, 2.5)
    max_input_buffer: int = 50
    max_output_buffer: int = 5
    
    # 工艺参数
    hv_test_voltage: float = 3000.0   # 高压测试电压 V
    insulation_resistance: float = 100.0  # 绝缘电阻 MΩ
    leak_test_pressure: float = 50.0  # 气密测试压力 kPa


@dataclass
class ESSIntegratorConfig(StationConfig):
    """储能系统集成站配置"""
    station_type: str = "ess_integrator"
    size: Tuple[float, float, float] = (10.0, 8.0, 3.0)
    max_input_buffer: int = 30
    max_output_buffer: int = 5
    
    # 工艺参数
    system_voltage: float = 1000.0    # 系统电压 V
    grid_frequency: float = 50.0      # 电网频率 Hz
    protection_rating: str = "IP55"   # 防护等级


# ============================================================================
# 锂提炼站
# ============================================================================

class LithiumRefinery(WorkStation):
    """
    锂化合物提炼工站
    
    从锂矿提取碳酸锂/氢氧化锂等电池级原料。
    
    工艺流程:
    1. 锂矿焙烧 → 2. 酸浸/碱浸 → 3. 除杂净化 → 4. 沉淀结晶
    """
    
    def __init__(
        self,
        config: Optional[LithiumRefineryConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or LithiumRefineryConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        # 工艺状态
        self.temperature: float = 25.0
        self.purity_level: float = 0.0
        self.process_stage: int = 0
        
        self._load_battery_recipes()
    
    def _load_battery_recipes(self) -> None:
        """加载电池配方"""
        self._available_recipes = get_battery_recipes_by_station("lithium_refinery")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            # 温度模拟
            if self.process_stage < 2:
                if self.temperature < self.config.roasting_temp:
                    self.temperature += 20.0 * dt
            else:
                self.temperature = max(25.0, self.temperature - 10.0 * dt)
            
            # 纯度提升
            if self.temperature > 500:
                self.purity_level = min(
                    self.config.target_purity,
                    self.purity_level + 0.005 * dt
                )
            
            # 工艺阶段
            if self.current_recipe:
                progress = 1.0 - (self.process_timer / self.current_recipe.process_time)
                self.process_stage = int(progress * 4)
        else:
            self.temperature = max(25.0, self.temperature - 15.0 * dt)
            if self.temperature <= 25.0:
                self.purity_level = 0.0
                self.process_stage = 0
    
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
            "process_stage": self.process_stage,
        }


# ============================================================================
# 正极材料合成站
# ============================================================================

class CathodeSynthesizer(WorkStation):
    """
    正极材料合成工站
    
    高温固相法合成正极材料(LFP/NCM/LCO等)。
    
    工艺流程:
    1. 原料混合 → 2. 高温烧结 → 3. 研磨粉碎 → 4. 包覆改性
    """
    
    def __init__(
        self,
        config: Optional[CathodeSynthesizerConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or CathodeSynthesizerConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        self.furnace_temp: float = 25.0
        self.material_type: str = ""
        self.capacity: float = 0.0
        
        self._load_battery_recipes()
    
    def _load_battery_recipes(self) -> None:
        """加载电池配方"""
        self._available_recipes = get_battery_recipes_by_station("cathode_synthesizer")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            # 加热到烧结温度
            if self.furnace_temp < self.config.sintering_temp:
                self.furnace_temp += 15.0 * dt
            
            # 从配方获取材料类型
            if self.current_recipe:
                self.material_type = self.current_recipe.quality_params.get("type", "")
                capacity_str = self.current_recipe.quality_params.get("capacity", "0")
                if isinstance(capacity_str, str) and "mAh/g" in capacity_str:
                    self.capacity = float(capacity_str.replace("mAh/g", ""))
        else:
            self.furnace_temp = max(25.0, self.furnace_temp - 20.0 * dt)
    
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
            "material_type": self.material_type,
            "capacity": self.capacity,
        }


# ============================================================================
# 负极材料加工站
# ============================================================================

class AnodeProcessor(WorkStation):
    """
    负极材料加工工站
    
    石墨化处理和硅碳复合负极制造。
    
    工艺流程:
    1. 石墨提纯 → 2. 石墨化(2800°C) → 3. 研磨分级 → 4. 表面改性
    """
    
    def __init__(
        self,
        config: Optional[AnodeProcessorConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or AnodeProcessorConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        self.furnace_temp: float = 25.0
        self.graphitization_level: float = 0.0
        self.anode_capacity: float = 0.0
        
        self._load_battery_recipes()
    
    def _load_battery_recipes(self) -> None:
        """加载电池配方"""
        self._available_recipes = get_battery_recipes_by_station("anode_processor")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            # 石墨化需要极高温
            if self.furnace_temp < self.config.graphitization_temp:
                self.furnace_temp += 50.0 * dt  # 快速升温
            
            # 石墨化程度
            if self.furnace_temp > 2500:
                self.graphitization_level = min(99.9, self.graphitization_level + 0.01 * dt)
            
            # 从配方获取容量
            if self.current_recipe:
                capacity_str = self.current_recipe.quality_params.get("capacity", "0")
                if isinstance(capacity_str, str) and "mAh/g" in capacity_str:
                    self.anode_capacity = float(capacity_str.replace("mAh/g", ""))
        else:
            self.furnace_temp = max(25.0, self.furnace_temp - 30.0 * dt)
            if self.furnace_temp <= 25.0:
                self.graphitization_level = 0.0
    
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
            "graphitization_level": self.graphitization_level,
            "anode_capacity": self.anode_capacity,
        }


# ============================================================================
# 电极涂布站
# ============================================================================

class ElectrodeCoater(WorkStation):
    """
    电极涂布工站
    
    极片制造: 涂布、烘干、辊压、分切。
    
    工艺流程:
    1. 浆料制备 → 2. 涂布 → 3. 烘干 → 4. 辊压 → 5. 分切
    """
    
    def __init__(
        self,
        config: Optional[ElectrodeCoaterConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or ElectrodeCoaterConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        self.coating_speed: float = 0.0
        self.drying_temp: float = 25.0
        self.electrode_type: str = ""
        self.sheets_produced: int = 0
        
        self._load_battery_recipes()
    
    def _load_battery_recipes(self) -> None:
        """加载电池配方"""
        self._available_recipes = get_battery_recipes_by_station("electrode_coater")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            self.coating_speed = self.config.coating_speed
            self.drying_temp = self.config.drying_temp
            
            # 计算产出
            if self.current_recipe:
                progress = 1.0 - (self.process_timer / self.current_recipe.process_time)
                output_qty = sum(self.current_recipe.outputs.values())
                self.sheets_produced = int(progress * output_qty)
                
                # 判断电极类型
                if "cathode" in self.current_recipe.name:
                    self.electrode_type = "cathode"
                elif "anode" in self.current_recipe.name:
                    self.electrode_type = "anode"
        else:
            self.coating_speed = 0.0
            self.drying_temp = max(25.0, self.drying_temp - 10.0 * dt)
            self.sheets_produced = 0
    
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
            "coating_speed": self.coating_speed,
            "drying_temp": self.drying_temp,
            "electrode_type": self.electrode_type,
            "sheets_produced": self.sheets_produced,
        }


# ============================================================================
# 电芯组装站
# ============================================================================

class CellAssembler(WorkStation):
    """
    电芯组装工站
    
    卷绕/叠片+封装。
    
    工艺流程:
    1. 极片裁切 → 2. 卷绕/叠片 → 3. 入壳 → 4. 焊接 → 5. 注液 → 6. 封口
    """
    
    def __init__(
        self,
        config: Optional[CellAssemblerConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or CellAssemblerConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        self.cell_format: str = ""
        self.cell_capacity: float = 0.0
        self.cell_voltage: float = 0.0
        self.process_stage: int = 0
        
        self._load_battery_recipes()
    
    def _load_battery_recipes(self) -> None:
        """加载电池配方"""
        self._available_recipes = get_battery_recipes_by_station("cell_assembler")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            if self.current_recipe:
                progress = 1.0 - (self.process_timer / self.current_recipe.process_time)
                self.process_stage = int(progress * 6)
                
                # 从配方获取参数
                self.cell_format = self.current_recipe.quality_params.get("format", "")
                self.cell_capacity = float(self.current_recipe.quality_params.get("capacity", "0").replace("Ah", ""))
                self.cell_voltage = float(self.current_recipe.quality_params.get("voltage", "0").replace("V", ""))
        else:
            self.process_stage = 0
    
    def get_process_stage_name(self) -> str:
        """获取当前工序名称"""
        stages = [
            "极片裁切",
            "卷绕/叠片",
            "入壳",
            "焊接",
            "注液",
            "封口",
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
            "cell_format": self.cell_format,
            "cell_capacity": self.cell_capacity,
            "cell_voltage": self.cell_voltage,
        }


# ============================================================================
# 化成分容站
# ============================================================================

class CellFormation(WorkStation):
    """
    电芯化成分容工站
    
    激活与测试。
    
    工艺流程:
    1. 预充电 → 2. 化成(充放电循环) → 3. 老化 → 4. 分容测试 → 5. 分级
    """
    
    def __init__(
        self,
        config: Optional[CellFormationConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or CellFormationConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        self.formation_cycle: int = 0
        self.soc: float = 0.0           # 荷电状态
        self.cell_capacity: float = 0.0  # 实测容量
        self.ir: float = 0.0            # 内阻 mΩ
        
        self._load_battery_recipes()
    
    def _load_battery_recipes(self) -> None:
        """加载电池配方"""
        self._available_recipes = get_battery_recipes_by_station("cell_formation")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            if self.current_recipe:
                progress = 1.0 - (self.process_timer / self.current_recipe.process_time)
                
                # 化成循环
                self.formation_cycle = int(progress * self.config.formation_cycles)
                
                # SOC变化
                self.soc = 50.0 + 40.0 * math.sin(progress * math.pi * self.config.formation_cycles)
                
                # 容量和内阻
                self.cell_capacity = self.config.target_capacity * (0.95 + 0.05 * progress)
                self.ir = 0.3 + 0.1 * (1 - progress)  # 内阻逐渐降低
        else:
            self.formation_cycle = 0
            self.soc = 0.0
    
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
            "formation_cycle": self.formation_cycle,
            "soc": self.soc,
            "cell_capacity": self.cell_capacity,
            "ir": self.ir,
        }


# ============================================================================
# 模组组装站
# ============================================================================

class ModuleAssembler(WorkStation):
    """
    电池模组封装工站
    
    电芯串并联+BMS。
    
    工艺流程:
    1. 电芯配组 → 2. 串联/并联连接 → 3. BMS安装 → 4. 温感安装 → 5. 模组测试
    """
    
    def __init__(
        self,
        config: Optional[ModuleAssemblerConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or ModuleAssemblerConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        self.module_voltage: float = 0.0
        self.module_capacity: float = 0.0
        self.cells_connected: int = 0
        self.process_stage: int = 0
        
        self._load_battery_recipes()
    
    def _load_battery_recipes(self) -> None:
        """加载电池配方"""
        self._available_recipes = get_battery_recipes_by_station("module_assembler")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            if self.current_recipe:
                progress = 1.0 - (self.process_timer / self.current_recipe.process_time)
                self.process_stage = int(progress * 5)
                
                # 从配方获取参数
                self.module_voltage = float(self.current_recipe.quality_params.get("voltage", "0").replace("V", ""))
                self.module_capacity = float(self.current_recipe.quality_params.get("capacity", "0").replace("Ah", ""))
                self.cells_connected = int(self.current_recipe.quality_params.get("cells", "0"))
        else:
            self.process_stage = 0
    
    def get_process_stage_name(self) -> str:
        """获取当前工序名称"""
        stages = [
            "电芯配组",
            "串联/并联连接",
            "BMS安装",
            "温感安装",
            "模组测试",
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
            "module_voltage": self.module_voltage,
            "module_capacity": self.module_capacity,
            "cells_connected": self.cells_connected,
        }


# ============================================================================
# 电池包组装站
# ============================================================================

class PackAssembler(WorkStation):
    """
    电池包组装工站
    
    模组集成+热管理。
    
    工艺流程:
    1. 模组安装 → 2. 高压连接 → 3. 热管理系统安装 → 4. 外壳封装 → 5. EOL测试
    """
    
    def __init__(
        self,
        config: Optional[PackAssemblerConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or PackAssemblerConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        self.pack_voltage: float = 0.0
        self.pack_capacity: float = 0.0  # kWh
        self.modules_installed: int = 0
        self.process_stage: int = 0
        
        self._load_battery_recipes()
    
    def _load_battery_recipes(self) -> None:
        """加载电池配方"""
        self._available_recipes = get_battery_recipes_by_station("pack_assembler")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            if self.current_recipe:
                progress = 1.0 - (self.process_timer / self.current_recipe.process_time)
                self.process_stage = int(progress * 5)
                
                # 从配方获取参数
                self.pack_voltage = float(self.current_recipe.quality_params.get("voltage", "0").replace("V", ""))
                self.pack_capacity = float(self.current_recipe.quality_params.get("capacity", "0").replace("kWh", ""))
                self.modules_installed = int(self.current_recipe.quality_params.get("modules", "0"))
        else:
            self.process_stage = 0
    
    def get_process_stage_name(self) -> str:
        """获取当前工序名称"""
        stages = [
            "模组安装",
            "高压连接",
            "热管理系统安装",
            "外壳封装",
            "EOL测试",
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
            "pack_voltage": self.pack_voltage,
            "pack_capacity": self.pack_capacity,
            "modules_installed": self.modules_installed,
        }


# ============================================================================
# 储能系统集成站
# ============================================================================

class ESSIntegrator(WorkStation):
    """
    储能系统集成工站
    
    电池包+PCS+BMS集成。
    
    工艺流程:
    1. 电池架安装 → 2. PCS安装 → 3. BMS集成 → 4. 消防系统 → 5. 系统调试
    """
    
    def __init__(
        self,
        config: Optional[ESSIntegratorConfig] = None,
        recipe_registry: Optional[Any] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        config = config or ESSIntegratorConfig()
        super().__init__(config, recipe_registry, item_registry)
        
        self.system_power: float = 0.0    # kW
        self.system_capacity: float = 0.0  # kWh
        self.ac_voltage: float = 0.0
        self.process_stage: int = 0
        
        self._load_battery_recipes()
    
    def _load_battery_recipes(self) -> None:
        """加载电池配方"""
        self._available_recipes = get_battery_recipes_by_station("ess_integrator")
    
    def _build_geometry(self, sim_context: Any) -> None:
        """构建工站几何体"""
        pass
    
    def step(self, dt: float) -> None:
        """仿真步进"""
        super().step(dt)
        
        if self.state == StationState.PROCESSING:
            if self.current_recipe:
                progress = 1.0 - (self.process_timer / self.current_recipe.process_time)
                self.process_stage = int(progress * 5)
                
                # 从配方获取参数
                self.system_power = float(self.current_recipe.quality_params.get("power", "0").replace("kW", ""))
                self.system_capacity = float(self.current_recipe.quality_params.get("capacity", "0").replace("kWh", ""))
                ac_v = self.current_recipe.quality_params.get("ac_voltage", "0")
                if isinstance(ac_v, str) and "V" in ac_v:
                    self.ac_voltage = float(ac_v.replace("V", ""))
        else:
            self.process_stage = 0
    
    def get_process_stage_name(self) -> str:
        """获取当前工序名称"""
        stages = [
            "电池架安装",
            "PCS安装",
            "BMS集成",
            "消防系统",
            "系统调试",
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
            "system_power": self.system_power,
            "system_capacity": self.system_capacity,
            "ac_voltage": self.ac_voltage,
        }


# ============================================================================
# 工站工厂函数
# ============================================================================

def create_battery_station(
    station_type: str,
    name: str,
    position: Tuple[float, float, float],
    **kwargs,
) -> WorkStation:
    """
    创建电池制造工站
    
    Args:
        station_type: 工站类型
        name: 工站名称
        position: 位置
        **kwargs: 其他配置参数
    
    Returns:
        工站实例
    """
    station_map = {
        "lithium_refinery": (LithiumRefinery, LithiumRefineryConfig),
        "cathode_synthesizer": (CathodeSynthesizer, CathodeSynthesizerConfig),
        "anode_processor": (AnodeProcessor, AnodeProcessorConfig),
        "electrode_coater": (ElectrodeCoater, ElectrodeCoaterConfig),
        "cell_assembler": (CellAssembler, CellAssemblerConfig),
        "cell_formation": (CellFormation, CellFormationConfig),
        "module_assembler": (ModuleAssembler, ModuleAssemblerConfig),
        "pack_assembler": (PackAssembler, PackAssemblerConfig),
        "ess_integrator": (ESSIntegrator, ESSIntegratorConfig),
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
    "LithiumRefineryConfig",
    "CathodeSynthesizerConfig",
    "AnodeProcessorConfig",
    "ElectrodeCoaterConfig",
    "CellAssemblerConfig",
    "CellFormationConfig",
    "ModuleAssemblerConfig",
    "PackAssemblerConfig",
    "ESSIntegratorConfig",
    # 工站类
    "LithiumRefinery",
    "CathodeSynthesizer",
    "AnodeProcessor",
    "ElectrodeCoater",
    "CellAssembler",
    "CellFormation",
    "ModuleAssembler",
    "PackAssembler",
    "ESSIntegrator",
    # 工厂函数
    "create_battery_station",
]
