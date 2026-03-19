"""
GENESIS Level 1 Integration Test: 单配方闭环测试

场景: 采3个iron_ore → 送到smelter → 取回2个iron_bar → 存入仓库
预期时间: < 5分钟仿真时间

测试目标:
- 验证导航系统正确性
- 验证抓取技能可用性
- 验证工站投料/取料流程
- 验证仓储操作
"""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import time

# 添加项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from genesis.world import (
    WorldManager,
    ItemRegistry,
    RecipeRegistry,
    MineZone,
    Warehouse,
    ChargingDock,
)
from genesis.robot import GenesisBot, Battery
from genesis.control import Navigator, NavigationStatus
from workstation import (
    StationManager,
    StationInterface,
    Smelter,
    SmelterConfig,
)
from brain import (
    TaskPlan,
    Task,
    Blackboard,
    NodeStatus,
)


# ============================================================================
# Mock 类 (用于无仿真环境测试)
# ============================================================================

class MockSimContext:
    """Mock 仿真上下文"""
    def __init__(self):
        self.sim_time = 0.0
        self.physics_dt = 0.002
        
    def step(self):
        self.sim_time += self.physics_dt
        
    def get_time(self):
        return self.sim_time


class MockRobot:
    """Mock 机器人"""
    def __init__(self):
        self.position = [0.0, 0.0]
        self.yaw = 0.0
        self.battery_soc = 0.95
        self.carrying_items: List[str] = []
        
    def get_base_pose(self):
        return (self.position, self.yaw)
        
    def get_battery_soc(self):
        return self.battery_soc
        
    def move_to(self, target_pos, target_yaw):
        self.position = list(target_pos)
        self.yaw = target_yaw
        return True
        
    def grasp(self, item_id: str):
        if item_id not in self.carrying_items:
            self.carrying_items.append(item_id)
        return True
        
    def release(self, item_id: str):
        if item_id in self.carrying_items:
            self.carrying_items.remove(item_id)
        return True


class MockNavigator:
    """Mock 导航器"""
    def __init__(self):
        self.current_zone = "spawn"
        
    async def navigate_to_zone(self, zone_name: str) -> bool:
        await asyncio.sleep(0.1)  # 模拟导航时间
        self.current_zone = zone_name
        return True


class MockMineZone:
    """Mock 矿区"""
    def __init__(self, name: str, resource_type: str, remaining: int):
        self.name = name
        self.resource_type = resource_type
        self.remaining = remaining
        self.position = [5.0, 35.0, 0.0]
        
    def extract(self, quantity: int = 1) -> Optional[str]:
        if self.remaining >= quantity:
            self.remaining -= quantity
            return f"{self.resource_type}_{id(self)}"
        return None


class MockWarehouse:
    """Mock 仓库"""
    def __init__(self):
        self.inventory: Dict[str, int] = {}
        
    def store_item(self, item_type: str, quantity: int = 1) -> bool:
        self.inventory[item_type] = self.inventory.get(item_type, 0) + quantity
        return True
        
    def get_inventory(self) -> Dict[str, int]:
        return dict(self.inventory)


class MockSmelter:
    """Mock 冶炼站"""
    def __init__(self):
        self.state = "idle"
        self.input_buffer: Dict[str, int] = {}
        self.output_buffer: List[str] = []
        self.process_timer = 0.0
        self.recipe = {
            "name": "smelt_iron",
            "inputs": {"iron_ore": 3},
            "outputs": {"iron_bar": 2},
            "process_time": 30.0,
        }
        
    def receive_input(self, item_type: str, quantity: int = 1) -> bool:
        self.input_buffer[item_type] = self.input_buffer.get(item_type, 0) + quantity
        
        # 检查是否可以开始加工
        if self._can_start():
            self.state = "processing"
            self.process_timer = self.recipe["process_time"]
            # 消耗输入
            for k, v in self.recipe["inputs"].items():
                self.input_buffer[k] -= v
        return True
        
    def _can_start(self) -> bool:
        for k, v in self.recipe["inputs"].items():
            if self.input_buffer.get(k, 0) < v:
                return False
        return True
        
    def step(self, dt: float):
        if self.state == "processing":
            self.process_timer -= dt
            if self.process_timer <= 0:
                # 生产完成
                for k, v in self.recipe["outputs"].items():
                    for _ in range(v):
                        self.output_buffer.append(k)
                self.state = "done"
                
    def collect_output(self) -> Optional[str]:
        if self.output_buffer:
            return self.output_buffer.pop(0)
        return None
        
    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state,
            "input_buffer": dict(self.input_buffer),
            "output_count": len(self.output_buffer),
            "process_remaining": max(0, self.process_timer),
        }


# ============================================================================
# 测试用例
# ============================================================================

class TestSingleRecipe(unittest.TestCase):
    """Level 1: 单配方闭环测试"""
    
    def setUp(self):
        """测试初始化"""
        self.sim = MockSimContext()
        self.robot = MockRobot()
        self.navigator = MockNavigator()
        self.mine = MockMineZone("mine_iron", "iron_ore", 500)
        self.warehouse = MockWarehouse()
        self.smelter = MockSmelter()
        
    def test_mine_iron_ore(self):
        """测试: 采矿"""
        print("\n📦 测试: 采矿")
        
        # 导航到矿区
        success = asyncio.run(self.navigator.navigate_to_zone("mine_iron"))
        self.assertTrue(success, "导航到矿区失败")
        
        # 采矿
        for i in range(3):
            item = self.mine.extract(1)
            self.assertIsNotNone(item, f"采矿第 {i+1} 次失败")
            self.robot.grasp(item)
            
        # 验证
        self.assertEqual(len(self.robot.carrying_items), 3, "机器人应携带3个矿石")
        self.assertEqual(self.mine.remaining, 497, "矿区应剩余497个矿石")
        print("  ✅ 采矿测试通过")
        
    def test_deliver_to_smelter(self):
        """测试: 投料到冶炼站"""
        print("\n📦 测试: 投料到冶炼站")
        
        # 模拟机器人携带3个铁矿石
        for i in range(3):
            self.robot.carrying_items.append(f"iron_ore_{i}")
            
        # 导航到冶炼站
        success = asyncio.run(self.navigator.navigate_to_zone("smelter"))
        self.assertTrue(success, "导航到冶炼站失败")
        
        # 投料
        items_to_deliver = self.robot.carrying_items.copy()
        for item in items_to_deliver:
            self.smelter.receive_input("iron_ore", 1)
            self.robot.release(item)
            
        # 验证
        self.assertEqual(len(self.robot.carrying_items), 0, "机器人应无携带物品")
        self.assertEqual(self.smelter.input_buffer.get("iron_ore", 0), 3, "冶炼站应有3个铁矿石")
        print("  ✅ 投料测试通过")
        
    def test_smelting_process(self):
        """测试: 冶炼过程"""
        print("\n📦 测试: 冶炼过程")
        
        # 投入材料
        self.smelter.receive_input("iron_ore", 3)
        
        # 验证开始加工
        self.assertEqual(self.smelter.state, "processing", "冶炼站应处于加工状态")
        
        # 模拟加工过程
        total_time = 0.0
        while self.smelter.state == "processing":
            self.smelter.step(1.0)
            total_time += 1.0
            if total_time > 60:  # 超时保护
                break
                
        # 验证加工完成
        self.assertEqual(self.smelter.state, "done", "冶炼站应完成加工")
        self.assertEqual(len(self.smelter.output_buffer), 2, "应有2个铁锭产出")
        print(f"  ✅ 冶炼测试通过 (耗时 {total_time}s)")
        
    def test_collect_and_store(self):
        """测试: 取料并存储"""
        print("\n📦 测试: 取料并存储")
        
        # 模拟冶炼站有产出
        self.smelter.output_buffer = ["iron_bar", "iron_bar"]
        self.smelter.state = "done"
        
        # 取料
        collected = []
        while True:
            item = self.smelter.collect_output()
            if item is None:
                break
            collected.append(item)
            self.robot.grasp(item)
            
        # 验证取料
        self.assertEqual(len(collected), 2, "应取出2个铁锭")
        
        # 导航到仓库
        success = asyncio.run(self.navigator.navigate_to_zone("warehouse"))
        self.assertTrue(success, "导航到仓库失败")
        
        # 存储
        for item in self.robot.carrying_items:
            self.warehouse.store_item("iron_bar", 1)
            
        # 验证存储
        self.assertEqual(
            self.warehouse.inventory.get("iron_bar", 0), 2,
            "仓库应有2个铁锭"
        )
        print("  ✅ 取料存储测试通过")
        
    def test_full_single_recipe_flow(self):
        """测试: 完整单配方闭环"""
        print("\n" + "=" * 60)
        print("🧪 Level 1: 完整单配方闭环测试")
        print("=" * 60)
        
        start_time = time.time()
        
        # Step 1: 采矿
        print("\n📦 步骤 1: 采矿")
        asyncio.run(self.navigator.navigate_to_zone("mine_iron"))
        for i in range(3):
            item = self.mine.extract(1)
            self.robot.grasp(item)
        print(f"  - 机器人携带: {len(self.robot.carrying_items)} 个矿石")
        
        # Step 2: 投料
        print("\n📦 步骤 2: 投料到冶炼站")
        asyncio.run(self.navigator.navigate_to_zone("smelter"))
        for item in self.robot.carrying_items.copy():
            self.smelter.receive_input("iron_ore", 1)
            self.robot.release(item)
        print(f"  - 冶炼站状态: {self.smelter.get_status()}")
        
        # Step 3: 等待冶炼
        print("\n⏳ 步骤 3: 等待冶炼完成...")
        process_time = 0.0
        while self.smelter.state != "done":
            self.smelter.step(1.0)
            process_time += 1.0
            if process_time > 60:
                break
        print(f"  - 冶炼耗时: {process_time}s")
        
        # Step 4: 取料
        print("\n📦 步骤 4: 取出铁锭")
        while True:
            item = self.smelter.collect_output()
            if item is None:
                break
            self.robot.grasp(item)
        print(f"  - 机器人携带: {len(self.robot.carrying_items)} 个铁锭")
        
        # Step 5: 存储
        print("\n📦 步骤 5: 存入仓库")
        asyncio.run(self.navigator.navigate_to_zone("warehouse"))
        for item in self.robot.carrying_items.copy():
            self.warehouse.store_item("iron_bar", 1)
            self.robot.release(item)
        print(f"  - 仓库库存: {self.warehouse.get_inventory()}")
        
        # 验证
        elapsed_time = time.time() - start_time
        print("\n" + "=" * 60)
        print("📊 测试结果")
        print("=" * 60)
        print(f"  - 总耗时: {elapsed_time:.2f}s (实际)")
        print(f"  - 仿真时间: {process_time + 0.3:.1f}s")
        print(f"  - 最终库存: {self.warehouse.get_inventory()}")
        
        # 断言
        self.assertEqual(
            self.warehouse.inventory.get("iron_bar", 0), 2,
            "最终应有2个铁锭"
        )
        
        print("\n✅ Level 1 单配方闭环测试通过!")
        print("=" * 60)


class TestSingleRecipeIntegration(unittest.TestCase):
    """集成测试: 使用真实模块"""
    
    def test_task_plan_parsing(self):
        """测试: 任务计划解析"""
        print("\n🧪 测试: 任务计划解析")
        
        # 创建测试任务计划 JSON
        plan_json = {
            "goal": "iron_bar",
            "tasks": [
                {
                    "task_id": 1,
                    "type": "mine",
                    "description": "采矿",
                    "target": "iron_ore",
                    "quantity": 3,
                },
                {
                    "task_id": 2,
                    "type": "deliver_to_station",
                    "description": "投料",
                    "items": ["iron_ore", "iron_ore", "iron_ore"],
                    "station": "smelter",
                },
                {
                    "task_id": 3,
                    "type": "wait_for_processing",
                    "description": "等待冶炼",
                    "station": "smelter",
                    "recipe": "smelt_iron",
                },
                {
                    "task_id": 4,
                    "type": "collect_from_station",
                    "description": "取料",
                    "station": "smelter",
                },
                {
                    "task_id": 5,
                    "type": "store",
                    "description": "存储",
                    "item_type": "iron_bar",
                },
            ]
        }
        
        # 解析
        plan = TaskPlan.parse(plan_json)
        
        # 验证
        self.assertEqual(plan.goal, "iron_bar")
        self.assertEqual(len(plan.tasks), 5)
        self.assertEqual(plan.tasks[0].type, "mine")
        self.assertEqual(plan.tasks[0].quantity, 3)
        
        print("  ✅ 任务计划解析测试通过")
        
    def test_blackboard_operations(self):
        """测试: 黑板操作"""
        print("\n🧪 测试: 黑板操作")
        
        blackboard = Blackboard()
        
        # 设置数据
        blackboard.set("current_task", "mine")
        blackboard.set("task_progress", 0.5)
        blackboard.set("inventory", {"iron_ore": 3})
        
        # 获取数据
        self.assertEqual(blackboard.get("current_task"), "mine")
        self.assertEqual(blackboard.get("task_progress"), 0.5)
        self.assertEqual(blackboard.get("inventory"), {"iron_ore": 3})
        
        # 检查存在
        self.assertTrue(blackboard.has("current_task"))
        self.assertFalse(blackboard.has("nonexistent"))
        
        # 清除
        blackboard.clear("current_task")
        self.assertFalse(blackboard.has("current_task"))
        
        print("  ✅ 黑板操作测试通过")


# ============================================================================
# 运行测试
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 GENESIS Level 1 集成测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestSingleRecipe))
    suite.addTests(loader.loadTestsFromTestCase(TestSingleRecipeIntegration))
    
    # 运行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
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
