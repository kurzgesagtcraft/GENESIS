#!/usr/bin/env python3
"""
GENESIS 智能决策大脑测试脚本

测试 P6 阶段的所有模块:
- LLM 客户端
- 战略规划器
- 行为树框架
- 任务执行器
- 异常处理
- Dashboard
"""

import sys
import os
import argparse
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_llm_client():
    """测试 LLM 客户端"""
    print("\n" + "=" * 60)
    print("🧪 测试: LLM 客户端")
    print("=" * 60)
    
    from brain.llm_client import LLMClient, LLMConfig, LLMProvider
    
    # 使用 Mock 后端测试
    config = LLMConfig(provider=LLMProvider.MOCK)
    client = LLMClient(config)
    
    # 测试基本聊天
    response = client.chat("测试消息")
    assert response.content is not None
    assert response.model == "mock-model"
    print("  ✅ 基本聊天测试通过")
    
    # 测试 JSON 响应
    schema = {"type": "array", "items": {"type": "string"}}
    result = client.chat_json("列出5种水果", schema)
    assert isinstance(result, (dict, list))
    print("  ✅ JSON 响应测试通过")
    
    # 测试统计
    stats = client.get_stats()
    assert "total_tokens" in stats
    assert "call_count" in stats
    print("  ✅ 统计功能测试通过")
    
    print("✅ LLM 客户端测试通过")
    return True


def test_strategic_planner():
    """测试战略规划器"""
    print("\n" + "=" * 60)
    print("🧪 测试: 战略规划器")
    print("=" * 60)
    
    from brain.strategic_planner import TaskPlan, Task, StrategicPlanner
    from brain.llm_client import LLMClient, LLMConfig, LLMProvider
    
    # 创建测试数据
    tasks = [
        Task(task_id=1, type="mine", target="iron_ore", quantity=3, description="采集铁矿石"),
        Task(task_id=2, type="deliver_to_station", items=["iron_ore"] * 3, station="smelter", description="送往冶炼站"),
        Task(task_id=3, type="start_processing", station="smelter", recipe="smelt_iron", description="开始冶炼"),
    ]
    
    plan = TaskPlan(goal="iron_bar", tasks=tasks)
    
    # 测试 TaskPlan 方法
    assert plan.is_complete() == False
    next_task = plan.get_next_task()
    assert next_task is not None
    assert next_task.task_id == 1
    print("  ✅ TaskPlan 基本功能测试通过")
    
    # 测试 to_text
    text = plan.to_text()
    assert "Goal: iron_bar" in text
    print("  ✅ TaskPlan to_text 测试通过")
    
    # 测试 StrategicPlanner (使用 Mock)
    config = LLMConfig(provider=LLMProvider.MOCK)
    client = LLMClient(config)
    
    # Mock recipe_graph
    class MockRecipeGraph:
        def to_text(self):
            return "iron_ore -> iron_bar"
    
    def mock_world_state():
        return {
            "sim_time": 0,
            "battery_soc": 0.8,
            "mine_remaining": {"iron_ore": 100},
            "warehouse_inventory": {},
            "station_status": {"smelter": "idle"}
        }
    
    planner = StrategicPlanner(client, MockRecipeGraph(), mock_world_state)
    master_plan = planner.generate_master_plan("iron_bar")
    
    assert master_plan is not None
    assert len(master_plan.tasks) > 0
    print("  ✅ StrategicPlanner generate_master_plan 测试通过")
    
    print("✅ 战略规划器测试通过")
    return True


def test_behavior_tree():
    """测试行为树框架"""
    print("\n" + "=" * 60)
    print("🧪 测试: 行为树框架")
    print("=" * 60)
    
    from brain.behavior_tree import (
        Blackboard, BehaviorTree, SequenceNode, SelectorNode,
        ActionNode, ConditionNode, NodeStatus
    )
    
    # 测试 Blackboard
    bb = Blackboard()
    bb.set("test_key", "test_value")
    assert bb.get("test_key") == "test_value"
    assert bb.has("test_key")
    print("  ✅ Blackboard 测试通过")
    
    # 测试 ActionNode (需要设置 blackboard)
    def success_action(blackboard):
        return NodeStatus.SUCCESS
    
    action = ActionNode("TestAction", success_action)
    action.blackboard = bb  # 手动设置 blackboard
    status = action.tick()
    assert status == NodeStatus.SUCCESS
    print("  ✅ ActionNode 测试通过")
    
    # 测试 ConditionNode
    condition = ConditionNode("TestCondition", lambda bb: bb.get("test_key") == "test_value")
    condition.blackboard = bb  # 手动设置 blackboard
    status = condition.tick()
    assert status == NodeStatus.SUCCESS
    print("  ✅ ConditionNode 测试通过")
    
    # 测试 SequenceNode
    seq = SequenceNode("TestSequence", [
        ActionNode("A1", lambda bb: NodeStatus.SUCCESS),
        ActionNode("A2", lambda bb: NodeStatus.SUCCESS),
    ])
    status = seq.tick()
    assert status == NodeStatus.SUCCESS
    print("  ✅ SequenceNode 测试通过")
    
    # 测试 SelectorNode
    sel = SelectorNode("TestSelector", [
        ActionNode("S1", lambda bb: NodeStatus.FAILURE),
        ActionNode("S2", lambda bb: NodeStatus.SUCCESS),
    ])
    status = sel.tick()
    assert status == NodeStatus.SUCCESS
    print("  ✅ SelectorNode 测试通过")
    
    # 测试 BehaviorTree
    tree = BehaviorTree(seq, bb)
    status = tree.tick()
    assert status == NodeStatus.SUCCESS
    print("  ✅ BehaviorTree 测试通过")
    
    print("✅ 行为树框架测试通过")
    return True


def test_task_executor():
    """测试任务执行器"""
    print("\n" + "=" * 60)
    print("🧪 测试: 任务执行器")
    print("=" * 60)
    
    from brain.task_executor import TaskExecutor
    from brain.strategic_planner import TaskPlan, Task
    
    # Mock 对象
    class MockRobot:
        def get_battery_soc(self):
            return 0.8
        def get_base_pose(self):
            return (0.0, 0.0)
    
    class MockPerception:
        pass
    
    class MockNavigator:
        pass
    
    class MockSkillLibrary:
        pass
    
    class MockWorldManager:
        pass
    
    executor = TaskExecutor(
        MockRobot(), MockPerception(), MockNavigator(),
        MockSkillLibrary(), MockWorldManager()
    )
    
    # 创建测试计划
    tasks = [
        Task(task_id=1, type="mine", target="iron_ore", quantity=1),
        Task(task_id=2, type="charge"),
    ]
    plan = TaskPlan(goal="test", tasks=tasks)
    
    # 构建行为树
    tree = executor.build_tree_from_plan(plan)
    assert tree is not None
    assert tree.root is not None
    print("  ✅ build_tree_from_plan 测试通过")
    
    print("✅ 任务执行器测试通过")
    return True


def test_error_handler():
    """测试异常处理器"""
    print("\n" + "=" * 60)
    print("🧪 测试: 异常处理器")
    print("=" * 60)
    
    from brain.error_handler import ErrorHandler, ErrorType
    from brain.strategic_planner import StrategicPlanner
    from brain.llm_client import LLMClient, LLMConfig, LLMProvider
    
    # 创建 Mock planner
    config = LLMConfig(provider=LLMProvider.MOCK)
    client = LLMClient(config)
    
    class MockRecipeGraph:
        def to_text(self):
            return "test"
    
    def mock_world_state():
        return {}
    
    planner = StrategicPlanner(client, MockRecipeGraph(), mock_world_state)
    
    handler = ErrorHandler(planner)
    
    # 测试错误处理
    recovery = handler.handle_error(ErrorType.GRASP_FAILED, {"task_id": 1})
    assert recovery is not None
    assert "retry_grasp" in recovery.actions
    print("  ✅ handle_error 测试通过")
    
    # 测试错误统计
    summary = handler.get_error_summary()
    assert "grasp_failed" in summary
    print("  ✅ get_error_summary 测试通过")
    
    print("✅ 异常处理器测试通过")
    return True


def test_dashboard():
    """测试 Dashboard"""
    print("\n" + "=" * 60)
    print("🧪 测试: Dashboard")
    print("=" * 60)
    
    from brain.dashboard import Dashboard
    
    # Mock 对象
    class MockWorldManager:
        def get_world_state(self):
            return {
                "warehouse_inventory": {"iron_ore": 10},
                "station_status": {"smelter": "idle"},
                "energy_balance": 50.0
            }
    
    class MockRobot:
        def get_base_pose(self):
            return (1.0, 2.0)
        def get_battery_soc(self):
            return 0.75
        current_task = "mining"
        task_progress = 0.5
    
    dashboard = Dashboard(MockWorldManager(), MockRobot())
    
    # 测试更新
    state = dashboard.update()
    assert state is not None
    assert state.robot_battery == 0.75
    print("  ✅ update 测试通过")
    
    # 测试摘要
    summary = dashboard.get_summary()
    assert summary is not None
    assert "robot" in summary
    print("  ✅ get_summary 测试通过")
    
    # 测试文本渲染
    text = dashboard.render_text()
    assert "GENESIS Dashboard" in text
    print("  ✅ render_text 测试通过")
    
    print("✅ Dashboard 测试通过")
    return True


def run_all_tests(verbose: bool = False):
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("🧪 GENESIS 智能决策大脑测试")
    print("=" * 60)
    
    results = {}
    
    tests = [
        ("llm_client", test_llm_client),
        ("strategic_planner", test_strategic_planner),
        ("behavior_tree", test_behavior_tree),
        ("task_executor", test_task_executor),
        ("error_handler", test_error_handler),
        ("dashboard", test_dashboard),
    ]
    
    for name, test_fn in tests:
        try:
            result = test_fn()
            results[name] = "✅ 通过" if result else "❌ 失败"
        except Exception as e:
            results[name] = f"❌ 错误: {str(e)}"
            if verbose:
                import traceback
                traceback.print_exc()
    
    # 打印结果汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for name, result in results.items():
        print(f"{name}: {result}")
    
    all_passed = all("通过" in r for r in results.values())
    
    print("=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败")
    print("=" * 60)
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="GENESIS 智能决策大脑测试")
    parser.add_argument("--test", type=str, default="all", help="测试模块名称")
    parser.add_argument("--verbose", action="store_true", help="详细输出")
    
    args = parser.parse_args()
    
    if args.test == "all":
        success = run_all_tests(args.verbose)
        sys.exit(0 if success else 1)
    else:
        test_map = {
            "llm_client": test_llm_client,
            "strategic_planner": test_strategic_planner,
            "behavior_tree": test_behavior_tree,
            "task_executor": test_task_executor,
            "error_handler": test_error_handler,
            "dashboard": test_dashboard,
        }
        
        if args.test in test_map:
            try:
                test_map[args.test]()
                print(f"\n✅ {args.test} 测试通过")
            except Exception as e:
                print(f"\n❌ {args.test} 测试失败: {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                sys.exit(1)
        else:
            print(f"未知测试模块: {args.test}")
            print(f"可用模块: {list(test_map.keys())}")
            sys.exit(1)


if __name__ == "__main__":
    main()
