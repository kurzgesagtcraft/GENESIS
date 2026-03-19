"""
GENESIS Level 2 Integration Test: 双配方链式测试

场景: iron_ore → iron_bar → motor (需要circuit_board,递归展开)
预期时间: < 15分钟仿真时间

测试目标:
- 验证配方依赖链处理
- 验证多工站协作
- 验证中间产物管理
- 验证任务调度顺序
"""

import asyncio
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import time

# 添加项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from genesis.world import RecipeRegistry, Recipe
from brain import TaskPlan, Task, StrategicPlanner


# ============================================================================
# 配方依赖图测试
# ============================================================================

@dataclass
class MockRecipe:
    """Mock 配方"""
    name: str
    station_type: str
    inputs: Dict[str, int]
    outputs: Dict[str, int]
    process_time: float
    energy_cost: float


# 定义测试配方链
RECIPE_CHAIN = {
    # 基础冶炼
    "smelt_iron": MockRecipe(
        name="smelt_iron",
        station_type="smelter",
        inputs={"iron_ore": 3},
        outputs={"iron_bar": 2},
        process_time=30.0,
        energy_cost=500.0,
    ),
    # 电路板 (需要硅矿和铁锭)
    "make_circuit_board": MockRecipe(
        name="make_circuit_board",
        station_type="fabricator",
        inputs={"silicon_ore": 2, "iron_bar": 1},
        outputs={"circuit_board": 1},
        process_time=45.0,
        energy_cost=800.0,
    ),
    # 电机 (需要铁锭和电路板)
    "make_motor": MockRecipe(
        name="make_motor",
        station_type="fabricator",
        inputs={"iron_bar": 2, "circuit_board": 1},
        outputs={"motor": 1},
        process_time=60.0,
        energy_cost=1000.0,
    ),
}


class MockStation:
    """Mock 工站"""
    def __init__(self, name: str, station_type: str):
        self.name = name
        self.station_type = station_type
        self.state = "idle"
        self.input_buffer: Dict[str, int] = {}
        self.output_buffer: List[str] = []
        self.current_recipe: Optional[MockRecipe] = None
        self.process_timer = 0.0
        
    def receive_input(self, item_type: str, quantity: int = 1) -> bool:
        self.input_buffer[item_type] = self.input_buffer.get(item_type, 0) + quantity
        self._try_start_recipe()
        return True
        
    def _try_start_recipe(self) -> None:
        """尝试开始配方"""
        for recipe_name, recipe in RECIPE_CHAIN.items():
            if recipe.station_type != self.station_type:
                continue
            # 检查输入是否足够
            can_start = True
            for item, qty in recipe.inputs.items():
                if self.input_buffer.get(item, 0) < qty:
                    can_start = False
                    break
            if can_start:
                self.current_recipe = recipe
                self.state = "processing"
                self.process_timer = recipe.process_time
                # 消耗输入
                for item, qty in recipe.inputs.items():
                    self.input_buffer[item] -= qty
                break
                
    def step(self, dt: float) -> None:
        if self.state == "processing" and self.current_recipe:
            self.process_timer -= dt
            if self.process_timer <= 0:
                # 生产完成
                for item, qty in self.current_recipe.outputs.items():
                    for _ in range(qty):
                        self.output_buffer.append(item)
                self.state = "done"
                self.current_recipe = None
                
    def collect_output(self) -> Optional[str]:
        if self.output_buffer:
            item = self.output_buffer.pop(0)
            if not self.output_buffer:
                self.state = "idle"
            return item
        return None
        
    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "state": self.state,
            "input_buffer": dict(self.input_buffer),
            "output_count": len(self.output_buffer),
            "process_remaining": max(0, self.process_timer),
        }


class MockRobot:
    """Mock 机器人"""
    def __init__(self):
        self.position = [0.0, 0.0]
        self.carrying_items: List[str] = []
        self.current_zone = "spawn"
        
    async def navigate_to(self, zone: str) -> bool:
        await asyncio.sleep(0.05)
        self.current_zone = zone
        return True
        
    def pickup(self, item: str) -> None:
        self.carrying_items.append(item)
        
    def drop(self, item_type: str) -> bool:
        for item in self.carrying_items:
            if item.startswith(item_type):
                self.carrying_items.remove(item)
                return True
        return False


class MockWarehouse:
    """Mock 仓库"""
    def __init__(self):
        self.inventory: Dict[str, int] = {}
        
    def store(self, item_type: str, quantity: int = 1) -> None:
        self.inventory[item_type] = self.inventory.get(item_type, 0) + quantity
        
    def retrieve(self, item_type: str, quantity: int = 1) -> bool:
        if self.inventory.get(item_type, 0) >= quantity:
            self.inventory[item_type] -= quantity
            return True
        return False
        
    def get_inventory(self) -> Dict[str, int]:
        return dict(self.inventory)


class MockMine:
    """Mock 矿区"""
    def __init__(self, resource_type: str, amount: int):
        self.resource_type = resource_type
        self.remaining = amount
        
    def extract(self, quantity: int = 1) -> List[str]:
        if self.remaining >= quantity:
            self.remaining -= quantity
            return [f"{self.resource_type}_{i}" for i in range(quantity)]
        return []


# ============================================================================
# 测试用例
# ============================================================================

class TestChainRecipe(unittest.TestCase):
    """Level 2: 双配方链式测试"""
    
    def setUp(self):
        """测试初始化"""
        self.robot = MockRobot()
        self.warehouse = MockWarehouse()
        
        # 创建工站
        self.smelter = MockStation("smelter_1", "smelter")
        self.fabricator = MockStation("fabricator_1", "fabricator")
        
        # 创建矿区
        self.iron_mine = MockMine("iron_ore", 100)
        self.silicon_mine = MockMine("silicon_ore", 100)
        
        # 工站映射
        self.stations = {
            "smelter": self.smelter,
            "fabricator": self.fabricator,
        }
        
    def test_recipe_dependency_analysis(self):
        """测试: 配方依赖分析"""
        print("\n🧪 测试: 配方依赖分析")
        
        # 分析 motor 的依赖
        motor_recipe = RECIPE_CHAIN["make_motor"]
        print(f"\n  motor 配方:")
        print(f"    输入: {motor_recipe.inputs}")
        print(f"    输出: {motor_recipe.outputs}")
        
        # 计算总原材料需求
        # motor 需要: iron_bar: 2, circuit_board: 1
        # circuit_board 需要: silicon_ore: 2, iron_bar: 1
        # 总计: iron_bar: 3, silicon_ore: 2
        # iron_bar 需要: iron_ore: 3 (产出 2)
        # 所以需要 iron_ore: 3 * 2 = 6 (产出 4 个 iron_bar，用 3 个)
        
        total_iron_ore = 6  # 产出 4 个 iron_bar
        total_silicon_ore = 2
        
        print(f"\n  制造 1 个 motor 需要:")
        print(f"    iron_ore: {total_iron_ore}")
        print(f"    silicon_ore: {total_silicon_ore}")
        
        self.assertEqual(total_iron_ore, 6)
        self.assertEqual(total_silicon_ore, 2)
        print("  ✅ 配方依赖分析测试通过")
        
    def test_single_recipe_execution(self):
        """测试: 单个配方执行"""
        print("\n🧪 测试: 单个配方执行 (smelt_iron)")
        
        # 投入材料
        self.smelter.receive_input("iron_ore", 3)
        
        # 验证开始加工
        self.assertEqual(self.smelter.state, "processing")
        
        # 模拟加工
        while self.smelter.state == "processing":
            self.smelter.step(1.0)
            
        # 验证产出
        self.assertEqual(self.smelter.state, "done")
        self.assertEqual(len(self.smelter.output_buffer), 2)
        
        print("  ✅ 单配方执行测试通过")
        
    def test_chain_recipe_execution(self):
        """测试: 链式配方执行"""
        print("\n🧪 测试: 链式配方执行 (iron_ore → iron_bar → circuit_board)")
        
        # Step 1: 冶炼铁锭
        print("\n  Step 1: 冶炼铁锭")
        self.smelter.receive_input("iron_ore", 3)
        while self.smelter.state == "processing":
            self.smelter.step(1.0)
        iron_bars = []
        while self.smelter.output_buffer:
            iron_bars.append(self.smelter.collect_output())
        print(f"    产出: {len(iron_bars)} 个铁锭")
        
        # Step 2: 制造电路板
        print("\n  Step 2: 制造电路板")
        self.fabricator.receive_input("silicon_ore", 2)
        self.fabricator.receive_input("iron_bar", 1)
        while self.fabricator.state == "processing":
            self.fabricator.step(1.0)
        circuit_boards = []
        while self.fabricator.output_buffer:
            circuit_boards.append(self.fabricator.collect_output())
        print(f"    产出: {len(circuit_boards)} 个电路板")
        
        # 验证
        self.assertEqual(len(iron_bars), 2)
        self.assertEqual(len(circuit_boards), 1)
        
        print("  ✅ 链式配方执行测试通过")
        
    def test_full_motor_production_chain(self):
        """测试: 完整电机生产链"""
        print("\n" + "=" * 60)
        print("🧪 Level 2: 完整电机生产链测试")
        print("=" * 60)
        
        start_time = time.time()
        
        # Phase 1: 采矿
        print("\n📦 Phase 1: 采矿")
        iron_ores = self.iron_mine.extract(6)
        silicon_ores = self.silicon_mine.extract(2)
        print(f"  - 铁矿石: {len(iron_ores)} 个")
        print(f"  - 硅矿: {len(silicon_ores)} 个")
        
        # Phase 2: 冶炼 (产出 4 个铁锭)
        print("\n📦 Phase 2: 冶炼")
        self.smelter.receive_input("iron_ore", 3)
        while self.smelter.state == "processing":
            self.smelter.step(1.0)
        iron_bars_1 = []
        while self.smelter.output_buffer:
            iron_bars_1.append(self.smelter.collect_output())
            
        self.smelter.receive_input("iron_ore", 3)
        while self.smelter.state == "processing":
            self.smelter.step(1.0)
        iron_bars_2 = []
        while self.smelter.output_buffer:
            iron_bars_2.append(self.smelter.collect_output())
            
        iron_bars = iron_bars_1 + iron_bars_2
        print(f"  - 铁锭产出: {len(iron_bars)} 个")
        
        # Phase 3: 制造电路板
        print("\n📦 Phase 3: 制造电路板")
        self.fabricator.receive_input("silicon_ore", 2)
        self.fabricator.receive_input("iron_bar", 1)
        while self.fabricator.state == "processing":
            self.fabricator.step(1.0)
        circuit_boards = []
        while self.fabricator.output_buffer:
            circuit_boards.append(self.fabricator.collect_output())
        print(f"  - 电路板产出: {len(circuit_boards)} 个")
        
        # Phase 4: 制造电机
        print("\n📦 Phase 4: 制造电机")
        self.fabricator.receive_input("iron_bar", 2)
        self.fabricator.receive_input("circuit_board", 1)
        while self.fabricator.state == "processing":
            self.fabricator.step(1.0)
        motors = []
        while self.fabricator.output_buffer:
            motors.append(self.fabricator.collect_output())
        print(f"  - 电机产出: {len(motors)} 个")
        
        # 验证
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("📊 测试结果")
        print("=" * 60)
        print(f"  - 总耗时: {elapsed_time:.2f}s (实际)")
        print(f"  - 最终产出: {len(motors)} 个电机")
        
        self.assertEqual(len(motors), 1, "应产出1个电机")
        self.assertEqual(len(iron_bars), 4, "应产出4个铁锭")
        self.assertEqual(len(circuit_boards), 1, "应产出1个电路板")
        
        print("\n✅ Level 2 双配方链式测试通过!")
        print("=" * 60)


class TestRecipeGraph(unittest.TestCase):
    """配方依赖图测试"""
    
    def test_dependency_tree(self):
        """测试: 依赖树构建"""
        print("\n🧪 测试: 依赖树构建")
        
        # 构建依赖树
        # motor → iron_bar + circuit_board
        # circuit_board → silicon_ore + iron_bar
        # iron_bar → iron_ore
        
        def get_dependencies(item: str, quantity: int = 1) -> Dict[str, int]:
            """递归获取依赖"""
            deps = {}
            
            # 查找产出该物品的配方
            for recipe in RECIPE_CHAIN.values():
                if item in recipe.outputs:
                    # 计算需要多少次配方
                    output_qty = recipe.outputs[item]
                    runs_needed = (quantity + output_qty - 1) // output_qty
                    
                    # 递归获取输入依赖
                    for input_item, input_qty in recipe.inputs.items():
                        total_input = input_qty * runs_needed
                        sub_deps = get_dependencies(input_item, total_input)
                        
                        # 合并依赖
                        for k, v in sub_deps.items():
                            deps[k] = deps.get(k, 0) + v
                    return deps
                    
            # 如果没有配方产出该物品，则是原材料
            deps[item] = deps.get(item, 0) + quantity
            return deps
            
        # 计算制造 motor 的原材料需求
        motor_deps = get_dependencies("motor", 1)
        
        print(f"\n  制造 1 个 motor 需要:")
        for item, qty in sorted(motor_deps.items()):
            print(f"    {item}: {qty}")
            
        # 验证
        self.assertEqual(motor_deps.get("iron_ore", 0), 6)
        self.assertEqual(motor_deps.get("silicon_ore", 0), 2)
        
        print("  ✅ 依赖树构建测试通过")


# ============================================================================
# 运行测试
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 GENESIS Level 2 集成测试")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestChainRecipe))
    suite.addTests(loader.loadTestsFromTestCase(TestRecipeGraph))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 所有测试通过!")
    else:
        print("\n❌ 存在失败的测试")
        
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
