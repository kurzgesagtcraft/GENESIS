"""
光伏制造物品定义

定义光伏组件制造全产业链所需的所有物品类型。
包括: 原材料、中间产品、辅料、最终产品等。

文件: src/world/solar_items.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class SolarItemType(Enum):
    """光伏物品类型"""
    RAW_MATERIAL = "raw_material"       # 原材料
    INTERMEDIATE = "intermediate"       # 中间产品
    CONSUMABLE = "consumable"           # 消耗品
    COMPONENT = "component"             # 组件
    FINAL_PRODUCT = "final_product"     # 最终产品


@dataclass
class SolarItem:
    """
    光伏制造物品定义
    
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
    item_type: SolarItemType
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
# 光伏物品注册表
# ============================================================================

SOLAR_ITEM_REGISTRY: Dict[str, SolarItem] = {
    
    # ========================================================================
    # 原材料
    # ========================================================================
    
    "silicon_ore": SolarItem(
        item_id="silicon_ore",
        item_type=SolarItemType.RAW_MATERIAL,
        mass=2.5,
        size=(0.12, 0.12, 0.10),
        mesh_path="assets/parts/silicon_ore.usd",
        properties={
            "purity": "low",
            "color": "gray",
            "si_content": "20-30%"
        },
        description="硅矿石，用于提纯生产多晶硅"
    ),
    
    "quartz_sand": SolarItem(
        item_id="quartz_sand",
        item_type=SolarItemType.RAW_MATERIAL,
        mass=1.5,
        size=(0.10, 0.10, 0.08),
        mesh_path="assets/parts/quartz_sand.usd",
        properties={
            "type": "high_purity",
            "sio2_content": ">99%"
        },
        description="高纯石英砂，用于制造玻璃和坩埚"
    ),
    
    "aluminum_bar": SolarItem(
        item_id="aluminum_bar",
        item_type=SolarItemType.RAW_MATERIAL,
        mass=2.0,
        size=(0.30, 0.05, 0.05),
        mesh_path="assets/parts/aluminum_bar.usd",
        properties={
            "type": "alloy",
            "grade": "6063"
        },
        description="铝型材，用于制造边框"
    ),
    
    "copper_wire": SolarItem(
        item_id="copper_wire",
        item_type=SolarItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.05, 0.05, 0.02),
        mesh_path="assets/parts/copper_wire.usd",
        properties={
            "type": "tinned",
            "diameter": "4mm²"
        },
        description="镀锡铜线，用于组件接线"
    ),
    
    # ========================================================================
    # 中间产品 - 硅料
    # ========================================================================
    
    "polysilicon": SolarItem(
        item_id="polysilicon",
        item_type=SolarItemType.INTERMEDIATE,
        mass=3.0,
        size=(0.15, 0.15, 0.15),
        mesh_path="assets/parts/polysilicon.usd",
        properties={
            "purity": "99.9999%",
            "form": "chunk",
            "grade": "solar_grade"
        },
        description="多晶硅料，用于拉制单晶硅棒"
    ),
    
    "seed_crystal": SolarItem(
        item_id="seed_crystal",
        item_type=SolarItemType.CONSUMABLE,
        mass=0.1,
        size=(0.05, 0.05, 0.20),
        mesh_path="assets/parts/seed_crystal.usd",
        properties={
            "orientation": "<100>",
            "type": "monocrystalline"
        },
        description="籽晶，用于单晶拉制的晶种"
    ),
    
    # ========================================================================
    # 中间产品 - 晶体
    # ========================================================================
    
    "silicon_ingot": SolarItem(
        item_id="silicon_ingot",
        item_type=SolarItemType.INTERMEDIATE,
        mass=15.0,
        size=(0.20, 0.20, 1.50),
        mesh_path="assets/parts/silicon_ingot.usd",
        properties={
            "diameter": "200mm",
            "type": "monocrystalline",
            "length": "1.5m"
        },
        description="单晶硅棒，用于切割硅片"
    ),
    
    "silicon_scrap": SolarItem(
        item_id="silicon_scrap",
        item_type=SolarItemType.RAW_MATERIAL,
        mass=2.0,
        size=(0.15, 0.15, 0.10),
        mesh_path="assets/parts/silicon_scrap.usd",
        properties={
            "type": "recyclable",
            "purity": "high"
        },
        description="硅料废料，可回收利用"
    ),
    
    "silicon_kerf": SolarItem(
        item_id="silicon_kerf",
        item_type=SolarItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.10, 0.10, 0.05),
        mesh_path="assets/parts/silicon_kerf.usd",
        properties={
            "type": "cutting_waste",
            "form": "powder"
        },
        description="切割硅粉，切割过程中的损耗"
    ),
    
    # ========================================================================
    # 中间产品 - 硅片
    # ========================================================================
    
    "silicon_wafer": SolarItem(
        item_id="silicon_wafer",
        item_type=SolarItemType.INTERMEDIATE,
        mass=0.01,
        size=(0.21, 0.21, 0.00018),
        mesh_path="assets/parts/silicon_wafer.usd",
        properties={
            "thickness": "180μm",
            "size": "210mm",
            "type": "as_cut"
        },
        description="切割后的硅片"
    ),
    
    "polished_wafer": SolarItem(
        item_id="polished_wafer",
        item_type=SolarItemType.INTERMEDIATE,
        mass=0.009,
        size=(0.21, 0.21, 0.00016),
        mesh_path="assets/parts/polished_wafer.usd",
        properties={
            "thickness": "160μm",
            "surface": "mirror",
            "roughness": "<1nm"
        },
        description="抛光硅片"
    ),
    
    "textured_wafer": SolarItem(
        item_id="textured_wafer",
        item_type=SolarItemType.INTERMEDIATE,
        mass=0.009,
        size=(0.21, 0.21, 0.00016),
        mesh_path="assets/parts/textured_wafer.usd",
        properties={
            "surface": "textured",
            "reflection": "<5%",
            "method": "alkali_etching"
        },
        description="制绒硅片，降低反射率"
    ),
    
    # ========================================================================
    # 中间产品 - 电池片
    # ========================================================================
    
    "solar_cell": SolarItem(
        item_id="solar_cell",
        item_type=SolarItemType.INTERMEDIATE,
        mass=0.012,
        size=(0.21, 0.21, 0.00018),
        mesh_path="assets/parts/solar_cell.usd",
        properties={
            "efficiency": "23%",
            "busbar": "9BB",
            "type": "PERC"
        },
        description="太阳能电池片"
    ),
    
    # ========================================================================
    # 辅料 - 浆料
    # ========================================================================
    
    "silver_paste": SolarItem(
        item_id="silver_paste",
        item_type=SolarItemType.CONSUMABLE,
        mass=0.5,
        size=(0.08, 0.08, 0.05),
        mesh_path="assets/parts/silver_paste.usd",
        properties={
            "type": "front_side",
            "solid_content": "85%"
        },
        description="正面银浆，用于印刷电极"
    ),
    
    "aluminum_paste": SolarItem(
        item_id="aluminum_paste",
        item_type=SolarItemType.CONSUMABLE,
        mass=0.5,
        size=(0.08, 0.08, 0.05),
        mesh_path="assets/parts/aluminum_paste.usd",
        properties={
            "type": "back_side",
            "solid_content": "75%"
        },
        description="背面铝浆，用于背电场"
    ),
    
    # ========================================================================
    # 辅料 - 封装材料
    # ========================================================================
    
    "glass_sheet": SolarItem(
        item_id="glass_sheet",
        item_type=SolarItemType.INTERMEDIATE,
        mass=15.0,
        size=(2.30, 1.10, 0.0032),
        mesh_path="assets/parts/glass_sheet.usd",
        properties={
            "thickness": "3.2mm",
            "type": "tempered",
            "transmission": ">91%"
        },
        description="光伏玻璃"
    ),
    
    "eva_film": SolarItem(
        item_id="eva_film",
        item_type=SolarItemType.CONSUMABLE,
        mass=2.0,
        size=(2.30, 1.10, 0.0005),
        mesh_path="assets/parts/eva_film.usd",
        properties={
            "thickness": "0.5mm",
            "transmission": ">90%"
        },
        description="EVA胶膜，用于封装"
    ),
    
    # ========================================================================
    # 辅料 - 边框和接线盒
    # ========================================================================
    
    "aluminum_frame": SolarItem(
        item_id="aluminum_frame",
        item_type=SolarItemType.COMPONENT,
        mass=5.0,
        size=(2.30, 1.10, 0.04),
        mesh_path="assets/parts/aluminum_frame.usd",
        properties={
            "type": "anodized",
            "thickness": "1.5mm"
        },
        description="铝边框"
    ),
    
    "junction_box": SolarItem(
        item_id="junction_box",
        item_type=SolarItemType.COMPONENT,
        mass=0.5,
        size=(0.15, 0.10, 0.05),
        mesh_path="assets/parts/junction_box.usd",
        properties={
            "rating": "IP65",
            "current": "30A",
            "diodes": 3
        },
        description="接线盒"
    ),
    
    # ========================================================================
    # 最终产品
    # ========================================================================
    
    "solar_panel": SolarItem(
        item_id="solar_panel",
        item_type=SolarItemType.FINAL_PRODUCT,
        mass=28.0,
        size=(2.30, 1.10, 0.04),
        mesh_path="assets/parts/solar_panel.usd",
        properties={
            "power": "550W",
            "efficiency": "21%",
            "cells": 72,
            "voltage": "41.5V",
            "current": "13.26A"
        },
        description="光伏组件"
    ),
    
    "solar_array_module": SolarItem(
        item_id="solar_array_module",
        item_type=SolarItemType.FINAL_PRODUCT,
        mass=150.0,
        size=(5.0, 3.0, 0.5),
        mesh_path="assets/parts/solar_array_module.usd",
        properties={
            "panels": 5,
            "total_power": "2750W",
            "voltage": "300V"
        },
        description="光伏阵列模块"
    ),
    
    # ========================================================================
    # 其他辅料
    # ========================================================================
    
    "plastic": SolarItem(
        item_id="plastic",
        item_type=SolarItemType.RAW_MATERIAL,
        mass=0.5,
        size=(0.10, 0.10, 0.05),
        mesh_path="assets/parts/plastic.usd",
        properties={
            "type": "ABS",
            "form": "pellet"
        },
        description="塑料原料"
    ),
    
    "diode": SolarItem(
        item_id="diode",
        item_type=SolarItemType.COMPONENT,
        mass=0.01,
        size=(0.02, 0.02, 0.01),
        mesh_path="assets/parts/diode.usd",
        properties={
            "type": "bypass",
            "rating": "15A"
        },
        description="旁路二极管"
    ),
    
    "carbon_source": SolarItem(
        item_id="carbon_source",
        item_type=SolarItemType.CONSUMABLE,
        mass=0.5,
        size=(0.08, 0.08, 0.05),
        mesh_path="assets/parts/carbon_source.usd",
        properties={
            "type": "graphite_powder",
            "purity": ">99%"
        },
        description="碳源，用于LFP合成"
    ),
    
    "dopant": SolarItem(
        item_id="dopant",
        item_type=SolarItemType.CONSUMABLE,
        mass=0.1,
        size=(0.05, 0.05, 0.03),
        mesh_path="assets/parts/dopant.usd",
        properties={
            "type": "phosphorus",
            "form": "powder"
        },
        description="掺杂剂，用于电池片制造"
    ),
    
    "ito_target": SolarItem(
        item_id="ito_target",
        item_type=SolarItemType.CONSUMABLE,
        mass=0.5,
        size=(0.10, 0.05, 0.02),
        mesh_path="assets/parts/ito_target.usd",
        properties={
            "type": "ITO",
            "purity": "99.99%"
        },
        description="ITO靶材，用于HJT电池"
    ),
    
    "intrinsic_si": SolarItem(
        item_id="intrinsic_si",
        item_type=SolarItemType.CONSUMABLE,
        mass=0.2,
        size=(0.08, 0.08, 0.03),
        mesh_path="assets/parts/intrinsic_si.usd",
        properties={
            "type": "intrinsic_silicon",
            "purity": "99.999%"
        },
        description="本征硅，用于HJT电池"
    ),
    
    "mask_material": SolarItem(
        item_id="mask_material",
        item_type=SolarItemType.CONSUMABLE,
        mass=0.1,
        size=(0.08, 0.08, 0.02),
        mesh_path="assets/parts/mask_material.usd",
        properties={
            "type": "photoresist"
        },
        description="掩膜材料，用于BC电池"
    ),
    
    "mounting_rail": SolarItem(
        item_id="mounting_rail",
        item_type=SolarItemType.COMPONENT,
        mass=2.0,
        size=(2.0, 0.05, 0.05),
        mesh_path="assets/parts/mounting_rail.usd",
        properties={
            "type": "aluminum",
            "length": "2m"
        },
        description="安装导轨"
    ),
    
    "connector": SolarItem(
        item_id="connector",
        item_type=SolarItemType.COMPONENT,
        mass=0.1,
        size=(0.05, 0.03, 0.02),
        mesh_path="assets/parts/connector.usd",
        properties={
            "type": "MC4",
            "rating": "30A"
        },
        description="光伏连接器"
    ),
    
    "cable": SolarItem(
        item_id="cable",
        item_type=SolarItemType.RAW_MATERIAL,
        mass=0.3,
        size=(1.0, 0.01, 0.01),
        mesh_path="assets/parts/cable.usd",
        properties={
            "type": "PV_cable",
            "size": "4mm²"
        },
        description="光伏电缆"
    ),
}


# ============================================================================
# 工具函数
# ============================================================================

def get_solar_item(item_id: str) -> Optional[SolarItem]:
    """获取光伏物品"""
    return SOLAR_ITEM_REGISTRY.get(item_id)


def get_solar_items_by_type(item_type: SolarItemType) -> List[SolarItem]:
    """获取指定类型的所有物品"""
    return [item for item in SOLAR_ITEM_REGISTRY.values() if item.item_type == item_type]


def get_all_solar_item_ids() -> List[str]:
    """获取所有物品ID"""
    return list(SOLAR_ITEM_REGISTRY.keys())


def solar_item_exists(item_id: str) -> bool:
    """检查物品是否存在"""
    return item_id in SOLAR_ITEM_REGISTRY


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("光伏制造物品注册表")
    print("=" * 60)
    
    print(f"\n总物品数: {len(SOLAR_ITEM_REGISTRY)}")
    
    print("\n按类型统计:")
    for item_type in SolarItemType:
        items = get_solar_items_by_type(item_type)
        print(f"  {item_type.value}: {len(items)}")
    
    print("\n物品列表:")
    for item_id, item in SOLAR_ITEM_REGISTRY.items():
        print(f"  {item_id}: {item.mass}kg, {item.description}")
