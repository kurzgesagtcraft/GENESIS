"""
储能电池制造全链路集成测试

测试储能电池系统制造从原材料到最终产品的完整流程。

文件: tests/integration/test_battery_chain.py
"""

import pytest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestBatteryRecipeSystem:
    """电池配方系统测试"""
    
    def test_battery_recipes_loaded(self):
        """测试电池配方加载"""
        from src.world.battery_recipes import BATTERY_RECIPES, BatteryRecipeType
        
        assert len(BATTERY_RECIPES) > 0, "电池配方列表不应为空"
        
        # 检查配方类型分布
        recipe_types = set(r.recipe_type for r in BATTERY_RECIPES)
        assert BatteryRecipeType.MATERIAL_REFINING in recipe_types
        assert BatteryRecipeType.CATHODE_SYNTHESIS in recipe_types
        assert BatteryRecipeType.ANODE_PROCESSING in recipe_types
        assert BatteryRecipeType.ELECTRODE_MANUFACTURING in recipe_types
        assert BatteryRecipeType.CELL_MANUFACTURING in recipe_types
        assert BatteryRecipeType.CELL_FORMATION in recipe_types
        assert BatteryRecipeType.PACK_ASSEMBLY in recipe_types
        assert BatteryRecipeType.SYSTEM_INTEGRATION in recipe_types
    
    def test_get_recipes_by_station(self):
        """测试按工站类型获取配方"""
        from src.world.battery_recipes import get_recipes_by_station
        
        # 锂提炼站配方
        refinery_recipes = get_recipes_by_station("lithium_refinery")
        assert len(refinery_recipes) > 0
        assert all(r.station_type == "lithium_refinery" for r in refinery_recipes)
        
        # 正极材料合成站配方
        cathode_recipes = get_recipes_by_station("cathode_synthesizer")
        assert len(cathode_recipes) > 0
        
        # 负极材料加工站配方
        anode_recipes = get_recipes_by_station("anode_processor")
        assert len(anode_recipes) > 0
        
        # 电极涂布站配方
        coater_recipes = get_recipes_by_station("electrode_coater")
        assert len(coater_recipes) > 0
        
        # 电芯组装站配方
        cell_recipes = get_recipes_by_station("cell_assembler")
        assert len(cell_recipes) > 0
        
        # 化成分容站配方
        formation_recipes = get_recipes_by_station("cell_formation")
        assert len(formation_recipes) > 0
        
        # 模组组装站配方
        module_recipes = get_recipes_by_station("module_assembler")
        assert len(module_recipes) > 0
        
        # 电池包组装站配方
        pack_recipes = get_recipes_by_station("pack_assembler")
        assert len(pack_recipes) > 0
        
        # 储能系统集成站配方
        ess_recipes = get_recipes_by_station("ess_integrator")
        assert len(ess_recipes) > 0
    
    def test_get_recipe_by_name(self):
        """测试按名称获取配方"""
        from src.world.battery_recipes import get_recipe_by_name
        
        recipe = get_recipe_by_name("refine_lithium_carbonate")
        assert recipe is not None
        assert recipe.name == "refine_lithium_carbonate"
        assert recipe.station_type == "lithium_refinery"
        assert "lithium_ore" in recipe.inputs
        assert "lithium_carbonate" in recipe.outputs
    
    def test_recipe_for_output(self):
        """测试获取能产出指定物品的配方"""
        from src.world.battery_recipes import get_recipe_for_output
        
        # 碳酸锂产出配方
        lithium_recipes = get_recipe_for_output("lithium_carbonate")
        assert len(lithium_recipes) > 0
        
        # 正极材料产出配方
        cathode_recipes = get_recipe_for_output("lfp_cathode")
        assert len(cathode_recipes) > 0
        
        # 电芯产出配方
        cell_recipes = get_recipe_for_output("battery_cell")
        assert len(cell_recipes) > 0
        
        # 储能系统产出配方
        ess_recipes = get_recipe_for_output("energy_storage_system")
        assert len(ess_recipes) > 0
    
    def test_material_requirement_calculation(self):
        """测试原材料需求计算"""
        from src.world.battery_recipes import calculate_material_requirement
        
        # 计算制造1套储能系统的原材料需求
        materials = calculate_material_requirement("energy_storage_system", 1)
        
        assert isinstance(materials, dict)
        # 应该包含锂矿等原材料
        assert len(materials) > 0


class TestBatteryItemRegistry:
    """电池物品注册表测试"""
    
    def test_battery_items_loaded(self):
        """测试电池物品加载"""
        from src.world.battery_items import BATTERY_ITEM_REGISTRY, BatteryItemType
        
        assert len(BATTERY_ITEM_REGISTRY) > 0, "电池物品列表不应为空"
    
    def test_get_battery_item(self):
        """测试获取电池物品"""
        from src.world.battery_items import get_battery_item, BatteryItemType
        
        # 测试获取锂矿
        lithium_ore = get_battery_item("lithium_ore")
        assert lithium_ore is not None
        assert lithium_ore.item_id == "lithium_ore"
        assert lithium_ore.item_type == BatteryItemType.RAW_MATERIAL
        assert lithium_ore.mass > 0
        
        # 测试获取碳酸锂
        lithium_carbonate = get_battery_item("lithium_carbonate")
        assert lithium_carbonate is not None
        assert lithium_carbonate.item_type == BatteryItemType.INTERMEDIATE
        
        # 测试获取储能系统
        ess = get_battery_item("energy_storage_system")
        assert ess is not None
        assert ess.item_type == BatteryItemType.FINAL_PRODUCT
    
    def test_get_items_by_type(self):
        """测试按类型获取物品"""
        from src.world.battery_items import get_battery_items_by_type, BatteryItemType
        
        raw_materials = get_battery_items_by_type(BatteryItemType.RAW_MATERIAL)
        assert len(raw_materials) > 0
        
        intermediates = get_battery_items_by_type(BatteryItemType.INTERMEDIATE)
        assert len(intermediates) > 0
        
        final_products = get_battery_items_by_type(BatteryItemType.FINAL_PRODUCT)
        assert len(final_products) > 0
    
    def test_item_properties(self):
        """测试物品属性"""
        from src.world.battery_items import get_battery_item
        
        ess = get_battery_item("energy_storage_system")
        assert ess is not None
        
        # 检查基本属性
        assert ess.mass > 0
        assert len(ess.size) == 3
        assert all(s > 0 for s in ess.size)
        
        # 检查计算方法
        volume = ess.get_volume()
        assert volume > 0
        
        density = ess.get_density()
        assert density > 0


class TestBatteryManufacturingStations:
    """电池制造工站测试"""
    
    def test_lithium_refinery_creation(self):
        """测试锂提炼站创建"""
        from src.workstation.battery_manufacturing import (
            LithiumRefinery, LithiumRefineryConfig
        )
        
        config = LithiumRefineryConfig(
            name="test_refinery",
            position=(10.0, 30.0, 0.0)
        )
        station = LithiumRefinery(config)
        
        assert station.config.name == "test_refinery"
        assert station.config.station_type == "lithium_refinery"
        assert station.temperature == 25.0
        assert station.purity_level == 0.0
    
    def test_cathode_synthesizer_creation(self):
        """测试正极材料合成站创建"""
        from src.workstation.battery_manufacturing import (
            CathodeSynthesizer, CathodeSynthesizerConfig
        )
        
        config = CathodeSynthesizerConfig(
            name="test_cathode",
            position=(20.0, 30.0, 0.0)
        )
        station = CathodeSynthesizer(config)
        
        assert station.config.name == "test_cathode"
        assert station.config.station_type == "cathode_synthesizer"
        assert station.furnace_temp == 25.0
    
    def test_anode_processor_creation(self):
        """测试负极材料加工站创建"""
        from src.workstation.battery_manufacturing import (
            AnodeProcessor, AnodeProcessorConfig
        )
        
        config = AnodeProcessorConfig(
            name="test_anode",
            position=(30.0, 30.0, 0.0)
        )
        station = AnodeProcessor(config)
        
        assert station.config.name == "test_anode"
        assert station.config.station_type == "anode_processor"
        assert station.furnace_temp == 25.0
    
    def test_electrode_coater_creation(self):
        """测试电极涂布站创建"""
        from src.workstation.battery_manufacturing import (
            ElectrodeCoater, ElectrodeCoaterConfig
        )
        
        config = ElectrodeCoaterConfig(
            name="test_coater",
            position=(40.0, 30.0, 0.0)
        )
        station = ElectrodeCoater(config)
        
        assert station.config.name == "test_coater"
        assert station.config.station_type == "electrode_coater"
        assert station.coating_speed == 0.0
    
    def test_cell_assembler_creation(self):
        """测试电芯组装站创建"""
        from src.workstation.battery_manufacturing import (
            CellAssembler, CellAssemblerConfig
        )
        
        config = CellAssemblerConfig(
            name="test_cell_assembler",
            position=(50.0, 30.0, 0.0)
        )
        station = CellAssembler(config)
        
        assert station.config.name == "test_cell_assembler"
        assert station.config.station_type == "cell_assembler"
        assert station.process_stage == 0
    
    def test_cell_formation_creation(self):
        """测试化成分容站创建"""
        from src.workstation.battery_manufacturing import (
            CellFormation, CellFormationConfig
        )
        
        config = CellFormationConfig(
            name="test_formation",
            position=(60.0, 30.0, 0.0)
        )
        station = CellFormation(config)
        
        assert station.config.name == "test_formation"
        assert station.config.station_type == "cell_formation"
        assert station.formation_cycle == 0
    
    def test_module_assembler_creation(self):
        """测试模组组装站创建"""
        from src.workstation.battery_manufacturing import (
            ModuleAssembler, ModuleAssemblerConfig
        )
        
        config = ModuleAssemblerConfig(
            name="test_module",
            position=(70.0, 30.0, 0.0)
        )
        station = ModuleAssembler(config)
        
        assert station.config.name == "test_module"
        assert station.config.station_type == "module_assembler"
    
    def test_pack_assembler_creation(self):
        """测试电池包组装站创建"""
        from src.workstation.battery_manufacturing import (
            PackAssembler, PackAssemblerConfig
        )
        
        config = PackAssemblerConfig(
            name="test_pack",
            position=(80.0, 30.0, 0.0)
        )
        station = PackAssembler(config)
        
        assert station.config.name == "test_pack"
        assert station.config.station_type == "pack_assembler"
    
    def test_ess_integrator_creation(self):
        """测试储能系统集成站创建"""
        from src.workstation.battery_manufacturing import (
            ESSIntegrator, ESSIntegratorConfig
        )
        
        config = ESSIntegratorConfig(
            name="test_ess",
            position=(90.0, 30.0, 0.0)
        )
        station = ESSIntegrator(config)
        
        assert station.config.name == "test_ess"
        assert station.config.station_type == "ess_integrator"
    
    def test_station_factory_function(self):
        """测试工站工厂函数"""
        from src.workstation.battery_manufacturing import create_battery_station
        
        # 创建各种类型的工站
        refinery = create_battery_station(
            "lithium_refinery", "refinery_1", (10, 10, 0)
        )
        assert refinery.config.station_type == "lithium_refinery"
        
        cathode = create_battery_station(
            "cathode_synthesizer", "cathode_1", (20, 10, 0)
        )
        assert cathode.config.station_type == "cathode_synthesizer"
        
        anode = create_battery_station(
            "anode_processor", "anode_1", (30, 10, 0)
        )
        assert anode.config.station_type == "anode_processor"


class TestBatteryManufacturingChain:
    """电池制造全链路测试"""
    
    def test_lithium_refining_process(self):
        """测试锂提炼流程"""
        from src.workstation.battery_manufacturing import (
            LithiumRefinery, LithiumRefineryConfig
        )
        from workstation.base_station import StationState
        
        config = LithiumRefineryConfig(name="refinery_test")
        station = LithiumRefinery(config)
        
        # 投入原料
        result = station.receive_input("lithium_ore", 10)
        assert result == True
        assert "lithium_ore" in station.input_buffer
        
        station.receive_input("limestone", 2)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe is not None
        assert station.current_recipe.name == "refine_lithium_carbonate"
        
        # 模拟加工完成
        station.process_timer = 0
        station.step(0.1)
        
        # 检查产出
        assert station.state == StationState.DONE
        assert len(station.output_buffer) == 3
        assert station.output_buffer[0].item_type == "lithium_carbonate"
    
    def test_cathode_synthesis_process(self):
        """测试正极材料合成流程"""
        from src.workstation.battery_manufacturing import (
            CathodeSynthesizer, CathodeSynthesizerConfig
        )
        from workstation.base_station import StationState
        
        config = CathodeSynthesizerConfig(name="cathode_test")
        station = CathodeSynthesizer(config)
        
        # 投入原料
        station.receive_input("lithium_carbonate", 1)
        station.receive_input("iron_phosphate", 1)
        station.receive_input("carbon_source", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "make_lfp_cathode"
    
    def test_anode_processing_process(self):
        """测试负极材料加工流程"""
        from src.workstation.battery_manufacturing import (
            AnodeProcessor, AnodeProcessorConfig
        )
        from workstation.base_station import StationState
        
        config = AnodeProcessorConfig(name="anode_test")
        station = AnodeProcessor(config)
        
        # 投入原料
        station.receive_input("graphite_ore", 5)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "process_graphite_anode"
        
        # 模拟加工完成
        station.process_timer = 0
        station.step(0.1)
        
        # 检查产出
        assert station.state == StationState.DONE
        assert len(station.output_buffer) == 3  # 2 graphite_anode + 1 waste
    
    def test_electrode_coating_process(self):
        """测试电极涂布流程"""
        from src.workstation.battery_manufacturing import (
            ElectrodeCoater, ElectrodeCoaterConfig
        )
        from workstation.base_station import StationState
        
        config = ElectrodeCoaterConfig(name="coater_test")
        station = ElectrodeCoater(config)
        
        # 投入原料
        station.receive_input("lfp_cathode", 1)
        station.receive_input("aluminum_foil", 1)
        station.receive_input("binder", 1)
        station.receive_input("conductive_agent", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "coat_cathode_lfp"
    
    def test_cell_assembly_process(self):
        """测试电芯组装流程"""
        from src.workstation.battery_manufacturing import (
            CellAssembler, CellAssemblerConfig
        )
        from workstation.base_station import StationState
        
        config = CellAssemblerConfig(name="cell_assembly_test")
        station = CellAssembler(config)
        
        # 投入原料
        station.receive_input("cathode_sheet", 1)
        station.receive_input("anode_sheet", 1)
        station.receive_input("separator", 2)
        station.receive_input("electrolyte", 1)
        station.receive_input("cell_can", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "assemble_cell_lfp"
    
    def test_cell_formation_process(self):
        """测试化成分容流程"""
        from src.workstation.battery_manufacturing import (
            CellFormation, CellFormationConfig
        )
        from workstation.base_station import StationState
        
        config = CellFormationConfig(name="formation_test")
        station = CellFormation(config)
        
        # 投入原料
        station.receive_input("battery_cell", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "form_cell"
    
    def test_module_assembly_process(self):
        """测试模组组装流程"""
        from src.workstation.battery_manufacturing import (
            ModuleAssembler, ModuleAssemblerConfig
        )
        from workstation.base_station import StationState
        
        config = ModuleAssemblerConfig(name="module_test")
        station = ModuleAssembler(config)
        
        # 投入原料
        station.receive_input("formed_cell", 4)
        station.receive_input("busbar", 5)
        station.receive_input("bms_board", 1)
        station.receive_input("thermal_pad", 4)
        station.receive_input("module_frame", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "assemble_module_1p4s"
    
    def test_pack_assembly_process(self):
        """测试电池包组装流程"""
        from src.workstation.battery_manufacturing import (
            PackAssembler, PackAssemblerConfig
        )
        from workstation.base_station import StationState
        
        config = PackAssemblerConfig(name="pack_test")
        station = PackAssembler(config)
        
        # 投入原料
        station.receive_input("battery_module", 4)
        station.receive_input("cooling_plate", 2)
        station.receive_input("hv_connector", 4)
        station.receive_input("pack_enclosure", 1)
        station.receive_input("main_bms", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "assemble_pack_medium"
    
    def test_ess_integration_process(self):
        """测试储能系统集成流程"""
        from src.workstation.battery_manufacturing import (
            ESSIntegrator, ESSIntegratorConfig
        )
        from workstation.base_station import StationState
        
        config = ESSIntegratorConfig(name="ess_test")
        station = ESSIntegrator(config)
        
        # 投入原料
        station.receive_input("battery_pack", 4)
        station.receive_input("pcs_unit", 1)
        station.receive_input("master_bms", 1)
        station.receive_input("fire_suppression", 1)
        station.receive_input("container", 1)
        
        # 检查配方启动
        assert station.state == StationState.PROCESSING
        assert station.current_recipe.name == "integrate_ess_medium"


class TestBatteryDependencyGraph:
    """电池制造依赖关系测试"""
    
    def test_dependency_graph_building(self):
        """测试依赖图构建"""
        from src.world.battery_recipes import build_battery_recipe_dependency_graph
        
        output_to_recipes, input_to_recipes = build_battery_recipe_dependency_graph()
        
        # 检查产出关系
        assert "lithium_carbonate" in output_to_recipes
        assert "lfp_cathode" in output_to_recipes
        assert "battery_cell" in output_to_recipes
        assert "energy_storage_system" in output_to_recipes
        
        # 检查消耗关系
        assert "lithium_ore" in input_to_recipes
        assert "lithium_carbonate" in input_to_recipes
    
    def test_dependency_tree_printing(self):
        """测试依赖树打印"""
        from src.world.battery_recipes import print_battery_dependency_tree
        import io
        import sys
        
        # 捕获输出
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        
        try:
            print_battery_dependency_tree("energy_storage_system")
            output = sys.stdout.getvalue()
            
            # 检查输出包含关键物品
            assert "energy_storage_system" in output
        finally:
            sys.stdout = old_stdout


class TestEnergyLoop:
    """能源闭环测试"""
    
    def test_energy_system_integration(self):
        """测试能源系统集成"""
        # 这个测试验证光伏+储能系统的集成
        from src.world.solar_recipes import SOLAR_RECIPES
        from src.world.battery_recipes import BATTERY_RECIPES
        
        # 检查两个系统都有完整的配方
        assert len(SOLAR_RECIPES) > 0
        assert len(BATTERY_RECIPES) > 0
        
        # 检查光伏系统可以产出最终产品
        solar_final_products = [
            r for r in SOLAR_RECIPES 
            if any("solar_panel" in o or "solar_array" in o for o in r.outputs)
        ]
        assert len(solar_final_products) > 0
        
        # 检查储能系统可以产出最终产品
        battery_final_products = [
            r for r in BATTERY_RECIPES 
            if any("energy_storage_system" in o or "megawatt_ess" in o for o in r.outputs)
        ]
        assert len(battery_final_products) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
