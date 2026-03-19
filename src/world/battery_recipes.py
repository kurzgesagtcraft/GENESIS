"""
储能电池制造配方系统

实现从原材料到完整储能电池系统的全产业链制造配方。
包括: 锂提炼、正极材料合成、负极材料加工、电极涂布、电芯组装、化成分容、模组/电池包组装等工序。

文件: src/world/battery_recipes.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class BatteryRecipeType(Enum):
    """电池配方类型"""
    # 上游原材料提炼
    MATERIAL_REFINING = "material_refining"
    # 正极材料合成
    CATHODE_SYNTHESIS = "cathode_synthesis"
    # 负极材料加工
    ANODE_PROCESSING = "anode_processing"
    # 电极制造
    ELECTRODE_MANUFACTURING = "electrode_manufacturing"
    # 电芯制造
    CELL_MANUFACTURING = "cell_manufacturing"
    # 化成分容
    CELL_FORMATION = "cell_formation"
    # 模组/电池包组装
    PACK_ASSEMBLY = "pack_assembly"
    # 系统集成
    SYSTEM_INTEGRATION = "system_integration"
    # 辅料制造
    AUXILIARY = "auxiliary"


@dataclass
class BatteryRecipe:
    """
    储能电池制造配方
    
    属性:
        name: 配方名称
        station_type: 工站类型
        inputs: 输入物品及数量
        outputs: 输出物品及数量
        process_time: 加工时间 (秒)
        energy_cost: 能耗 (焦耳)
        quality_params: 质量参数
        recipe_type: 配方类型
        description: 描述
    """
    name: str
    station_type: str
    inputs: Dict[str, int]
    outputs: Dict[str, int]
    process_time: float  # seconds
    energy_cost: float   # Joules
    quality_params: Dict = field(default_factory=dict)
    recipe_type: BatteryRecipeType = BatteryRecipeType.AUXILIARY
    description: str = ""
    
    def get_input_total_mass(self, item_registry) -> float:
        """计算输入物品总质量"""
        total = 0.0
        for item_type, quantity in self.inputs.items():
            if item_type in item_registry:
                total += item_registry[item_type].mass * quantity
        return total
    
    def get_output_total_mass(self, item_registry) -> float:
        """计算输出物品总质量"""
        total = 0.0
        for item_type, quantity in self.outputs.items():
            if item_type in item_registry:
                total += item_registry[item_type].mass * quantity
        return total
    
    def get_mass_yield(self, item_registry) -> float:
        """计算质量收率"""
        input_mass = self.get_input_total_mass(item_registry)
        output_mass = self.get_output_total_mass(item_registry)
        if input_mass > 0:
            return output_mass / input_mass
        return 0.0


# ============================================================================
# 储能电池制造配方定义
# ============================================================================

BATTERY_RECIPES: List[BatteryRecipe] = [
    
    # ========================================================================
    # 上游: 原材料提炼
    # ========================================================================
    
    BatteryRecipe(
        name="refine_lithium_carbonate",
        station_type="lithium_refinery",
        inputs={"lithium_ore": 10, "limestone": 2},
        outputs={"lithium_carbonate": 3},
        process_time=180.0,
        energy_cost=2500.0,
        quality_params={
            "purity": "99.5%",
            "type": "battery_grade",
            "form": "powder"
        },
        recipe_type=BatteryRecipeType.MATERIAL_REFINING,
        description="锂矿提纯为碳酸锂(Li2CO3)"
    ),
    
    BatteryRecipe(
        name="refine_lithium_hydroxide",
        station_type="lithium_refinery",
        inputs={"lithium_ore": 10, "lime": 2},
        outputs={"lithium_hydroxide": 3},
        process_time=180.0,
        energy_cost=2500.0,
        quality_params={
            "purity": "99.0%",
            "type": "battery_grade",
            "form": "powder"
        },
        recipe_type=BatteryRecipeType.MATERIAL_REFINING,
        description="锂矿提纯为氢氧化锂(LiOH)"
    ),
    
    BatteryRecipe(
        name="refine_cobalt",
        station_type="lithium_refinery",
        inputs={"cobalt_ore": 5, "sulfuric_acid": 2},
        outputs={"cobalt_sulfate": 2},
        process_time=150.0,
        energy_cost=2000.0,
        quality_params={
            "purity": "99.8%",
            "type": "CoSO4·7H2O",
            "form": "crystal"
        },
        recipe_type=BatteryRecipeType.MATERIAL_REFINING,
        description="钴矿提炼为硫酸钴"
    ),
    
    BatteryRecipe(
        name="refine_nickel",
        station_type="lithium_refinery",
        inputs={"nickel_ore": 5, "sulfuric_acid": 2},
        outputs={"nickel_sulfate": 2},
        process_time=150.0,
        energy_cost=2000.0,
        quality_params={
            "purity": "99.9%",
            "type": "NiSO4·6H2O",
            "form": "crystal"
        },
        recipe_type=BatteryRecipeType.MATERIAL_REFINING,
        description="镍矿提炼为硫酸镍"
    ),
    
    BatteryRecipe(
        name="refine_manganese",
        station_type="lithium_refinery",
        inputs={"manganese_ore": 5, "sulfuric_acid": 2},
        outputs={"manganese_sulfate": 2},
        process_time=120.0,
        energy_cost=1500.0,
        quality_params={
            "purity": "99.5%",
            "type": "MnSO4·H2O",
            "form": "powder"
        },
        recipe_type=BatteryRecipeType.MATERIAL_REFINING,
        description="锰矿提炼为硫酸锰"
    ),
    
    BatteryRecipe(
        name="make_electrolyte",
        station_type="lithium_refinery",
        inputs={"lithium_salt": 1, "organic_solvent": 3},
        outputs={"electrolyte": 2},
        process_time=90.0,
        energy_cost=500.0,
        quality_params={
            "type": "LiPF6",
            "concentration": "1.0M",
            "solvent": "EC/DMC"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="电解液配制"
    ),
    
    # ========================================================================
    # 中游: 正极材料合成
    # ========================================================================
    
    BatteryRecipe(
        name="make_lfp_cathode",
        station_type="cathode_synthesizer",
        inputs={
            "lithium_carbonate": 1,
            "iron_phosphate": 1,
            "carbon_source": 1
        },
        outputs={"lfp_cathode": 1},
        process_time=300.0,
        energy_cost=4000.0,
        quality_params={
            "type": "LFP",
            "capacity": "160mAh/g",
            "voltage": "3.2V",
            "cycles": "6000+"
        },
        recipe_type=BatteryRecipeType.CATHODE_SYNTHESIS,
        description="磷酸铁锂(LFP)正极材料合成"
    ),
    
    BatteryRecipe(
        name="make_ncm_cathode",
        station_type="cathode_synthesizer",
        inputs={
            "lithium_hydroxide": 1,
            "nickel_sulfate": 2,
            "cobalt_sulfate": 1,
            "manganese_sulfate": 1
        },
        outputs={"ncm_cathode": 2},
        process_time=360.0,
        energy_cost=5000.0,
        quality_params={
            "type": "NCM811",
            "capacity": "200mAh/g",
            "voltage": "3.7V",
            "cycles": "2000+"
        },
        recipe_type=BatteryRecipeType.CATHODE_SYNTHESIS,
        description="三元(NCM811)正极材料合成"
    ),
    
    BatteryRecipe(
        name="make_ncm523_cathode",
        station_type="cathode_synthesizer",
        inputs={
            "lithium_hydroxide": 1,
            "nickel_sulfate": 1,
            "cobalt_sulfate": 1,
            "manganese_sulfate": 2
        },
        outputs={"ncm_cathode": 2},
        process_time=340.0,
        energy_cost=4500.0,
        quality_params={
            "type": "NCM523",
            "capacity": "170mAh/g",
            "voltage": "3.6V",
            "cycles": "3000+"
        },
        recipe_type=BatteryRecipeType.CATHODE_SYNTHESIS,
        description="三元(NCM523)正极材料合成"
    ),
    
    BatteryRecipe(
        name="make_lco_cathode",
        station_type="cathode_synthesizer",
        inputs={
            "lithium_carbonate": 1,
            "cobalt_sulfate": 2
        },
        outputs={"lco_cathode": 1},
        process_time=280.0,
        energy_cost=3500.0,
        quality_params={
            "type": "LCO",
            "capacity": "145mAh/g",
            "voltage": "3.7V",
            "cycles": "500+"
        },
        recipe_type=BatteryRecipeType.CATHODE_SYNTHESIS,
        description="钴酸锂(LCO)正极材料合成(消费电子)"
    ),
    
    BatteryRecipe(
        name="make_lmo_cathode",
        station_type="cathode_synthesizer",
        inputs={
            "lithium_carbonate": 1,
            "manganese_sulfate": 2
        },
        outputs={"lmo_cathode": 1},
        process_time=260.0,
        energy_cost=3000.0,
        quality_params={
            "type": "LMO",
            "capacity": "120mAh/g",
            "voltage": "4.0V",
            "cycles": "2000+"
        },
        recipe_type=BatteryRecipeType.CATHODE_SYNTHESIS,
        description="锰酸锂(LMO)正极材料合成"
    ),
    
    # ========================================================================
    # 中游: 负极材料加工
    # ========================================================================
    
    BatteryRecipe(
        name="process_graphite_anode",
        station_type="anode_processor",
        inputs={"graphite_ore": 5},
        outputs={"graphite_anode": 2, "graphite_waste": 1},
        process_time=240.0,
        energy_cost=6000.0,
        quality_params={
            "capacity": "360mAh/g",
            "type": "artificial",
            "graphitization": "99.9%"
        },
        recipe_type=BatteryRecipeType.ANODE_PROCESSING,
        description="石墨化处理(2800°C高温)"
    ),
    
    BatteryRecipe(
        name="make_silicon_anode",
        station_type="anode_processor",
        inputs={"graphite_anode": 1, "silicon_powder": 1},
        outputs={"silicon_anode": 1},
        process_time=180.0,
        energy_cost=3000.0,
        quality_params={
            "capacity": "500mAh/g",
            "si_content": "5%",
            "type": "Si/C_composite"
        },
        recipe_type=BatteryRecipeType.ANODE_PROCESSING,
        description="硅碳复合负极材料制造"
    ),
    
    BatteryRecipe(
        name="make_hard_carbon_anode",
        station_type="anode_processor",
        inputs={"biomass": 3},
        outputs={"hard_carbon_anode": 1},
        process_time=200.0,
        energy_cost=2500.0,
        quality_params={
            "capacity": "300mAh/g",
            "type": "hard_carbon",
            "application": "sodium_ion"
        },
        recipe_type=BatteryRecipeType.ANODE_PROCESSING,
        description="硬碳负极材料制造(钠离子电池)"
    ),
    
    # ========================================================================
    # 中游: 电极制造
    # ========================================================================
    
    BatteryRecipe(
        name="coat_cathode_lfp",
        station_type="electrode_coater",
        inputs={
            "lfp_cathode": 1,
            "aluminum_foil": 1,
            "binder": 1,
            "conductive_agent": 1
        },
        outputs={"cathode_sheet": 10},
        process_time=120.0,
        energy_cost=1500.0,
        quality_params={
            "loading": "15mg/cm²",
            "thickness": "100μm",
            "density": "2.3g/cm³"
        },
        recipe_type=BatteryRecipeType.ELECTRODE_MANUFACTURING,
        description="LFP正极极片涂布"
    ),
    
    BatteryRecipe(
        name="coat_cathode_ncm",
        station_type="electrode_coater",
        inputs={
            "ncm_cathode": 1,
            "aluminum_foil": 1,
            "binder": 1,
            "conductive_agent": 1
        },
        outputs={"cathode_sheet": 10},
        process_time=130.0,
        energy_cost=1600.0,
        quality_params={
            "loading": "20mg/cm²",
            "thickness": "120μm",
            "density": "3.5g/cm³"
        },
        recipe_type=BatteryRecipeType.ELECTRODE_MANUFACTURING,
        description="NCM正极极片涂布"
    ),
    
    BatteryRecipe(
        name="coat_anode_graphite",
        station_type="electrode_coater",
        inputs={
            "graphite_anode": 1,
            "copper_foil": 1,
            "binder": 1,
            "conductive_agent": 1
        },
        outputs={"anode_sheet": 10},
        process_time=120.0,
        energy_cost=1500.0,
        quality_params={
            "loading": "8mg/cm²",
            "thickness": "80μm",
            "density": "1.5g/cm³"
        },
        recipe_type=BatteryRecipeType.ELECTRODE_MANUFACTURING,
        description="石墨负极极片涂布"
    ),
    
    BatteryRecipe(
        name="coat_anode_silicon",
        station_type="electrode_coater",
        inputs={
            "silicon_anode": 1,
            "copper_foil": 1,
            "binder": 2,
            "conductive_agent": 1
        },
        outputs={"anode_sheet": 10},
        process_time=140.0,
        energy_cost=1800.0,
        quality_params={
            "loading": "6mg/cm²",
            "thickness": "70μm",
            "density": "1.2g/cm³"
        },
        recipe_type=BatteryRecipeType.ELECTRODE_MANUFACTURING,
        description="硅碳负极极片涂布"
    ),
    
    # ========================================================================
    # 中游: 电芯制造
    # ========================================================================
    
    BatteryRecipe(
        name="assemble_cell_lfp",
        station_type="cell_assembler",
        inputs={
            "cathode_sheet": 1,
            "anode_sheet": 1,
            "separator": 2,
            "electrolyte": 1,
            "cell_can": 1
        },
        outputs={"battery_cell": 1},
        process_time=180.0,
        energy_cost=800.0,
        quality_params={
            "format": "prismatic",
            "capacity": "280Ah",
            "voltage": "3.2V",
            "type": "LFP"
        },
        recipe_type=BatteryRecipeType.CELL_MANUFACTURING,
        description="LFP方形电芯组装"
    ),
    
    BatteryRecipe(
        name="assemble_cell_ncm",
        station_type="cell_assembler",
        inputs={
            "cathode_sheet": 1,
            "anode_sheet": 1,
            "separator": 2,
            "electrolyte": 1,
            "cell_can": 1
        },
        outputs={"battery_cell": 1},
        process_time=180.0,
        energy_cost=800.0,
        quality_params={
            "format": "prismatic",
            "capacity": "230Ah",
            "voltage": "3.7V",
            "type": "NCM"
        },
        recipe_type=BatteryRecipeType.CELL_MANUFACTURING,
        description="NCM方形电芯组装"
    ),
    
    BatteryRecipe(
        name="assemble_cell_cylindrical",
        station_type="cell_assembler",
        inputs={
            "cathode_sheet": 1,
            "anode_sheet": 1,
            "separator": 2,
            "electrolyte": 1,
            "cylindrical_can": 1
        },
        outputs={"battery_cell": 1},
        process_time=150.0,
        energy_cost=700.0,
        quality_params={
            "format": "cylindrical",
            "capacity": "50Ah",
            "voltage": "3.6V",
            "size": "4680"
        },
        recipe_type=BatteryRecipeType.CELL_MANUFACTURING,
        description="圆柱电芯组装(4680规格)"
    ),
    
    BatteryRecipe(
        name="assemble_cell_pouch",
        station_type="cell_assembler",
        inputs={
            "cathode_sheet": 1,
            "anode_sheet": 1,
            "separator": 2,
            "electrolyte": 1,
            "pouch_film": 2
        },
        outputs={"battery_cell": 1},
        process_time=160.0,
        energy_cost=750.0,
        quality_params={
            "format": "pouch",
            "capacity": "100Ah",
            "voltage": "3.7V",
            "type": "NCM"
        },
        recipe_type=BatteryRecipeType.CELL_MANUFACTURING,
        description="软包电芯组装"
    ),
    
    # ========================================================================
    # 中游: 化成分容
    # ========================================================================
    
    BatteryRecipe(
        name="form_cell",
        station_type="cell_formation",
        inputs={"battery_cell": 1},
        outputs={"formed_cell": 1},
        process_time=600.0,
        energy_cost=500.0,
        quality_params={
            "cycles": "6000+",
            "efficiency": "95%",
            "formation_cycles": 3
        },
        recipe_type=BatteryRecipeType.CELL_FORMATION,
        description="电芯化成激活"
    ),
    
    BatteryRecipe(
        name="test_cell_capacity",
        station_type="cell_formation",
        inputs={"formed_cell": 1},
        outputs={"tested_cell": 1},
        process_time=300.0,
        energy_cost=200.0,
        quality_params={
            "test_type": "capacity",
            "grade": "A"
        },
        recipe_type=BatteryRecipeType.CELL_FORMATION,
        description="电芯容量测试分选"
    ),
    
    # ========================================================================
    # 下游: 模组组装
    # ========================================================================
    
    BatteryRecipe(
        name="assemble_module_1p2s",
        station_type="module_assembler",
        inputs={
            "formed_cell": 2,
            "busbar": 3,
            "bms_board": 1,
            "thermal_pad": 2,
            "module_frame": 1
        },
        outputs={"battery_module": 1},
        process_time=180.0,
        energy_cost=500.0,
        quality_params={
            "voltage": "6.4V",
            "capacity": "280Ah",
            "cells": 2,
            "config": "1P2S"
        },
        recipe_type=BatteryRecipeType.PACK_ASSEMBLY,
        description="2串模组组装"
    ),
    
    BatteryRecipe(
        name="assemble_module_1p4s",
        station_type="module_assembler",
        inputs={
            "formed_cell": 4,
            "busbar": 5,
            "bms_board": 1,
            "thermal_pad": 4,
            "module_frame": 1
        },
        outputs={"battery_module": 1},
        process_time=240.0,
        energy_cost=600.0,
        quality_params={
            "voltage": "12.8V",
            "capacity": "280Ah",
            "cells": 4,
            "config": "1P4S"
        },
        recipe_type=BatteryRecipeType.PACK_ASSEMBLY,
        description="4串模组组装(48V系统基础)"
    ),
    
    BatteryRecipe(
        name="assemble_module_1p16s",
        station_type="module_assembler",
        inputs={
            "formed_cell": 16,
            "busbar": 17,
            "bms_board": 1,
            "thermal_pad": 16,
            "module_frame": 1
        },
        outputs={"battery_module": 1},
        process_time=400.0,
        energy_cost=1000.0,
        quality_params={
            "voltage": "51.2V",
            "capacity": "280Ah",
            "cells": 16,
            "config": "1P16S"
        },
        recipe_type=BatteryRecipeType.PACK_ASSEMBLY,
        description="16串模组组装"
    ),
    
    # ========================================================================
    # 下游: 电池包组装
    # ========================================================================
    
    BatteryRecipe(
        name="assemble_pack_small",
        station_type="pack_assembler",
        inputs={
            "battery_module": 1,
            "cooling_plate": 1,
            "hv_connector": 2,
            "pack_enclosure": 1,
            "main_bms": 1
        },
        outputs={"battery_pack": 1},
        process_time=300.0,
        energy_cost=800.0,
        quality_params={
            "voltage": "51.2V",
            "capacity": "14.3kWh",
            "modules": 1,
            "type": "residential"
        },
        recipe_type=BatteryRecipeType.PACK_ASSEMBLY,
        description="户用储能电池包组装"
    ),
    
    BatteryRecipe(
        name="assemble_pack_medium",
        station_type="pack_assembler",
        inputs={
            "battery_module": 4,
            "cooling_plate": 2,
            "hv_connector": 4,
            "pack_enclosure": 1,
            "main_bms": 1
        },
        outputs={"battery_pack": 1},
        process_time=360.0,
        energy_cost=1000.0,
        quality_params={
            "voltage": "51.2V",
            "capacity": "57.2kWh",
            "modules": 4,
            "type": "commercial"
        },
        recipe_type=BatteryRecipeType.PACK_ASSEMBLY,
        description="工商业储能电池包组装"
    ),
    
    BatteryRecipe(
        name="assemble_pack_large",
        station_type="pack_assembler",
        inputs={
            "battery_module": 8,
            "cooling_plate": 4,
            "hv_connector": 8,
            "pack_enclosure": 1,
            "main_bms": 1
        },
        outputs={"battery_pack": 1},
        process_time=450.0,
        energy_cost=1200.0,
        quality_params={
            "voltage": "102.4V",
            "capacity": "114.4kWh",
            "modules": 8,
            "type": "utility"
        },
        recipe_type=BatteryRecipeType.PACK_ASSEMBLY,
        description="大型储能电池包组装"
    ),
    
    # ========================================================================
    # 下游: 储能系统集成
    # ========================================================================
    
    BatteryRecipe(
        name="integrate_ess_small",
        station_type="ess_integrator",
        inputs={
            "battery_pack": 1,
            "pcs_unit": 1,
            "master_bms": 1,
            "fire_suppression": 1,
            "thermal_system": 1
        },
        outputs={"energy_storage_system": 1},
        process_time=400.0,
        energy_cost=1200.0,
        quality_params={
            "power": "10kW",
            "capacity": "14.3kWh",
            "type": "residential",
            "ac_voltage": "220V"
        },
        recipe_type=BatteryRecipeType.SYSTEM_INTEGRATION,
        description="户用储能系统集成"
    ),
    
    BatteryRecipe(
        name="integrate_ess_medium",
        station_type="ess_integrator",
        inputs={
            "battery_pack": 4,
            "pcs_unit": 1,
            "master_bms": 1,
            "fire_suppression": 1,
            "container": 1
        },
        outputs={"energy_storage_system": 1},
        process_time=480.0,
        energy_cost=1500.0,
        quality_params={
            "power": "50kW",
            "capacity": "57.2kWh",
            "type": "commercial",
            "ac_voltage": "380V"
        },
        recipe_type=BatteryRecipeType.SYSTEM_INTEGRATION,
        description="工商业储能系统集成"
    ),
    
    BatteryRecipe(
        name="integrate_ess_large",
        station_type="ess_integrator",
        inputs={
            "battery_pack": 8,
            "pcs_unit": 2,
            "master_bms": 1,
            "fire_suppression": 2,
            "container": 1
        },
        outputs={"energy_storage_system": 1},
        process_time=600.0,
        energy_cost=2000.0,
        quality_params={
            "power": "100kW",
            "capacity": "229kWh",
            "type": "utility",
            "ac_voltage": "10kV"
        },
        recipe_type=BatteryRecipeType.SYSTEM_INTEGRATION,
        description="电网级储能系统集成"
    ),
    
    BatteryRecipe(
        name="integrate_ess_megawatt",
        station_type="ess_integrator",
        inputs={
            "energy_storage_system": 10,
            "transformer": 1,
            "grid_controller": 1,
            "hvac_system": 2,
            "container": 2
        },
        outputs={"megawatt_ess": 1},
        process_time=900.0,
        energy_cost=5000.0,
        quality_params={
            "power": "1MW",
            "capacity": "2MWh",
            "type": "grid_scale",
            "ac_voltage": "35kV"
        },
        recipe_type=BatteryRecipeType.SYSTEM_INTEGRATION,
        description="兆瓦级储能系统集成"
    ),
    
    # ========================================================================
    # 辅料制造
    # ========================================================================
    
    BatteryRecipe(
        name="make_separator",
        station_type="fabricator",
        inputs={"pe_pellet": 1, "pp_pellet": 1},
        outputs={"separator": 10},
        process_time=60.0,
        energy_cost=400.0,
        quality_params={
            "thickness": "20μm",
            "porosity": "40%",
            "type": "PE/PP"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="隔膜制造"
    ),
    
    BatteryRecipe(
        name="make_ceramic_separator",
        station_type="fabricator",
        inputs={"separator": 1, "ceramic_coating": 1},
        outputs={"ceramic_separator": 1},
        process_time=45.0,
        energy_cost=300.0,
        quality_params={
            "thickness": "25μm",
            "heat_resistance": ">180°C",
            "type": "ceramic_coated"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="陶瓷涂覆隔膜制造"
    ),
    
    BatteryRecipe(
        name="make_cell_can",
        station_type="fabricator",
        inputs={"aluminum_sheet": 1},
        outputs={"cell_can": 1},
        process_time=45.0,
        energy_cost=300.0,
        quality_params={
            "type": "prismatic",
            "thickness": "1.5mm",
            "coating": "insulated"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="方形电芯外壳制造"
    ),
    
    BatteryRecipe(
        name="make_cylindrical_can",
        station_type="fabricator",
        inputs={"steel_sheet": 1},
        outputs={"cylindrical_can": 1},
        process_time=40.0,
        energy_cost=280.0,
        quality_params={
            "type": "cylindrical",
            "size": "4680",
            "plating": "nickel"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="圆柱电芯外壳制造"
    ),
    
    BatteryRecipe(
        name="make_busbar",
        station_type="fabricator",
        inputs={"copper_bar": 1},
        outputs={"busbar": 3},
        process_time=30.0,
        energy_cost=200.0,
        quality_params={
            "material": "copper",
            "rating": "300A",
            "plating": "tin"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="汇流排制造"
    ),
    
    BatteryRecipe(
        name="make_bms_board",
        station_type="fabricator",
        inputs={"pcb": 1, "ic_chips": 5, "connector": 2},
        outputs={"bms_board": 1},
        process_time=60.0,
        energy_cost=400.0,
        quality_params={
            "channels": "4S",
            "type": "slave",
            "protocol": "CAN"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="BMS从控板制造"
    ),
    
    BatteryRecipe(
        name="make_thermal_pad",
        station_type="fabricator",
        inputs={"silicone": 1, "ceramic_powder": 1},
        outputs={"thermal_pad": 5},
        process_time=40.0,
        energy_cost=250.0,
        quality_params={
            "conductivity": "6W/mK",
            "thickness": "2mm",
            "type": "gap_filler"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="导热垫制造"
    ),
    
    BatteryRecipe(
        name="make_cooling_plate",
        station_type="fabricator",
        inputs={"aluminum_plate": 2, "copper_tube": 1},
        outputs={"cooling_plate": 1},
        process_time=80.0,
        energy_cost=500.0,
        quality_params={
            "type": "liquid_cooled",
            "flow_rate": "10L/min",
            "pressure_drop": "<50kPa"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="液冷板制造"
    ),
    
    BatteryRecipe(
        name="make_pcs_unit",
        station_type="fabricator",
        inputs={
            "inverter_module": 2,
            "dc_dc_converter": 2,
            "control_board": 1,
            "heat_sink": 1
        },
        outputs={"pcs_unit": 1},
        process_time=120.0,
        energy_cost=800.0,
        quality_params={
            "power": "50kW",
            "type": "bidirectional",
            "efficiency": "97%"
        },
        recipe_type=BatteryRecipeType.AUXILIARY,
        description="PCS功率转换系统制造"
    ),
]


# ============================================================================
# 配方查询工具函数
# ============================================================================

def get_recipes_by_station(station_type: str) -> List[BatteryRecipe]:
    """获取指定工站类型的所有配方"""
    return [r for r in BATTERY_RECIPES if r.station_type == station_type]


def get_recipes_by_type(recipe_type: BatteryRecipeType) -> List[BatteryRecipe]:
    """获取指定类型的所有配方"""
    return [r for r in BATTERY_RECIPES if r.recipe_type == recipe_type]


def get_recipe_by_name(name: str) -> Optional[BatteryRecipe]:
    """根据名称获取配方"""
    for recipe in BATTERY_RECIPES:
        if recipe.name == name:
            return recipe
    return None


def get_recipe_for_output(output_type: str) -> List[BatteryRecipe]:
    """获取能产出指定物品的所有配方"""
    return [r for r in BATTERY_RECIPES if output_type in r.outputs]


def get_recipe_for_input(input_type: str) -> List[BatteryRecipe]:
    """获取需要指定物品作为输入的所有配方"""
    return [r for r in BATTERY_RECIPES if input_type in r.inputs]


# ============================================================================
# 配方依赖分析
# ============================================================================

def build_battery_recipe_dependency_graph():
    """
    构建电池配方依赖图
    
    返回:
        Dict[str, List[str]]: 物品 -> 可由哪些配方产出
        Dict[str, List[str]]: 物品 -> 被哪些配方消耗
    """
    output_to_recipes: Dict[str, List[str]] = {}
    input_to_recipes: Dict[str, List[str]] = {}
    
    for recipe in BATTERY_RECIPES:
        # 记录产出关系
        for output in recipe.outputs:
            if output not in output_to_recipes:
                output_to_recipes[output] = []
            output_to_recipes[output].append(recipe.name)
        
        # 记录消耗关系
        for input_item in recipe.inputs:
            if input_item not in input_to_recipes:
                input_to_recipes[input_item] = []
            input_to_recipes[input_item].append(recipe.name)
    
    return output_to_recipes, input_to_recipes


def calculate_material_requirement(target_item: str, target_quantity: int = 1) -> Dict[str, int]:
    """
    计算制造目标物品所需的原材料总量
    
    参数:
        target_item: 目标物品
        target_quantity: 目标数量
    
    返回:
        Dict[str, int]: 原材料 -> 所需数量
    """
    materials: Dict[str, int] = {}
    
    def recurse(item: str, quantity: int):
        recipes = get_recipe_for_output(item)
        if not recipes:
            # 原材料，直接累加
            materials[item] = materials.get(item, 0) + quantity
            return
        
        # 选择第一个配方（简化处理）
        recipe = recipes[0]
        
        # 计算需要运行多少次配方
        output_per_run = recipe.outputs.get(item, 1)
        runs_needed = (quantity + output_per_run - 1) // output_per_run
        
        # 递归计算输入
        for input_item, input_qty in recipe.inputs.items():
            recurse(input_item, input_qty * runs_needed)
    
    recurse(target_item, target_quantity)
    return materials


def print_battery_dependency_tree(target_item: str = "energy_storage_system", indent: int = 0):
    """
    打印电池制造依赖树
    
    参数:
        target_item: 目标物品
        indent: 缩进级别
    """
    prefix = "  " * indent
    recipes = get_recipe_for_output(target_item)
    
    if not recipes:
        print(f"{prefix}└── {target_item} (原材料)")
        return
    
    recipe = recipes[0]  # 选择第一个配方
    output_qty = recipe.outputs.get(target_item, 1)
    
    print(f"{prefix}├── {target_item} ({output_qty})")
    
    for input_item, input_qty in recipe.inputs.items():
        print(f"{prefix}│   ├── {input_item} ({input_qty})")
        print_battery_dependency_tree(input_item, indent + 2)


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    # 打印配方统计
    print("=" * 60)
    print("储能电池制造配方系统统计")
    print("=" * 60)
    
    print(f"\n总配方数: {len(BATTERY_RECIPES)}")
    
    # 按类型统计
    print("\n按配方类型统计:")
    for recipe_type in BatteryRecipeType:
        count = len([r for r in BATTERY_RECIPES if r.recipe_type == recipe_type])
        print(f"  {recipe_type.value}: {count}")
    
    # 按工站统计
    print("\n按工站类型统计:")
    station_types = set(r.station_type for r in BATTERY_RECIPES)
    for station in sorted(station_types):
        count = len([r for r in BATTERY_RECIPES if r.station_type == station])
        print(f"  {station}: {count}")
    
    # 打印依赖树
    print("\n" + "=" * 60)
    print("储能系统制造依赖树 (energy_storage_system)")
    print("=" * 60)
    print_battery_dependency_tree("energy_storage_system")
    
    # 计算原材料需求
    print("\n" + "=" * 60)
    print("制造1套50kW/57.2kWh储能系统所需原材料")
    print("=" * 60)
    materials = calculate_material_requirement("energy_storage_system", 1)
    for item, qty in sorted(materials.items()):
        print(f"  {item}: {qty}")
