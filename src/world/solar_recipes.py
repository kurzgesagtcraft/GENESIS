"""
光伏制造配方系统

实现从硅料到完整光伏组件的全产业链制造配方。
包括: 硅料提纯、晶体生长、硅片切割、电池片制造、组件封装等工序。

文件: src/world/solar_recipes.py
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class SolarRecipeType(Enum):
    """光伏配方类型"""
    # 上游原材料加工
    SILICON_PURIFICATION = "silicon_purification"
    # 晶体生长
    CRYSTAL_GROWTH = "crystal_growth"
    # 硅片制造
    WAFER_MANUFACTURING = "wafer_manufacturing"
    # 电池片制造
    CELL_MANUFACTURING = "cell_manufacturing"
    # 组件封装
    PANEL_ASSEMBLY = "panel_assembly"
    # 辅料制造
    AUXILIARY = "auxiliary"


@dataclass
class SolarRecipe:
    """
    光伏制造配方
    
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
    recipe_type: SolarRecipeType = SolarRecipeType.AUXILIARY
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
# 光伏制造配方定义
# ============================================================================

SOLAR_RECIPES: List[SolarRecipe] = [
    
    # ========================================================================
    # 上游: 原材料加工
    # ========================================================================
    
    SolarRecipe(
        name="purify_silicon",
        station_type="silicon_purifier",
        inputs={"silicon_ore": 5, "quartz_sand": 1},
        outputs={"polysilicon": 2},
        process_time=120.0,
        energy_cost=2000.0,
        quality_params={
            "purity": "99.9999%",
            "grade": "solar_grade",
            "form": "chunk"
        },
        recipe_type=SolarRecipeType.SILICON_PURIFICATION,
        description="硅矿提纯为多晶硅料，采用改进西门子法"
    ),
    
    SolarRecipe(
        name="purify_silicon_high_grade",
        station_type="silicon_purifier",
        inputs={"silicon_ore": 8, "quartz_sand": 2, "chemical_agent": 1},
        outputs={"polysilicon": 4},
        process_time=180.0,
        energy_cost=3500.0,
        quality_params={
            "purity": "99.99999%",
            "grade": "electronic_grade",
            "form": "chunk"
        },
        recipe_type=SolarRecipeType.SILICON_PURIFICATION,
        description="高纯度电子级多晶硅料生产"
    ),
    
    # ========================================================================
    # 中游: 晶体生长
    # ========================================================================
    
    SolarRecipe(
        name="grow_single_crystal",
        station_type="crystal_grower",
        inputs={"polysilicon": 3, "seed_crystal": 1},
        outputs={"silicon_ingot": 1},
        process_time=300.0,
        energy_cost=5000.0,
        quality_params={
            "diameter": "200mm",
            "type": "monocrystalline",
            "length": "1.5m",
            "method": "CZ"
        },
        recipe_type=SolarRecipeType.CRYSTAL_GROWTH,
        description="直拉法(CZ)生长单晶硅棒"
    ),
    
    SolarRecipe(
        name="grow_single_crystal_large",
        station_type="crystal_grower",
        inputs={"polysilicon": 5, "seed_crystal": 1},
        outputs={"silicon_ingot": 1, "silicon_scrap": 1},
        process_time=400.0,
        energy_cost=7000.0,
        quality_params={
            "diameter": "300mm",
            "type": "monocrystalline",
            "length": "2.0m",
            "method": "CZ"
        },
        recipe_type=SolarRecipeType.CRYSTAL_GROWTH,
        description="大尺寸单晶硅棒生长(12英寸)"
    ),
    
    SolarRecipe(
        name="grow_multicrystal",
        station_type="crystal_grower",
        inputs={"polysilicon": 4},
        outputs={"silicon_ingot": 1, "silicon_scrap": 1},
        process_time=240.0,
        energy_cost=4000.0,
        quality_params={
            "type": "multicrystalline",
            "size": "large",
            "method": "directional_solidification"
        },
        recipe_type=SolarRecipeType.CRYSTAL_GROWTH,
        description="定向凝固法生产多晶硅锭"
    ),
    
    # ========================================================================
    # 中游: 硅片制造
    # ========================================================================
    
    SolarRecipe(
        name="slice_wafer",
        station_type="wafer_slicer",
        inputs={"silicon_ingot": 1},
        outputs={"silicon_wafer": 50, "silicon_kerf": 1},
        process_time=180.0,
        energy_cost=800.0,
        quality_params={
            "thickness": "180μm",
            "size": "210mm",
            "type": "as_cut",
            "method": "multi_wire_sawing"
        },
        recipe_type=SolarRecipeType.WAFER_MANUFACTURING,
        description="多线切割硅棒为硅片，每根晶棒切50片"
    ),
    
    SolarRecipe(
        name="slice_wafer_thin",
        station_type="wafer_slicer",
        inputs={"silicon_ingot": 1},
        outputs={"silicon_wafer": 60, "silicon_kerf": 1},
        process_time=200.0,
        energy_cost=900.0,
        quality_params={
            "thickness": "150μm",
            "size": "210mm",
            "type": "as_cut",
            "method": "diamond_wire_sawing"
        },
        recipe_type=SolarRecipeType.WAFER_MANUFACTURING,
        description="金刚线切割薄片硅片"
    ),
    
    SolarRecipe(
        name="polish_wafer",
        station_type="wafer_slicer",
        inputs={"silicon_wafer": 10},
        outputs={"polished_wafer": 10},
        process_time=60.0,
        energy_cost=200.0,
        quality_params={
            "surface_roughness": "<1nm",
            "type": "polished",
            "thickness": "160μm"
        },
        recipe_type=SolarRecipeType.WAFER_MANUFACTURING,
        description="硅片表面抛光处理"
    ),
    
    SolarRecipe(
        name="texture_wafer",
        station_type="wafer_slicer",
        inputs={"silicon_wafer": 10},
        outputs={"textured_wafer": 10},
        process_time=45.0,
        energy_cost=150.0,
        quality_params={
            "surface": "textured",
            "reflection": "<5%",
            "method": "alkali_etching"
        },
        recipe_type=SolarRecipeType.WAFER_MANUFACTURING,
        description="硅片制绒处理，降低反射率"
    ),
    
    # ========================================================================
    # 中游: 电池片制造
    # ========================================================================
    
    SolarRecipe(
        name="make_solar_cell_perc",
        station_type="solar_cell_fab",
        inputs={
            "silicon_wafer": 1,
            "silver_paste": 1,
            "aluminum_paste": 1
        },
        outputs={"solar_cell": 1},
        process_time=240.0,
        energy_cost=1500.0,
        quality_params={
            "efficiency": "23%",
            "type": "PERC",
            "busbar": "9BB",
            "voc": "685mV"
        },
        recipe_type=SolarRecipeType.CELL_MANUFACTURING,
        description="PERC电池片制造"
    ),
    
    SolarRecipe(
        name="make_solar_cell_topcon",
        station_type="solar_cell_fab",
        inputs={
            "polished_wafer": 1,
            "silver_paste": 1,
            "aluminum_paste": 1,
            "dopant": 1
        },
        outputs={"solar_cell": 1},
        process_time=300.0,
        energy_cost=2000.0,
        quality_params={
            "efficiency": "25%",
            "type": "TOPCon",
            "busbar": "16BB",
            "voc": "710mV"
        },
        recipe_type=SolarRecipeType.CELL_MANUFACTURING,
        description="TOPCon高效电池片制造"
    ),
    
    SolarRecipe(
        name="make_solar_cell_hjt",
        station_type="solar_cell_fab",
        inputs={
            "textured_wafer": 1,
            "silver_paste": 1,
            "ito_target": 1,
            "intrinsic_si": 1
        },
        outputs={"solar_cell": 1},
        process_time=350.0,
        energy_cost=2500.0,
        quality_params={
            "efficiency": "26%",
            "type": "HJT",
            "busbar": "无主栅",
            "voc": "740mV"
        },
        recipe_type=SolarRecipeType.CELL_MANUFACTURING,
        description="异质结(HJT)电池片制造"
    ),
    
    SolarRecipe(
        name="make_solar_cell_bc",
        station_type="solar_cell_fab",
        inputs={
            "polished_wafer": 1,
            "silver_paste": 2,
            "aluminum_paste": 1,
            "mask_material": 1
        },
        outputs={"solar_cell": 1},
        process_time=320.0,
        energy_cost=2200.0,
        quality_params={
            "efficiency": "25.5%",
            "type": "BC",
            "busbar": "无主栅",
            "voc": "720mV"
        },
        recipe_type=SolarRecipeType.CELL_MANUFACTURING,
        description="背接触(BC)电池片制造"
    ),
    
    # ========================================================================
    # 下游: 组件封装
    # ========================================================================
    
    SolarRecipe(
        name="assemble_panel_72cell",
        station_type="panel_assembler",
        inputs={
            "solar_cell": 72,
            "glass_sheet": 2,
            "eva_film": 2,
            "aluminum_frame": 1,
            "junction_box": 1,
            "copper_wire": 5
        },
        outputs={"solar_panel": 1},
        process_time=360.0,
        energy_cost=1200.0,
        quality_params={
            "power": "550W",
            "cells": "72",
            "size": "2.3m×1.1m",
            "efficiency": "21%"
        },
        recipe_type=SolarRecipeType.PANEL_ASSEMBLY,
        description="72片电池组件封装"
    ),
    
    SolarRecipe(
        name="assemble_panel_60cell",
        station_type="panel_assembler",
        inputs={
            "solar_cell": 60,
            "glass_sheet": 2,
            "eva_film": 2,
            "aluminum_frame": 1,
            "junction_box": 1,
            "copper_wire": 4
        },
        outputs={"solar_panel": 1},
        process_time=300.0,
        energy_cost=1000.0,
        quality_params={
            "power": "450W",
            "cells": "60",
            "size": "2.0m×1.0m",
            "efficiency": "21%"
        },
        recipe_type=SolarRecipeType.PANEL_ASSEMBLY,
        description="60片电池组件封装"
    ),
    
    SolarRecipe(
        name="assemble_panel_54cell",
        station_type="panel_assembler",
        inputs={
            "solar_cell": 54,
            "glass_sheet": 2,
            "eva_film": 2,
            "aluminum_frame": 1,
            "junction_box": 1,
            "copper_wire": 3
        },
        outputs={"solar_panel": 1},
        process_time=270.0,
        energy_cost=900.0,
        quality_params={
            "power": "400W",
            "cells": "54",
            "size": "1.8m×1.0m",
            "efficiency": "21%"
        },
        recipe_type=SolarRecipeType.PANEL_ASSEMBLY,
        description="54片电池组件封装(户用)"
    ),
    
    SolarRecipe(
        name="assemble_bifacial_panel",
        station_type="panel_assembler",
        inputs={
            "solar_cell": 72,
            "glass_sheet": 2,
            "eva_film": 2,
            "aluminum_frame": 1,
            "junction_box": 1,
            "copper_wire": 5
        },
        outputs={"solar_panel": 1},
        process_time=380.0,
        energy_cost=1300.0,
        quality_params={
            "power": "580W",
            "cells": "72",
            "type": "bifacial",
            "bifaciality": "70%"
        },
        recipe_type=SolarRecipeType.PANEL_ASSEMBLY,
        description="双面发电组件封装"
    ),
    
    # ========================================================================
    # 辅料制造
    # ========================================================================
    
    SolarRecipe(
        name="make_glass_sheet",
        station_type="fabricator",
        inputs={"quartz_sand": 2},
        outputs={"glass_sheet": 1},
        process_time=90.0,
        energy_cost=600.0,
        quality_params={
            "thickness": "3.2mm",
            "transmission": ">91%",
            "type": "tempered"
        },
        recipe_type=SolarRecipeType.AUXILIARY,
        description="光伏玻璃制造"
    ),
    
    SolarRecipe(
        name="make_glass_sheet_thin",
        station_type="fabricator",
        inputs={"quartz_sand": 1.5},
        outputs={"glass_sheet": 1},
        process_time=80.0,
        energy_cost=500.0,
        quality_params={
            "thickness": "2.0mm",
            "transmission": ">93%",
            "type": "tempered"
        },
        recipe_type=SolarRecipeType.AUXILIARY,
        description="薄玻璃制造(双玻组件用)"
    ),
    
    SolarRecipe(
        name="make_aluminum_frame",
        station_type="fabricator",
        inputs={"aluminum_bar": 3},
        outputs={"aluminum_frame": 1},
        process_time=60.0,
        energy_cost=400.0,
        quality_params={
            "type": "anodized",
            "thickness": "1.5mm",
            "surface": "silver"
        },
        recipe_type=SolarRecipeType.AUXILIARY,
        description="铝边框制造"
    ),
    
    SolarRecipe(
        name="make_junction_box",
        station_type="fabricator",
        inputs={"plastic": 1, "copper_wire": 2, "diode": 3},
        outputs={"junction_box": 1},
        process_time=45.0,
        energy_cost=300.0,
        quality_params={
            "rating": "IP65",
            "current": "30A",
            "diodes": 3
        },
        recipe_type=SolarRecipeType.AUXILIARY,
        description="接线盒制造"
    ),
    
    SolarRecipe(
        name="make_seed_crystal",
        station_type="fabricator",
        inputs={"polysilicon": 1},
        outputs={"seed_crystal": 2},
        process_time=30.0,
        energy_cost=200.0,
        quality_params={
            "orientation": "<100>",
            "length": "200mm",
            "diameter": "10mm"
        },
        recipe_type=SolarRecipeType.AUXILIARY,
        description="籽晶制造"
    ),
    
    SolarRecipe(
        name="make_silver_paste",
        station_type="fabricator",
        inputs={"silver_powder": 1, "glass_frit": 1, "organic_carrier": 1},
        outputs={"silver_paste": 2},
        process_time=40.0,
        energy_cost=250.0,
        quality_params={
            "type": "front_side",
            "solid_content": "85%"
        },
        recipe_type=SolarRecipeType.AUXILIARY,
        description="银浆制造(正面电极)"
    ),
    
    SolarRecipe(
        name="make_aluminum_paste",
        station_type="fabricator",
        inputs={"aluminum_powder": 1, "glass_frit": 1, "organic_carrier": 1},
        outputs={"aluminum_paste": 2},
        process_time=40.0,
        energy_cost=200.0,
        quality_params={
            "type": "back_side",
            "solid_content": "75%"
        },
        recipe_type=SolarRecipeType.AUXILIARY,
        description="铝浆制造(背面电极)"
    ),
    
    SolarRecipe(
        name="make_eva_film",
        station_type="fabricator",
        inputs={"eva_resin": 1, "crosslinker": 1},
        outputs={"eva_film": 2},
        process_time=50.0,
        energy_cost=300.0,
        quality_params={
            "thickness": "0.5mm",
            "transmission": ">90%"
        },
        recipe_type=SolarRecipeType.AUXILIARY,
        description="EVA胶膜制造"
    ),
    
    # ========================================================================
    # 系统集成
    # ========================================================================
    
    SolarRecipe(
        name="assemble_solar_array",
        station_type="panel_assembler",
        inputs={
            "solar_panel": 5,
            "mounting_rail": 10,
            "connector": 5,
            "cable": 10
        },
        outputs={"solar_array_module": 1},
        process_time=180.0,
        energy_cost=500.0,
        quality_params={
            "panels": 5,
            "total_power": "2750W",
            "voltage": "300V"
        },
        recipe_type=SolarRecipeType.PANEL_ASSEMBLY,
        description="光伏阵列组装"
    ),
]


# ============================================================================
# 配方查询工具函数
# ============================================================================

def get_recipes_by_station(station_type: str) -> List[SolarRecipe]:
    """获取指定工站类型的所有配方"""
    return [r for r in SOLAR_RECIPES if r.station_type == station_type]


def get_recipes_by_type(recipe_type: SolarRecipeType) -> List[SolarRecipe]:
    """获取指定类型的所有配方"""
    return [r for r in SOLAR_RECIPES if r.recipe_type == recipe_type]


def get_recipe_by_name(name: str) -> Optional[SolarRecipe]:
    """根据名称获取配方"""
    for recipe in SOLAR_RECIPES:
        if recipe.name == name:
            return recipe
    return None


def get_recipe_for_output(output_type: str) -> List[SolarRecipe]:
    """获取能产出指定物品的所有配方"""
    return [r for r in SOLAR_RECIPES if output_type in r.outputs]


def get_recipe_for_input(input_type: str) -> List[SolarRecipe]:
    """获取需要指定物品作为输入的所有配方"""
    return [r for r in SOLAR_RECIPES if input_type in r.inputs]


# ============================================================================
# 配方依赖分析
# ============================================================================

def build_solar_recipe_dependency_graph():
    """
    构建光伏配方依赖图
    
    返回:
        Dict[str, List[str]]: 物品 -> 可由哪些配方产出
        Dict[str, List[str]]: 物品 -> 被哪些配方消耗
    """
    output_to_recipes: Dict[str, List[str]] = {}
    input_to_recipes: Dict[str, List[str]] = {}
    
    for recipe in SOLAR_RECIPES:
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


def print_solar_dependency_tree(target_item: str = "solar_panel", indent: int = 0):
    """
    打印光伏制造依赖树
    
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
        print_solar_dependency_tree(input_item, indent + 2)


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    # 打印配方统计
    print("=" * 60)
    print("光伏制造配方系统统计")
    print("=" * 60)
    
    print(f"\n总配方数: {len(SOLAR_RECIPES)}")
    
    # 按类型统计
    print("\n按配方类型统计:")
    for recipe_type in SolarRecipeType:
        count = len([r for r in SOLAR_RECIPES if r.recipe_type == recipe_type])
        print(f"  {recipe_type.value}: {count}")
    
    # 按工站统计
    print("\n按工站类型统计:")
    station_types = set(r.station_type for r in SOLAR_RECIPES)
    for station in sorted(station_types):
        count = len([r for r in SOLAR_RECIPES if r.station_type == station])
        print(f"  {station}: {count}")
    
    # 打印依赖树
    print("\n" + "=" * 60)
    print("光伏组件制造依赖树 (solar_panel)")
    print("=" * 60)
    print_solar_dependency_tree("solar_panel")
    
    # 计算原材料需求
    print("\n" + "=" * 60)
    print("制造1块550W光伏组件所需原材料")
    print("=" * 60)
    materials = calculate_material_requirement("solar_panel", 1)
    for item, qty in sorted(materials.items()):
        print(f"  {item}: {qty}")
