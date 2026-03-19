"""
储能电池制造物品定义

定义储能电池系统制造全产业链所需的所有物品类型。
包括: 原材料、中间产品、辅料、最终产品等。

文件: src/world/battery_items.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class BatteryItemType(Enum):
    """电池物品类型"""
    RAW_MATERIAL = "raw_material"       # 原材料
    INTERMEDIATE = "intermediate"       # 中间产品
    CONSUMABLE = "consumable"           # 消耗品
    COMPONENT = "component"             # 组件
    FINAL_PRODUCT = "final_product"     # 最终产品


@dataclass
class BatteryItem:
    """
    储能电池制造物品定义
    
    属性:
        item_id: 物品ID
        item_type: 物品类型分类
        mass: 质量 (kg)
        size: 尺寸 (长x宽x高, 米)
        mesh_path: 3D模型路径
        properties: 物品属性
        description: 描述
    """
    item_id: str
    item_type: BatteryItemType
    mass: float
    size: Tuple[float, float, float]
    mesh_path: str = ""
    properties: Dict = field(default_factory=dict)
    description: str = ""
    
    def get_volume(self) -> float:
        """计算体积 (m³)"""
        return self.size[0] * self.size[1] * self.size[2]
    
    def get_density(self) -> float:
        """计算密度 (kg/m³)"""
        volume = self.get_volume()
        if volume > 0:
            return self.mass / volume
        return 0.0


# ============================================================================
# 储能电池物品注册表
# ============================================================================

BATTERY_ITEM_REGISTRY: Dict[str, BatteryItem] = {
    
    # ========================================================================
    # 原材料 - 矿石
    # ========================================================================
    
    "lithium_ore": BatteryItem(
        item_id="lithium_ore",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=2.0,
        size=(0.10, 0.10, 0.08),
        mesh_path="assets/parts/lithium_ore.usd",
        properties={
            "type": "spodumene",
            "li2o_content": "6%"
        },
        description="锂矿石，用于提炼锂化合物"
    ),
    
    "cobalt_ore": BatteryItem(
        item_id="cobalt_ore",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=2.5,
        size=(0.10, 0.10, 0.08),
        mesh_path="assets/parts/cobalt_ore.usd",
        properties={
            "type": "cobaltite",
            "co_content": "10%"
        },
        description="钴矿石，用于提炼钴化合物"
    ),
    
    "nickel_ore": BatteryItem(
        item_id="nickel_ore",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=2.2,
        size=(0.10, 0.10, 0.08),
        mesh_path="assets/parts/nickel_ore.usd",
        properties={
            "type": "laterite",
            "ni_content": "1.5%"
        },
        description="镍矿石，用于提炼镍化合物"
    ),
    
    "manganese_ore": BatteryItem(
        item_id="manganese_ore",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=2.0,
        size=(0.10, 0.10, 0.08),
        mesh_path="assets/parts/manganese_ore.usd",
        properties={
            "type": "pyrolusite",
            "mn_content": "40%"
        },
        description="锰矿石，用于提炼锰化合物"
    ),
    
    "graphite_ore": BatteryItem(
        item_id="graphite_ore",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=1.8,
        size=(0.12, 0.10, 0.08),
        mesh_path="assets/parts/graphite_ore.usd",
        properties={
            "type": "natural",
            "carbon": "90%"
        },
        description="石墨矿，用于制造负极材料"
    ),
    
    # ========================================================================
    # 原材料 - 其他
    # ========================================================================
    
    "limestone": BatteryItem(
        item_id="limestone",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=2.0,
        size=(0.10, 0.10, 0.08),
        mesh_path="assets/parts/limestone.usd",
        properties={
            "type": "calcium_carbonate",
            "purity": ">95%"
        },
        description="石灰石，用于锂提炼"
    ),
    
    "lime": BatteryItem(
        item_id="lime",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=1.5,
        size=(0.08, 0.08, 0.06),
        mesh_path="assets/parts/lime.usd",
        properties={
            "type": "calcium_oxide",
            "purity": ">90%"
        },
        description="生石灰，用于锂提炼"
    ),
    
    "sulfuric_acid": BatteryItem(
        item_id="sulfuric_acid",
        item_type=BatteryItemType.CONSUMABLE,
        mass=1.8,
        size=(0.10, 0.10, 0.15),
        mesh_path="assets/parts/sulfuric_acid.usd",
        properties={
            "concentration": "98%",
            "type": "industrial"
        },
        description="硫酸，用于金属提炼"
    ),
    
    "biomass": BatteryItem(
        item_id="biomass",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=1.0,
        size=(0.15, 0.10, 0.08),
        mesh_path="assets/parts/biomass.usd",
        properties={
            "type": "organic",
            "carbon_content": "50%"
        },
        description="生物质，用于硬碳负极制造"
    ),
    
    # ========================================================================
    # 中间产品 - 锂化合物
    # ========================================================================
    
    "lithium_carbonate": BatteryItem(
        item_id="lithium_carbonate",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.0,
        size=(0.15, 0.10, 0.05),
        mesh_path="assets/parts/lithium_carbonate.usd",
        properties={
            "purity": "99.5%",
            "type": "battery_grade",
            "form": "powder"
        },
        description="碳酸锂(Li2CO3)，用于LFP正极"
    ),
    
    "lithium_hydroxide": BatteryItem(
        item_id="lithium_hydroxide",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.0,
        size=(0.15, 0.10, 0.05),
        mesh_path="assets/parts/lithium_hydroxide.usd",
        properties={
            "purity": "99.0%",
            "type": "battery_grade",
            "form": "powder"
        },
        description="氢氧化锂(LiOH)，用于NCM正极"
    ),
    
    "lithium_salt": BatteryItem(
        item_id="lithium_salt",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=0.5,
        size=(0.08, 0.08, 0.05),
        mesh_path="assets/parts/lithium_salt.usd",
        properties={
            "type": "LiPF6",
            "purity": "99.9%"
        },
        description="锂盐，用于电解液"
    ),
    
    # ========================================================================
    # 中间产品 - 金属化合物
    # ========================================================================
    
    "cobalt_sulfate": BatteryItem(
        item_id="cobalt_sulfate",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.2,
        size=(0.12, 0.08, 0.05),
        mesh_path="assets/parts/cobalt_sulfate.usd",
        properties={
            "purity": "99.8%",
            "type": "CoSO4·7H2O",
            "form": "crystal"
        },
        description="硫酸钴，用于NCM正极"
    ),
    
    "nickel_sulfate": BatteryItem(
        item_id="nickel_sulfate",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.2,
        size=(0.12, 0.08, 0.05),
        mesh_path="assets/parts/nickel_sulfate.usd",
        properties={
            "purity": "99.9%",
            "type": "NiSO4·6H2O",
            "form": "crystal"
        },
        description="硫酸镍，用于NCM正极"
    ),
    
    "manganese_sulfate": BatteryItem(
        item_id="manganese_sulfate",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.0,
        size=(0.12, 0.08, 0.05),
        mesh_path="assets/parts/manganese_sulfate.usd",
        properties={
            "purity": "99.5%",
            "type": "MnSO4·H2O",
            "form": "powder"
        },
        description="硫酸锰，用于NCM正极"
    ),
    
    "iron_phosphate": BatteryItem(
        item_id="iron_phosphate",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.5,
        size=(0.12, 0.10, 0.05),
        mesh_path="assets/parts/iron_phosphate.usd",
        properties={
            "purity": "99%",
            "type": "FePO4",
            "form": "powder"
        },
        description="磷酸铁，用于LFP正极"
    ),
    
    # ========================================================================
    # 中间产品 - 正极材料
    # ========================================================================
    
    "lfp_cathode": BatteryItem(
        item_id="lfp_cathode",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=2.0,
        size=(0.20, 0.15, 0.05),
        mesh_path="assets/parts/lfp_cathode.usd",
        properties={
            "type": "LFP",
            "capacity": "160mAh/g",
            "voltage": "3.2V"
        },
        description="磷酸铁锂正极材料"
    ),
    
    "ncm_cathode": BatteryItem(
        item_id="ncm_cathode",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=2.0,
        size=(0.20, 0.15, 0.05),
        mesh_path="assets/parts/ncm_cathode.usd",
        properties={
            "type": "NCM811",
            "capacity": "200mAh/g",
            "voltage": "3.7V"
        },
        description="三元正极材料"
    ),
    
    "lco_cathode": BatteryItem(
        item_id="lco_cathode",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.8,
        size=(0.20, 0.15, 0.05),
        mesh_path="assets/parts/lco_cathode.usd",
        properties={
            "type": "LCO",
            "capacity": "145mAh/g",
            "voltage": "3.7V"
        },
        description="钴酸锂正极材料(消费电子)"
    ),
    
    "lmo_cathode": BatteryItem(
        item_id="lmo_cathode",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.8,
        size=(0.20, 0.15, 0.05),
        mesh_path="assets/parts/lmo_cathode.usd",
        properties={
            "type": "LMO",
            "capacity": "120mAh/g",
            "voltage": "4.0V"
        },
        description="锰酸锂正极材料"
    ),
    
    # ========================================================================
    # 中间产品 - 负极材料
    # ========================================================================
    
    "graphite_anode": BatteryItem(
        item_id="graphite_anode",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.5,
        size=(0.20, 0.15, 0.05),
        mesh_path="assets/parts/graphite_anode.usd",
        properties={
            "type": "artificial",
            "capacity": "360mAh/g",
            "graphitization": "99.9%"
        },
        description="人造石墨负极材料"
    ),
    
    "graphite_waste": BatteryItem(
        item_id="graphite_waste",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.10, 0.08, 0.05),
        mesh_path="assets/parts/graphite_waste.usd",
        properties={
            "type": "recyclable",
            "carbon": "95%"
        },
        description="石墨废料，可回收"
    ),
    
    "silicon_anode": BatteryItem(
        item_id="silicon_anode",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.5,
        size=(0.20, 0.15, 0.05),
        mesh_path="assets/parts/silicon_anode.usd",
        properties={
            "si_content": "5%",
            "capacity": "500mAh/g",
            "type": "Si/C_composite"
        },
        description="硅碳复合负极材料"
    ),
    
    "silicon_powder": BatteryItem(
        item_id="silicon_powder",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.08, 0.08, 0.05),
        mesh_path="assets/parts/silicon_powder.usd",
        properties={
            "purity": "99.9%",
            "particle_size": "100nm"
        },
        description="硅粉，用于硅碳负极"
    ),
    
    "hard_carbon_anode": BatteryItem(
        item_id="hard_carbon_anode",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=1.2,
        size=(0.20, 0.15, 0.05),
        mesh_path="assets/parts/hard_carbon_anode.usd",
        properties={
            "type": "hard_carbon",
            "capacity": "300mAh/g",
            "application": "sodium_ion"
        },
        description="硬碳负极材料(钠离子电池)"
    ),
    
    # ========================================================================
    # 中间产品 - 电极片
    # ========================================================================
    
    "cathode_sheet": BatteryItem(
        item_id="cathode_sheet",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=0.5,
        size=(0.50, 0.30, 0.0001),
        mesh_path="assets/parts/cathode_sheet.usd",
        properties={
            "loading": "15mg/cm²",
            "thickness": "100μm",
            "density": "2.3g/cm³"
        },
        description="正极极片"
    ),
    
    "anode_sheet": BatteryItem(
        item_id="anode_sheet",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=0.4,
        size=(0.50, 0.30, 0.00008),
        mesh_path="assets/parts/anode_sheet.usd",
        properties={
            "loading": "8mg/cm²",
            "thickness": "80μm",
            "density": "1.5g/cm³"
        },
        description="负极极片"
    ),
    
    # ========================================================================
    # 消耗品 - 集流体
    # ========================================================================
    
    "aluminum_foil": BatteryItem(
        item_id="aluminum_foil",
        item_type=BatteryItemType.CONSUMABLE,
        mass=0.3,
        size=(0.50, 0.30, 0.00002),
        mesh_path="assets/parts/aluminum_foil.usd",
        properties={
            "thickness": "15μm",
            "type": "battery_grade"
        },
        description="铝箔，正极集流体"
    ),
    
    "copper_foil": BatteryItem(
        item_id="copper_foil",
        item_type=BatteryItemType.CONSUMABLE,
        mass=0.5,
        size=(0.50, 0.30, 0.00001),
        mesh_path="assets/parts/copper_foil.usd",
        properties={
            "thickness": "8μm",
            "type": "electrode"
        },
        description="铜箔，负极集流体"
    ),
    
    # ========================================================================
    # 消耗品 - 电解液和隔膜
    # ========================================================================
    
    "electrolyte": BatteryItem(
        item_id="electrolyte",
        item_type=BatteryItemType.CONSUMABLE,
        mass=0.5,
        size=(0.10, 0.10, 0.10),
        mesh_path="assets/parts/electrolyte.usd",
        properties={
            "type": "LiPF6",
            "concentration": "1.0M",
            "solvent": "EC/DMC"
        },
        description="电解液"
    ),
    
    "organic_solvent": BatteryItem(
        item_id="organic_solvent",
        item_type=BatteryItemType.CONSUMABLE,
        mass=0.8,
        size=(0.10, 0.10, 0.10),
        mesh_path="assets/parts/organic_solvent.usd",
        properties={
            "type": "EC/DMC",
            "purity": "99.9%"
        },
        description="有机溶剂，用于电解液"
    ),
    
    "separator": BatteryItem(
        item_id="separator",
        item_type=BatteryItemType.CONSUMABLE,
        mass=0.05,
        size=(0.50, 0.30, 0.00002),
        mesh_path="assets/parts/separator.usd",
        properties={
            "thickness": "20μm",
            "material": "PE/PP",
            "porosity": "40%"
        },
        description="隔膜"
    ),
    
    "ceramic_separator": BatteryItem(
        item_id="ceramic_separator",
        item_type=BatteryItemType.CONSUMABLE,
        mass=0.06,
        size=(0.50, 0.30, 0.000025),
        mesh_path="assets/parts/ceramic_separator.usd",
        properties={
            "thickness": "25μm",
            "heat_resistance": ">180°C",
            "type": "ceramic_coated"
        },
        description="陶瓷涂覆隔膜"
    ),
    
    "ceramic_coating": BatteryItem(
        item_id="ceramic_coating",
        item_type=BatteryItemType.CONSUMABLE,
        mass=0.2,
        size=(0.08, 0.08, 0.03),
        mesh_path="assets/parts/ceramic_coating.usd",
        properties={
            "type": "Al2O3",
            "particle_size": "1μm"
        },
        description="陶瓷涂层材料"
    ),
    
    # ========================================================================
    # 消耗品 - 粘结剂和导电剂
    # ========================================================================
    
    "binder": BatteryItem(
        item_id="binder",
        item_type=BatteryItemType.CONSUMABLE,
        mass=0.3,
        size=(0.08, 0.08, 0.05),
        mesh_path="assets/parts/binder.usd",
        properties={
            "type": "PVDF",
            "purity": "99%"
        },
        description="粘结剂"
    ),
    
    "conductive_agent": BatteryItem(
        item_id="conductive_agent",
        item_type=BatteryItemType.CONSUMABLE,
        mass=0.2,
        size=(0.08, 0.08, 0.05),
        mesh_path="assets/parts/conductive_agent.usd",
        properties={
            "type": "carbon_black",
            "particle_size": "50nm"
        },
        description="导电剂"
    ),
    
    # ========================================================================
    # 组件 - 电芯外壳
    # ========================================================================
    
    "cell_can": BatteryItem(
        item_id="cell_can",
        item_type=BatteryItemType.COMPONENT,
        mass=0.3,
        size=(0.15, 0.10, 0.20),
        mesh_path="assets/parts/cell_can.usd",
        properties={
            "type": "prismatic",
            "material": "aluminum",
            "thickness": "1.5mm"
        },
        description="方形电芯外壳"
    ),
    
    "cylindrical_can": BatteryItem(
        item_id="cylindrical_can",
        item_type=BatteryItemType.COMPONENT,
        mass=0.25,
        size=(0.05, 0.05, 0.08),
        mesh_path="assets/parts/cylindrical_can.usd",
        properties={
            "type": "cylindrical",
            "size": "4680",
            "plating": "nickel"
        },
        description="圆柱电芯外壳(4680规格)"
    ),
    
    "pouch_film": BatteryItem(
        item_id="pouch_film",
        item_type=BatteryItemType.COMPONENT,
        mass=0.1,
        size=(0.20, 0.15, 0.0001),
        mesh_path="assets/parts/pouch_film.usd",
        properties={
            "type": "aluminum_laminated",
            "thickness": "100μm"
        },
        description="软包电芯铝塑膜"
    ),
    
    "aluminum_sheet": BatteryItem(
        item_id="aluminum_sheet",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=1.0,
        size=(0.30, 0.30, 0.002),
        mesh_path="assets/parts/aluminum_sheet.usd",
        properties={
            "type": "aluminum",
            "thickness": "2mm"
        },
        description="铝板，用于制造外壳"
    ),
    
    "steel_sheet": BatteryItem(
        item_id="steel_sheet",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=2.0,
        size=(0.30, 0.30, 0.001),
        mesh_path="assets/parts/steel_sheet.usd",
        properties={
            "type": "stainless",
            "thickness": "1mm"
        },
        description="钢板，用于制造圆柱外壳"
    ),
    
    # ========================================================================
    # 组件 - 电芯
    # ========================================================================
    
    "battery_cell": BatteryItem(
        item_id="battery_cell",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=5.5,
        size=(0.15, 0.10, 0.25),
        mesh_path="assets/parts/battery_cell.usd",
        properties={
            "format": "prismatic",
            "capacity": "280Ah",
            "voltage": "3.2V"
        },
        description="电芯(未化成)"
    ),
    
    "formed_cell": BatteryItem(
        item_id="formed_cell",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=5.5,
        size=(0.15, 0.10, 0.25),
        mesh_path="assets/parts/formed_cell.usd",
        properties={
            "capacity": "280Ah",
            "cycles": "6000+",
            "efficiency": "95%"
        },
        description="化成后的电芯"
    ),
    
    "tested_cell": BatteryItem(
        item_id="tested_cell",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=5.5,
        size=(0.15, 0.10, 0.25),
        mesh_path="assets/parts/tested_cell.usd",
        properties={
            "capacity": "280Ah",
            "grade": "A",
            "test_type": "capacity"
        },
        description="测试分选后的电芯"
    ),
    
    # ========================================================================
    # 组件 - 模组/电池包
    # ========================================================================
    
    "busbar": BatteryItem(
        item_id="busbar",
        item_type=BatteryItemType.COMPONENT,
        mass=0.2,
        size=(0.15, 0.03, 0.01),
        mesh_path="assets/parts/busbar.usd",
        properties={
            "material": "copper",
            "rating": "300A",
            "plating": "tin"
        },
        description="汇流排"
    ),
    
    "copper_bar": BatteryItem(
        item_id="copper_bar",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.30, 0.03, 0.01),
        mesh_path="assets/parts/copper_bar.usd",
        properties={
            "type": "copper",
            "purity": "99.9%"
        },
        description="铜排，用于制造汇流排"
    ),
    
    "bms_board": BatteryItem(
        item_id="bms_board",
        item_type=BatteryItemType.COMPONENT,
        mass=0.3,
        size=(0.15, 0.10, 0.02),
        mesh_path="assets/parts/bms_board.usd",
        properties={
            "channels": "4S",
            "type": "slave",
            "protocol": "CAN"
        },
        description="BMS从控板"
    ),
    
    "thermal_pad": BatteryItem(
        item_id="thermal_pad",
        item_type=BatteryItemType.COMPONENT,
        mass=0.1,
        size=(0.15, 0.10, 0.003),
        mesh_path="assets/parts/thermal_pad.usd",
        properties={
            "conductivity": "6W/mK",
            "thickness": "2mm",
            "type": "gap_filler"
        },
        description="导热垫"
    ),
    
    "module_frame": BatteryItem(
        item_id="module_frame",
        item_type=BatteryItemType.COMPONENT,
        mass=2.0,
        size=(0.50, 0.30, 0.15),
        mesh_path="assets/parts/module_frame.usd",
        properties={
            "material": "aluminum",
            "type": "extruded"
        },
        description="模组框架"
    ),
    
    "battery_module": BatteryItem(
        item_id="battery_module",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=25.0,
        size=(0.50, 0.30, 0.20),
        mesh_path="assets/parts/battery_module.usd",
        properties={
            "voltage": "12.8V",
            "capacity": "280Ah",
            "cells": 4
        },
        description="电池模组"
    ),
    
    "cooling_plate": BatteryItem(
        item_id="cooling_plate",
        item_type=BatteryItemType.COMPONENT,
        mass=3.0,
        size=(0.60, 0.40, 0.02),
        mesh_path="assets/parts/cooling_plate.usd",
        properties={
            "type": "liquid_cooled",
            "flow_rate": "10L/min",
            "pressure_drop": "<50kPa"
        },
        description="液冷板"
    ),
    
    "hv_connector": BatteryItem(
        item_id="hv_connector",
        item_type=BatteryItemType.COMPONENT,
        mass=0.5,
        size=(0.10, 0.08, 0.05),
        mesh_path="assets/parts/hv_connector.usd",
        properties={
            "rating": "1000V DC",
            "current": "200A"
        },
        description="高压连接器"
    ),
    
    "pack_enclosure": BatteryItem(
        item_id="pack_enclosure",
        item_type=BatteryItemType.COMPONENT,
        mass=15.0,
        size=(1.20, 0.80, 0.30),
        mesh_path="assets/parts/pack_enclosure.usd",
        properties={
            "rating": "IP67",
            "material": "steel"
        },
        description="电池包外壳"
    ),
    
    "main_bms": BatteryItem(
        item_id="main_bms",
        item_type=BatteryItemType.COMPONENT,
        mass=1.0,
        size=(0.30, 0.20, 0.05),
        mesh_path="assets/parts/main_bms.usd",
        properties={
            "type": "master",
            "protocol": "CAN"
        },
        description="BMS主控板"
    ),
    
    "battery_pack": BatteryItem(
        item_id="battery_pack",
        item_type=BatteryItemType.INTERMEDIATE,
        mass=120.0,
        size=(1.20, 0.80, 0.35),
        mesh_path="assets/parts/battery_pack.usd",
        properties={
            "voltage": "51.2V",
            "capacity": "14.3kWh"
        },
        description="电池包"
    ),
    
    # ========================================================================
    # 组件 - 系统级
    # ========================================================================
    
    "pcs_unit": BatteryItem(
        item_id="pcs_unit",
        item_type=BatteryItemType.COMPONENT,
        mass=50.0,
        size=(0.80, 0.60, 0.40),
        mesh_path="assets/parts/pcs_unit.usd",
        properties={
            "power": "50kW",
            "type": "bidirectional",
            "efficiency": "97%"
        },
        description="PCS功率转换系统"
    ),
    
    "inverter_module": BatteryItem(
        item_id="inverter_module",
        item_type=BatteryItemType.COMPONENT,
        mass=10.0,
        size=(0.40, 0.30, 0.15),
        mesh_path="assets/parts/inverter_module.usd",
        properties={
            "power": "25kW",
            "type": "DC-AC"
        },
        description="逆变器模块"
    ),
    
    "dc_dc_converter": BatteryItem(
        item_id="dc_dc_converter",
        item_type=BatteryItemType.COMPONENT,
        mass=5.0,
        size=(0.30, 0.20, 0.10),
        mesh_path="assets/parts/dc_dc_converter.usd",
        properties={
            "power": "10kW",
            "type": "bidirectional"
        },
        description="DC-DC转换器"
    ),
    
    "control_board": BatteryItem(
        item_id="control_board",
        item_type=BatteryItemType.COMPONENT,
        mass=0.5,
        size=(0.20, 0.15, 0.03),
        mesh_path="assets/parts/control_board.usd",
        properties={
            "type": "main_controller",
            "mcu": "ARM"
        },
        description="控制板"
    ),
    
    "heat_sink": BatteryItem(
        item_id="heat_sink",
        item_type=BatteryItemType.COMPONENT,
        mass=3.0,
        size=(0.40, 0.30, 0.05),
        mesh_path="assets/parts/heat_sink.usd",
        properties={
            "type": "aluminum",
            "thermal_resistance": "0.5°C/W"
        },
        description="散热器"
    ),
    
    "master_bms": BatteryItem(
        item_id="master_bms",
        item_type=BatteryItemType.COMPONENT,
        mass=2.0,
        size=(0.40, 0.30, 0.10),
        mesh_path="assets/parts/master_bms.usd",
        properties={
            "type": "system_master",
            "protocol": "Modbus"
        },
        description="系统级BMS主控"
    ),
    
    "fire_suppression": BatteryItem(
        item_id="fire_suppression",
        item_type=BatteryItemType.COMPONENT,
        mass=20.0,
        size=(0.50, 0.30, 0.30),
        mesh_path="assets/parts/fire_suppression.usd",
        properties={
            "agent": "FM200",
            "type": "automatic"
        },
        description="消防系统"
    ),
    
    "thermal_system": BatteryItem(
        item_id="thermal_system",
        item_type=BatteryItemType.COMPONENT,
        mass=15.0,
        size=(0.60, 0.40, 0.30),
        mesh_path="assets/parts/thermal_system.usd",
        properties={
            "type": "liquid_cooled",
            "cooling_capacity": "10kW"
        },
        description="热管理系统"
    ),
    
    "container": BatteryItem(
        item_id="container",
        item_type=BatteryItemType.COMPONENT,
        mass=500.0,
        size=(3.00, 2.50, 2.50),
        mesh_path="assets/parts/container.usd",
        properties={
            "type": "20ft",
            "rating": "IP55"
        },
        description="储能集装箱"
    ),
    
    "transformer": BatteryItem(
        item_id="transformer",
        item_type=BatteryItemType.COMPONENT,
        mass=200.0,
        size=(1.50, 1.00, 1.50),
        mesh_path="assets/parts/transformer.usd",
        properties={
            "power": "1MVA",
            "voltage": "35kV/380V"
        },
        description="变压器"
    ),
    
    "grid_controller": BatteryItem(
        item_id="grid_controller",
        item_type=BatteryItemType.COMPONENT,
        mass=5.0,
        size=(0.50, 0.40, 0.20),
        mesh_path="assets/parts/grid_controller.usd",
        properties={
            "type": "grid_tie",
            "protocol": "IEC61850"
        },
        description="电网控制器"
    ),
    
    "hvac_system": BatteryItem(
        item_id="hvac_system",
        item_type=BatteryItemType.COMPONENT,
        mass=100.0,
        size=(1.50, 1.00, 0.80),
        mesh_path="assets/parts/hvac_system.usd",
        properties={
            "cooling_capacity": "50kW",
            "type": "precision"
        },
        description="精密空调系统"
    ),
    
    # ========================================================================
    # 最终产品
    # ========================================================================
    
    "energy_storage_system": BatteryItem(
        item_id="energy_storage_system",
        item_type=BatteryItemType.FINAL_PRODUCT,
        mass=800.0,
        size=(3.00, 2.50, 2.50),
        mesh_path="assets/parts/energy_storage_system.usd",
        properties={
            "power": "50kW",
            "capacity": "57.2kWh",
            "type": "ESS"
        },
        description="储能系统"
    ),
    
    "megawatt_ess": BatteryItem(
        item_id="megawatt_ess",
        item_type=BatteryItemType.FINAL_PRODUCT,
        mass=8000.0,
        size=(12.00, 2.50, 2.50),
        mesh_path="assets/parts/megawatt_ess.usd",
        properties={
            "power": "1MW",
            "capacity": "2MWh",
            "type": "grid_scale"
        },
        description="兆瓦级储能系统"
    ),
    
    # ========================================================================
    # 其他辅料
    # ========================================================================
    
    "pcb": BatteryItem(
        item_id="pcb",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=0.1,
        size=(0.15, 0.10, 0.002),
        mesh_path="assets/parts/pcb.usd",
        properties={
            "type": "FR4",
            "layers": 4
        },
        description="印刷电路板"
    ),
    
    "ic_chips": BatteryItem(
        item_id="ic_chips",
        item_type=BatteryItemType.COMPONENT,
        mass=0.01,
        size=(0.01, 0.01, 0.002),
        mesh_path="assets/parts/ic_chips.usd",
        properties={
            "type": "analog_front_end",
            "package": "QFN"
        },
        description="IC芯片"
    ),
    
    "connector": BatteryItem(
        item_id="connector",
        item_type=BatteryItemType.COMPONENT,
        mass=0.05,
        size=(0.03, 0.02, 0.01),
        mesh_path="assets/parts/connector.usd",
        properties={
            "type": "wire_to_board",
            "pins": 4
        },
        description="连接器"
    ),
    
    "silicone": BatteryItem(
        item_id="silicone",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.10, 0.08, 0.05),
        mesh_path="assets/parts/silicone.usd",
        properties={
            "type": "silicone_rubber",
            "form": "gel"
        },
        description="硅胶，用于导热垫"
    ),
    
    "ceramic_powder": BatteryItem(
        item_id="ceramic_powder",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.08, 0.08, 0.05),
        mesh_path="assets/parts/ceramic_powder.usd",
        properties={
            "type": "Al2O3",
            "particle_size": "5μm"
        },
        description="陶瓷粉末"
    ),
    
    "aluminum_plate": BatteryItem(
        item_id="aluminum_plate",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=2.0,
        size=(0.60, 0.40, 0.003),
        mesh_path="assets/parts/aluminum_plate.usd",
        properties={
            "type": "aluminum",
            "thickness": "3mm"
        },
        description="铝板，用于液冷板"
    ),
    
    "copper_tube": BatteryItem(
        item_id="copper_tube",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.50, 0.01, 0.01),
        mesh_path="assets/parts/copper_tube.usd",
        properties={
            "type": "copper",
            "diameter": "8mm"
        },
        description="铜管，用于液冷板"
    ),
    
    "pe_pellet": BatteryItem(
        item_id="pe_pellet",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.05, 0.05, 0.05),
        mesh_path="assets/parts/pe_pellet.usd",
        properties={
            "type": "polyethylene",
            "grade": "battery"
        },
        description="PE颗粒，用于隔膜"
    ),
    
    "pp_pellet": BatteryItem(
        item_id="pp_pellet",
        item_type=BatteryItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.05, 0.05, 0.05),
        mesh_path="assets/parts/pp_pellet.usd",
        properties={
            "type": "polypropylene",
            "grade": "battery"
        },
        description="PP颗粒，用于隔膜"
    ),
}


# ============================================================================
# 工具函数
# ============================================================================

def get_battery_item(item_id: str) -> Optional[BatteryItem]:
    """获取电池物品"""
    return BATTERY_ITEM_REGISTRY.get(item_id)


def get_battery_items_by_type(item_type: BatteryItemType) -> List[BatteryItem]:
    """获取指定类型的所有物品"""
    return [item for item in BATTERY_ITEM_REGISTRY.values() if item.item_type == item_type]


def get_all_battery_item_ids() -> List[str]:
    """获取所有物品ID"""
    return list(BATTERY_ITEM_REGISTRY.keys())


def battery_item_exists(item_id: str) -> bool:
    """检查物品是否存在"""
    return item_id in BATTERY_ITEM_REGISTRY


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("储能电池制造物品注册表")
    print("=" * 60)
    
    print(f"\n总物品数: {len(BATTERY_ITEM_REGISTRY)}")
    
    print("\n按类型统计:")
    for item_type in BatteryItemType:
        items = get_battery_items_by_type(item_type)
        print(f"  {item_type.value}: {len(items)}")
    
    print("\n物品列表:")
    for item_id, item in BATTERY_ITEM_REGISTRY.items():
        print(f"  {item_id}: {item.mass}kg, {item.description}")
