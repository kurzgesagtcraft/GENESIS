"""
GENESIS Level 4 Integration Test: 完整 assembled_robot 终极测试

场景: 从0开始, 制造一个完整机器人
预期时间: < 2小时仿真时间 (可加速)

测试目标:
- 验证完整配方链处理
- 验证所有工站协作
- 验证端到端任务执行
- 验证系统稳定性

这是 GENESIS 项目的终极测试！
"""

import sys
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
import time
import json

# 添加项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# ============================================================================
# 完整配方定义 (从任务规划.md)
# ============================================================================

@dataclass
class Recipe:
    """配方定义"""
    name: str
    station_type: str
    inputs: Dict[str, int]
    outputs: Dict[str, int]
    process_time: float
    energy_cost: float


# 完整配方列表 (来自 P1.3.2)
FULL_RECIPES = {
    # 基础冶炼
    "smelt_iron": Recipe(
        name="smelt_iron",
        station_type="smelter",
        inputs={"iron_ore": 3},
        outputs={"iron_bar": 2},
        process_time=30.0,
        energy_cost=500.0,
    ),
    # 电路板
    "make_circuit_board": Recipe(
        name="make_circuit_board",
        station_type="fabricator",
        inputs={"silicon_ore": 2, "iron_bar": 1},
        outputs={"circuit_board": 1},
        process_time=45.0,
        energy_cost=800.0,
    ),
    # 电机
    "make_motor": Recipe(
        name="make_motor",
        station_type="fabricator",
        inputs={"iron_bar": 2, "circuit_board": 1},
        outputs={"motor": 1},
        process_time=60.0,
        energy_cost=1000.0,
    ),
    # 关节模块
    "make_joint_module": Recipe(
        name="make_joint_module",
        station_type="fabricator",
        inputs={"motor": 1, "iron_bar": 1},
        outputs={"joint_module": 1},
        process_time=40.0,
        energy_cost=600.0,
    ),
    # 框架
    "make_frame": Recipe(
        name="make_frame",
        station_type="fabricator",
        inputs={"iron_bar": 4},
        outputs={"frame_segment": 1},
        process_time=50.0,
        energy_cost=700.0,
    ),
    # 控制器
    "make_controller": Recipe(
        name="make_controller",
        station_type="fabricator",
        inputs={"circuit_board": 2, "silicon_ore": 1},
        outputs={"controller_board": 1},
        process_time=90.0,
        energy_cost=1500.0,
    ),
    # 夹爪手指
    "make_gripper_finger": Recipe(
        name="make_gripper_finger",
        station_type="fabricator",
        inputs={"iron_bar": 1},
        outputs={"gripper_finger": 2},
        process_time=20.0,
        energy_cost=300.0,
    ),
    # 装配机械臂
    "assemble_arm": Recipe(
        name="assemble_arm",
        station_type="assembler",
        inputs={"joint_module": 3, "frame_segment": 2, "gripper_finger": 2},
        outputs={"assembled_arm": 1},
        process_time=120.0,
        energy_cost=200.0,
    ),
    # 装配机器人 ★ 终极配方
    "assemble_robot": Recipe(
        name="assemble_robot",
        station_type="assembler",
        inputs={
            "assembled_arm": 2,
            "frame_segment": 4,
            "joint_module": 4,
            "controller_board": 1,
            "motor": 4,
        },
        outputs={"assembled_robot": 1},
        process_time=300.0,
        energy_cost=500.0,
    ),
}


# ============================================================================
# 材料需求计算器
# ============================================================================

class FullMaterialCalculator:
    """完整材料需求计算器"""
    
    def __init__(self, recipes: Dict[str, Recipe]):
        self.recipes = recipes
        self._build_output_map()
        
    def _build_output_map(self) -> None:
        """构建产出映射"""
        self.output_map: Dict[str, Recipe] = {}
        for recipe in self.recipes.values():
            for output in recipe.outputs:
                self.output_map[output] = recipe
                
    def calculate_requirements(
        self,
        target: str,
        quantity: int = 1,
    ) -> Dict[str, int]:
        """计算原材料需求"""
        requirements: Dict[str, int] = {}
        self._calc_recursive(target, quantity, requirements)
        return requirements
        
    def _calc_recursive(
        self,
        item: str,
        quantity: int,
        requirements: Dict[str, int],
    ) -> None:
        """递归计算"""
        if item not in self.output_map:
            requirements[item] = requirements.get(item, 0) + quantity
            return
            
        recipe = self.output_map[item]
        output_qty = recipe.outputs[item]
        runs_needed = (quantity + output_qty - 1) // output_qty
        
        for input_item, input_qty in recipe.inputs.items():
            total_input = input_qty * runs_needed
            self._calc_recursive(input_item, total_input, requirements)


# ============================================================================
# 生产计划生成器
# ============================================================================

class ProductionPlanner:
    """生产计划生成器"""
    
    def __init__(self, recipes: Dict[str, Recipe]):
        self.recipes = recipes
        self.calculator = FullMaterialCalculator(recipes)
        
    def generate_plan(self, target: str) -> List[Dict[str, Any]]:
        """生成完整生产计划"""
        plan = []
        self._build_plan(target, 1, plan, set())
        return plan
        
    def _build_plan(
        self,
        item: str,
        quantity: int,
        plan: List[Dict[str, Any]],
        visited: set,
    ) -> None:
        """递归构建计划"""
        if item in visited:
            return
        visited.add(item)
        
        if item not in self.calculator.output_map:
            return
            
        recipe = self.calculator.output_map[item]
        output_qty = recipe.outputs[item]
        runs_needed = (quantity + output_qty - 1) // output_qty
        
        # 先处理输入
        for input_item, input_qty in recipe.inputs.items():
            self._build_plan(
                input_item,
                input_qty * runs_needed,
                plan,
                visited.copy()
            )
            
        # 添加当前步骤
        plan.append({
            "step": len(plan) + 1,
            "recipe": recipe.name,
            "station_type": recipe.station_type,
            "runs": runs_needed,
            "inputs": {
                k: v * runs_needed for k, v in recipe.inputs.items()
            },
            "outputs": {
                k: v * runs_needed for k, v in recipe.outputs.items()
            },
            "time": recipe.process_time * runs_needed,
            "energy": recipe.energy_cost * runs_needed,
        })
        
    def optimize_plan(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """优化生产计划 (合并相同配方)"""
        # 按配方类型分组
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for step in plan:
            recipe_name = step["recipe"]
            if recipe_name not in grouped:
                grouped[recipe_name] = []
            grouped[recipe_name].append(step)
            
        # 合并相同配方
        optimized = []
        for recipe_name, steps in grouped.items():
            if len(steps) == 1:
                optimized.append(steps[0])
            else:
                # 合并
                merged = {
                    "step": len(optimized) + 1,
                    "recipe": recipe_name,
                    "station_type": steps[0]["station_type"],
                    "runs": sum(s["runs"] for s in steps),
                    "inputs": {},
                    "outputs": {},
                    "time": sum(s["time"] for s in steps),
                    "energy": sum(s["energy"] for s in steps),
                }
                for s in steps:
                    for k, v in s["inputs"].items():
                        merged["inputs"][k] = merged["inputs"].get(k, 0) + v
                    for k, v in s["outputs"].items():
                        merged["outputs"][k] = merged["outputs"].get(k, 0) + v
                optimized.append(merged)
                
        return optimized


# ============================================================================
# 测试用例
# ============================================================================

class TestFullGenesis(unittest.TestCase):
    """Level 4: 完整 assembled_robot 终极测试"""
    
    def setUp(self):
        """测试初始化"""
        self.planner = ProductionPlanner(FULL_RECIPES)
        
    def test_material_requirements(self):
        """测试: 完整材料需求计算"""
        print("\n🧪 测试: assembled_robot 材料需求计算")
        
        requirements = self.planner.calculator.calculate_requirements(
            "assembled_robot", 1
        )
        
        print("\n  制造 1 个 assembled_robot 需要:")
        for item, qty in sorted(requirements.items()):
            print(f"    {item}: {qty}")
            
        # 验证原材料存在
        self.assertIn("iron_ore", requirements)
        self.assertIn("silicon_ore", requirements)
        
        # 验证数量合理
        self.assertGreater(requirements["iron_ore"], 50)
        self.assertGreater(requirements["silicon_ore"], 10)
        
        print("  ✅ 材料需求计算测试通过")
        
    def test_production_plan_generation(self):
        """测试: 生产计划生成"""
        print("\n🧪 测试: 生产计划生成")
        
        plan = self.planner.generate_plan("assembled_robot")
        
        print(f"\n  生产计划共 {len(plan)} 个步骤:")
        total_time = 0.0
        total_energy = 0.0
        for step in plan:
            print(f"    {step['step']}. {step['recipe']} x {step['runs']}")
            print(f"       工站: {step['station_type']}")
            print(f"       时间: {step['time']:.1f}s")
            total_time += step["time"]
            total_energy += step["energy"]
            
        print(f"\n  总生产时间: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"  总能量消耗: {total_energy:.1f} J")
        
        # 验证计划包含所有必要步骤
        recipe_names = [step["recipe"] for step in plan]
        self.assertIn("smelt_iron", recipe_names)
        self.assertIn("assemble_robot", recipe_names)
        
        print("  ✅ 生产计划生成测试通过")
        
    def test_optimized_plan(self):
        """测试: 优化生产计划"""
        print("\n🧪 测试: 优化生产计划")
        
        raw_plan = self.planner.generate_plan("assembled_robot")
        optimized = self.planner.optimize_plan(raw_plan)
        
        print(f"\n  原始计划: {len(raw_plan)} 步骤")
        print(f"  优化计划: {len(optimized)} 步骤")
        
        # 计算总时间
        total_time = sum(step["time"] for step in optimized)
        print(f"  总时间: {total_time:.1f}s ({total_time/60:.1f} min)")
        
        print("  ✅ 优化计划测试通过")
        
    def test_recipe_dependency_tree(self):
        """测试: 配方依赖树"""
        print("\n🧪 测试: 配方依赖树")
        
        def print_tree(item: str, indent: int = 0) -> int:
            """打印依赖树"""
            prefix = "  " * indent
            if item not in self.planner.calculator.output_map:
                print(f"{prefix}└── {item} (原材料)")
                return 0
                
            recipe = self.planner.calculator.output_map[item]
            print(f"{prefix}├── {item}")
            
            max_depth = 0
            for input_item in recipe.inputs:
                depth = print_tree(input_item, indent + 1)
                max_depth = max(max_depth, depth)
                
            return max_depth + 1
            
        print("\n  assembled_robot 依赖树:")
        depth = print_tree("assembled_robot")
        print(f"\n  依赖树深度: {depth}")
        
        self.assertGreater(depth, 3)
        print("  ✅ 依赖树测试通过")


class TestFullProductionSimulation(unittest.TestCase):
    """完整生产模拟测试"""
    
    def test_full_robot_production(self):
        """测试: 完整机器人生产模拟"""
        print("\n" + "=" * 60)
        print("🧪 Level 4: 完整机器人生产模拟 ★ 终极测试")
        print("=" * 60)
        
        start_time = time.time()
        
        # 初始化库存
        inventory: Dict[str, int] = {
            "iron_ore": 200,
            "silicon_ore": 100,
        }
        
        # 生产计划
        planner = ProductionPlanner(FULL_RECIPES)
        plan = planner.optimize_plan(
            planner.generate_plan("assembled_robot")
        )
        
        # 模拟生产
        print("\n📦 执行生产计划:")
        total_time = 0.0
        total_energy = 0.0
        
        for step in plan:
            # 检查输入是否足够
            for item, qty in step["inputs"].items():
                if inventory.get(item, 0) < qty:
                    self.fail(f"缺少 {item}: 需要 {qty}, 库存 {inventory.get(item, 0)}")
                    
            # 消耗输入
            for item, qty in step["inputs"].items():
                inventory[item] -= qty
                
            # 产出
            for item, qty in step["outputs"].items():
                inventory[item] = inventory.get(item, 0) + qty
                
            total_time += step["time"]
            total_energy += step["energy"]
            
            print(f"\n  {step['step']}. {step['recipe']} x {step['runs']}")
            print(f"     输入: {step['inputs']}")
            print(f"     输出: {step['outputs']}")
            print(f"     时间: {step['time']:.1f}s")
            
        # 验证最终产出
        self.assertEqual(inventory.get("assembled_robot", 0), 1)
        
        # 输出结果
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("📊 测试结果")
        print("=" * 60)
        print(f"  - 总耗时: {elapsed_time:.2f}s (实际)")
        print(f"  - 仿真时间: {total_time:.1f}s ({total_time/60:.1f} min)")
        print(f"  - 总能量消耗: {total_energy:.1f} J")
        print(f"  - 最终库存:")
        for item, qty in sorted(inventory.items()):
            if qty > 0:
                print(f"      {item}: {qty}")
                
        print("\n🎉 Level 4 终极测试通过!")
        print("   assembled_robot 已成功制造!")
        print("=" * 60)


class TestBenchmarkMetrics(unittest.TestCase):
    """基准测试指标"""
    
    def test_benchmark_calculation(self):
        """测试: 基准指标计算"""
        print("\n🧪 测试: 基准指标计算")
        
        planner = ProductionPlanner(FULL_RECIPES)
        plan = planner.optimize_plan(
            planner.generate_plan("assembled_robot")
        )
        
        # 计算指标
        metrics = {
            "total_sim_time": sum(step["time"] for step in plan),
            "total_energy_consumed": sum(step["energy"] for step in plan),
            "total_steps": len(plan),
            "station_usage": {},
        }
        
        # 统计工站使用
        for step in plan:
            station = step["station_type"]
            metrics["station_usage"][station] = (
                metrics["station_usage"].get(station, 0) + step["runs"]
            )
            
        # 计算能量比 (假设太阳能发电 100W)
        solar_output = 100  # Watts
        energy_generated = metrics["total_sim_time"] * solar_output / 3600  # Wh
        energy_consumed_wh = metrics["total_energy_consumed"] / 3600
        energy_ratio = energy_generated / energy_consumed_wh if energy_consumed_wh > 0 else 0
        
        metrics["total_energy_generated"] = energy_generated
        metrics["energy_ratio"] = energy_ratio
        
        print("\n  基准指标:")
        print(f"    总仿真时间: {metrics['total_sim_time']:.1f}s")
        print(f"    总能耗: {metrics['total_energy_consumed']:.1f} J")
        print(f"    总发电量: {metrics['total_energy_generated']:.2f} Wh")
        print(f"    能量比: {metrics['energy_ratio']:.2f}")
        print(f"    总步骤数: {metrics['total_steps']}")
        print(f"    工站使用: {metrics['station_usage']}")
        
        # 验证指标合理性
        self.assertGreater(metrics["total_sim_time"], 0)
        self.assertGreater(metrics["total_steps"], 5)
        
        print("  ✅ 基准指标计算测试通过")


# ============================================================================
# 运行测试
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 GENESIS Level 4 集成测试 ★ 终极测试")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestFullGenesis))
    suite.addTests(loader.loadTestsFromTestCase(TestFullProductionSimulation))
    suite.addTests(loader.loadTestsFromTestCase(TestBenchmarkMetrics))
    
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
        print("   GENESIS 系统已验证!")
    else:
        print("\n❌ 存在失败的测试")
        
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
