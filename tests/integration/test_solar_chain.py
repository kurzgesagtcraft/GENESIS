"""
光伏制造全链路集成测试

测试光伏组件制造从硅矿到最终产品的完整流程。

文件: tests/integration/test_solar_chain.py
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestSolarRecipeSystem:
    """光伏配方系统测试"""
    
    def test_solar_recipes_loaded(self):
        """测试光伏配方加载"""
        from src.world.solar_recipes import SOLAR_RECIPES, SolarRecipeType
        
        assert len(SOLAR_RECIPES) > 0, "光伏配方列表不应为空"
        
        # 检查配方类型分布
        recipe_types = set(r.recipe_type for r in SOLAR_RECIPES)
        assert SolarRecipeType.SILICON_PURIFICATION in recipe_types
        assert SolarRecipeType.CRYSTAL_GROWTH in recipe_types
        assert SolarRecipeType.WAFER_MANUFACTURING in recipe_types
        assert SolarRecipeType.CELL_MANUFACTURING in recipe_types
        assert SolarRecipeType.PANEL_ASSEMBLY in recipe_types
    
    def test_get_recipes_by_station(self):
        """测试按工站类型获取配方"""
        from src.world.solar_recipes import get_recipes_by_station
        
        # 硅料提纯站配方
        purifier_recipes = get_recipes_by_station("silicon_purifier")
        assert len(purifier_recipes) > 0
        assert all(r.station_type == "silicon_purifier" for r in purifier_recipes)
        
        # 晶体生长站配方
        grower_recipes = get_recipes_by_station("crystal_grower")
        assert len(grower_recipes) > 0
        
        # 硅片切割站配方
        slicer_recipes = get_recipes_by_station("wafer_slicer")
        assert len(slicer_recipes) > 0
        
        # 电池片制造站配方
        cell_recipes = get_recipes_by_station("solar_cell_fab")
        assert len(cell_recipes) > 0
        
        # 组件封装站配方
        panel_recipes = get_recipes_by_station("panel_assembler")
        assert len(panel_recipes) > 0
    
    def test_get_recipe_by_name(self):
        """测试按名称获取配方"""
        from src.world.solar_recipes import get_recipe_by_name
        
        recipe = get_recipe_by_name("purify_silicon")
        assert recipe is not None
        assert recipe.name == "purify_silicon"
        assert recipe.station_type == "silicon_purifier"
        assert "silicon_ore" in recipe.inputs
        assert "polysilicon" in recipe.outputs
    
    def test_recipe_for_output(self):
        """测试获取能产出指定物品的配方"""
        from src.world.solar_recipes import get_recipe_for_output
        
        # 硅片产出配方
        wafer_recipes = get_recipe_for_output("silicon_wafer")
        assert len(wafer_recipes) > 0
        
        # 电池片产出配方
        cell_recipes = get_recipe_for_output("solar_cell")
        assert len(cell_recipes) > 0
        
        # 组件产出配方
        panel_recipes = get_recipe_for_output("solar_panel")
        assert len(panel_recipes) > 0
    
    def test_material_requirement_calculation(self):
        """测试原材料需求计算"""
        from src.world.solar_recipes import calculate_material_requirement
        
        # 计算制造1块光伏组件的原材料需求
        materials = calculate_material_requirement("solar_panel", 1)
        
        assert isinstance(materials, dict)
        # 应该包含硅矿等原材料
        assert len(materials) > 0


class TestSolarItemRegistry:
    """光伏物品注册表测试"""
    
    def test_solar_items_loaded(self):
        """测试光伏物品加载"""
        from src.world.solar_items import SOLAR_ITEM_REGISTRY, SolarItemType
        
        assert len(SOLAR_ITEM_REGISTRY) > 0, "光伏物品列表不应为空"
    
    def test_get_solar_item(self):
        """测试获取光伏物品"""
        from src.world.solar_items import get_solar_item, SolarItemType
        
        # 测试获取硅矿
        silicon_ore = get_solar_item("silicon_ore")
        assert silicon_ore is not None
        assert silicon_ore.item_id == "silicon_ore"
        assert silicon_ore.item_type == SolarItemType.RAW_MATERIAL
        assert silicon_ore.mass > 0
        
        # 测试获取多晶硅
        polysilicon = get_solar_item("polysilicon")
        assert polysilicon is not None
        assert polysilicon.item_type == SolarItemType.INTERMEDIATE
        
        # 测试获取光伏组件
        panel = get_solar_item("solar_panel")
        assert panel is not None
        assert panel.item_type == SolarItemType.FINAL_PRODUCT
    
    def test_get_items_by_type(self):
        """测试按类型获取物品"""
        from src.world.solar_items import get_solar_items_by_type, SolarItemType
        
        raw_materials = get_solar_items_by_type(SolarItemType.RAW_MATERIAL)
        assert len(raw_materials) > 0
        
        intermediates = get_solar_items_by_type(SolarItemType.INTERMEDIATE)
        assert len(intermediates) > 0
        
        final_products = get_solar_items_by_type(SolarItemType.FINAL_PRODUCT)
        assert len(final_products) > 0
    
    def test_item_properties(self):
        """测试物品属性"""
        from src.world.solar_items import get_solar_item
        
        panel = get_solar_item("solar_panel")
        assert panel is not None
        
        # 检查基本属性
        assert panel.mass > 0
        assert len(panel.size) == 3
        assert all(s > 0 for s in panel.size)
        
        # 检查计算方法
        volume = panel.get_volume()
        assert volume > 0
        
        density = panel.get_density()
        assert density > 0


class TestSolarManufacturingStations:
    """光伏制造工站测试"""
    
    def test_silicon_purifier_creation(self):
        """测试硅料提纯站创建"""
        from src.workstation.solar_manufacturing import (
            SiliconPurifier, SiliconPurifierConfig
        )
        
        config = SiliconPurifierConfig(
            name="test_purifier",
            position=(10.0, 20.0, 0.0)
        )
        station = SiliconPurifier(config)
        
        assert station.config.name == "test_purifier"
        assert station.config.station_type == "silicon_purifier"
        assert station.temperature == 25.0
        assert station.purity_level == 0.0
    
    def test_crystal_grower_creation(self):
        """测试晶体生长站创建"""
        from src.workstation.solar_manufacturing import (
            CrystalGrower, CrystalGrowerConfig
        )
        
        config = CrystalGrowerConfig(
            name="test_grower",
            position=(20.0, 20.0, 0.0)
        )
        station = CrystalGrower(config)
        
        assert station.config.name == "test_grower"
        assert station.config.station_type == "crystal_grower"
        assert station.furnace_temp == 25.0
    
    def test_wafer_slicer_creation(self):
        """测试硅片切割站创建"""
        from src.workstation.solar_manufacturing import (
            WaferSlicer, WaferSlicerConfig
        )
        
        config = WaferSlicerConfig(
            name="test_slicer",
            position=(30.0, 20.0, 0.0)
        )
        station = WaferSlicer(config)
        
        assert station.config.name == "test_slicer"
        assert station.config.station_type == "wafer_slicer"
        assert station.wafers_cut == 0
    
    def test_solar_cell_fab_creation(self):
        """测试电池片制造站创建"""
        from src.workstation.solar_manufacturing import (
            SolarCellFab, SolarCellFabConfig
        )
        
        config = SolarCellFabConfig(
            name="test_cell_fab",
            position=(40.0, 20.0, 0.0)
        )
        station = SolarCellFab(config)
        
        assert station.config.name == "test_cell_fab"
        assert station.config.station_type == "solar_cell_fab"
        assert station.process_stage == 0
    
    def test_panel_assembler_creation(self):
        """测试组件封装站创建"""
        from src.workstation.solar_manufacturing import (
            PanelAssembler, PanelAssemblerConfig
        )
        
        config = PanelAssemblerConfig(
            name="test_assembler",
            position=(50.0, 20.0, 0.0)
        )
        station = PanelAssembler(config)
        
        assert station.config.name == "test_assembler"
        assert station.config.station_type == "panel_assembler"
        assert station.cells_soldered == 0
    
    def test_station_factory_function(self):
        """测试工站工厂函数"""
        from src.workstation.solar_manufacturing import create_solar_station
        
        # 创建各种类型的工站
        purifier = create_solar_station(
            "silicon_purifier", "purifier_1", (10, 10, 0)
        )
        assert purifier.config.station_type == "silicon_purifier"
        
        grower = create_solar_station(
            "crystal_grower", "grower_1", (20, 10, 0)
        )
        assert grower.config.station_type == "crystal_grower"
        
        slicer = create_solar_station(
            "wafer_slicer", "slicer_1", (30, 10, 0)
        )
        assert slicer.config.station_type == "wafer_slicer"


class TestSolarManufacturingChain:
    """光伏制造全链路测试"""
    
    def test_silicon_purification_process(self):
        """测试硅料提纯流程"""
        from src.workstation.solar_manufacturing import (
            SiliconPurifier, SiliconPurifierConfig
        )
        from workstation.base_station import StationState
        
        config = SiliconPurifierConfig(name="purifier_test")
        station = SiliconPurifier(config)
        
        # 投入原料
        result = station.receive_input("silicon_ore", 5)
        assert result == True
        assert "silicon_ore" in station.input_buffer
        
        station.receive_input("quartz_sand", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe is not None
        assert station.current_recipe.name == "purify_silicon"
        
        # 模拟加工完成
        station.process_timer = 0
        station.step(0.1)
        
        # 检查产出
        assert station.state == StationState.DONE
        assert len(station.output_buffer) == 2
        assert station.output_buffer[0].item_type == "polysilicon"
    
    def test_crystal_growing_process(self):
        """测试晶体生长流程"""
        from src.workstation.solar_manufacturing import (
            CrystalGrower, CrystalGrowerConfig
        )
        from workstation.base_station import StationState
        
        config = CrystalGrowerConfig(name="grower_test")
        station = CrystalGrower(config)
        
        # 投入原料
        station.receive_input("polysilicon", 3)
        station.receive_input("seed_crystal", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "grow_single_crystal"
    
    def test_wafer_slicing_process(self):
        """测试硅片切割流程"""
        from src.workstation.solar_manufacturing import (
            WaferSlicer, WaferSlicerConfig
        )
        from workstation.base_station import StationState
        
        config = WaferSlicerConfig(name="slicer_test")
        station = WaferSlicer(config)
        
        # 投入原料
        station.receive_input("silicon_ingot", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "slice_wafer"
        
        # 模拟加工完成
        station.process_timer = 0
        station.step(0.1)
        
        # 检查产出: 1根晶棒切50片硅片
        assert station.state == StationState.DONE
        assert len(station.output_buffer) == 51  # 50 wafers + 1 kerf
    
    def test_solar_cell_fabrication_process(self):
        """测试电池片制造流程"""
        from src.workstation.solar_manufacturing import (
            SolarCellFab, SolarCellFabConfig
        )
        from workstation.base_station import StationState
        
        config = SolarCellFabConfig(name="cell_fab_test")
        station = SolarCellFab(config)
        
        # 投入原料
        station.receive_input("silicon_wafer", 1)
        station.receive_input("silver_paste", 1)
        station.receive_input("aluminum_paste", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "make_solar_cell_perc"
    
    def test_panel_assembly_process(self):
        """测试组件封装流程"""
        from src.workstation.solar_manufacturing import (
            PanelAssembler, PanelAssemblerConfig
        )
        from workstation.base_station import StationState
        
        config = PanelAssemblerConfig(name="assembler_test")
        station = PanelAssembler(config)
        
        # 投入所有组件
        station.receive_input("solar_cell", 72)
        station.receive_input("glass_sheet", 2)
        station.receive_input("eva_film", 2)
        station.receive_input("aluminum_frame", 1)
        station.receive_input("junction_box", 1)
        station.receive_input("copper_wire", 5)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "assemble_panel_72cell"


class TestSolarDependencyGraph:
    """光伏制造依赖关系测试"""
    
    def test_dependency_graph_building(self):
        """测试依赖图构建"""
        from src.world.solar_recipes import build_solar_recipe_dependency_graph
        
        output_to_recipes, input_to_recipes = build_solar_recipe_dependency_graph()
        
        # 检查产出关系
        assert "polysilicon" in output_to_recipes
        assert "silicon_ingot" in output_to_recipes
        assert "silicon_wafer" in output_to_recipes
        assert "solar_cell" in output_to_recipes
        assert "solar_panel" in output_to_recipes
        
        # 检查消耗关系
        assert "silicon_ore" in input_to_recipes
        assert "polysilicon" in input_to_recipes
    
    def test_dependency_tree_printing(self):
        """测试依赖树打印"""
        from src.world.solar_recipes import print_solar_dependency_tree
        import io
        import sys
        
        # 捕获输出
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            print_solar_dependency_tree("solar_panel")
            output = sys.stdout.getvalue()
            
            # 检查输出包含关键物品
            assert "solar_panel" in output
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
