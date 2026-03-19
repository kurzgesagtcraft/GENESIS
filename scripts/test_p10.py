"""
GENESIS P10 拓展测试脚本

测试 P10 阶段的所有拓展模块：
- P10.1 多机器人协作
- P10.2 真实能源系统
- P10.3 真实制造系统
- P10.4 芯片制造模拟
- P10.5 自我修复机制
- P10.6 Sim-to-Real 桥接
"""

import sys
import time
import argparse
from typing import Dict, List, Any

# 添加项目根目录到路径
sys.path.insert(0, '.')


def test_multi_robot():
    """测试多机器人协作系统"""
    print("\n📦 测试模块: multi_robot")
    
    from genesis.control.multi_robot_manager import (
        MultiRobotManager, RobotStatus, TaskPriority,
        CooperativeTaskPlanner, CommunicationProtocol,
    )
    from genesis.robot.robot_interface import GenesisBot
    
    # 创建多机器人管理器
    manager = MultiRobotManager(min_separation=1.0, enable_communication=True)
    
    # 创建模拟机器人
    robot1 = GenesisBot(name="robot_001")
    robot2 = GenesisBot(name="robot_002")
    
    # 注册机器人
    rid1 = manager.register_robot(robot1, zone="zone_a")
    rid2 = manager.register_robot(robot2, zone="zone_b")
    
    print(f"  ✅ 注册机器人: {rid1}, {rid2}")
    
    # 添加任务
    task1 = manager.add_task("mine", "iron_ore", TaskPriority.NORMAL)
    task2 = manager.add_task("transport", "smelter", TaskPriority.HIGH)
    
    print(f"  ✅ 添加任务: {task1}, {task2}")
    
    # 预约区域
    reserved = manager.reserve_zone("mine_iron", rid1, 60.0)
    print(f"  ✅ 区域预约: {reserved}")
    
    # 更新管理器
    manager.update(1.0)
    
    # 获取状态
    status = manager.get_all_status()
    print(f"  ✅ 获取状态: {len(status['robots'])} 机器人")
    
    # 测试协作任务规划器
    planner = CooperativeTaskPlanner(manager)
    task_ids = planner.plan_parallel_mining("iron_ore", 10, ["mine_iron", "mine_silicon"])
    print(f"  ✅ 并行采矿任务: {len(task_ids)} 个任务")
    
    # 获取摘要
    summary = manager.get_summary()
    print(f"  ✅ 管理器摘要: {summary}")
    
    print("✅ 多机器人协作系统测试通过")
    return True


def test_realistic_energy():
    """测试真实能源系统"""
    print("\n📦 测试模块: realistic_energy")
    
    from genesis.world.realistic_energy import (
        RealisticEnergyManager, DayNightCycle, WeatherModel,
        WeatherCondition, SolarArray, WindTurbine,
        BatteryWithDegradation, BatteryHealthState,
    )
    
    # 创建日夜循环
    day_night = DayNightCycle(
        day_length_hours=24.0,
        sunrise_hour=6.0,
        sunset_hour=18.0,
    )
    
    # 测试太阳位置计算
    elevation, azimuth = day_night.get_sun_position(12.0)  # 正午
    print(f"  ✅ 正午太阳位置: 高度角={elevation:.1f}°, 方位角={azimuth:.1f}°")
    
    # 测试日照因子
    daylight = day_night.get_daylight_factor(12.0)
    print(f"  ✅ 正午日照因子: {daylight:.3f}")
    
    # 创建天气模型
    weather = WeatherModel()
    weather.current_condition = WeatherCondition.CLEAR
    
    efficiency = weather.get_solar_efficiency()
    print(f"  ✅ 晴天太阳能效率: {efficiency:.3f}")
    
    # 更新天气
    weather.current_condition = WeatherCondition.CLOUDY
    weather.update(1.0)
    efficiency_cloudy = weather.get_solar_efficiency()
    print(f"  ✅ 多云太阳能效率: {efficiency_cloudy:.3f}")
    
    # 创建电池退化模型
    battery = BatteryWithDegradation(capacity_wh=500.0)
    
    # 模拟充放电循环
    for _ in range(100):
        battery.charge(100.0, 3600.0)
        battery.discharge(100.0, 3600.0)
    
    print(f"  ✅ 电池循环后健康度: {battery.health_percentage:.1f}%")
    print(f"  ✅ 电池健康状态: {battery.health_state.value}")
    
    # 创建能源管理器
    energy_manager = RealisticEnergyManager()
    
    # 模拟一天
    for _ in range(24 * 60):  # 24小时，每分钟更新
        energy_manager.update(60.0)
    
    status = energy_manager.get_generation_status()
    print(f"  ✅ 太阳能发电: {status['totals']['solar_generated_wh']:.1f} Wh")
    print(f"  ✅ 风能发电: {status['totals']['wind_generated_wh']:.1f} Wh")
    
    # 获取能量平衡
    balance = energy_manager.get_energy_balance()
    print(f"  ✅ 能量平衡: 净值={balance['net_balance_wh']:.1f} Wh")
    
    # 预测未来24小时
    forecast = energy_manager.forecast(24.0)
    total_predicted = sum(f['total_output_w'] for f in forecast)
    print(f"  ✅ 24小时预测总发电: {total_predicted:.1f} W")
    
    print("✅ 真实能源系统测试通过")
    return True


def test_realistic_manufacturing():
    """测试真实制造系统"""
    print("\n📦 测试模块: realistic_manufacturing")
    
    from workstation.realistic_manufacturing import (
        RealisticAssembler, QualityInspector, ToolChanger,
        ProductSpecification, AssemblyOperation, ToolType,
        QualityGrade, WearSimulator, SelfRepairSystem,
    )
    
    # 创建工具更换器
    tool_changer = ToolChanger()
    print(f"  ✅ 工具更换器初始化: {len(tool_changer.get_available_tools())} 种工具")
    
    # 更换工具
    tool_changer.change_tool(ToolType.SCREWDRIVER)
    current = tool_changer.get_current_tool()
    print(f"  ✅ 当前工具: {current.spec.name if current else 'None'}")
    
    # 创建质量检测器
    inspector = QualityInspector(defect_rate=0.05)
    
    # 创建产品规格
    product = ProductSpecification(
        name="test_assembly",
        target_dimensions=(100.0, 50.0, 25.0),
        tolerance_mm=0.5,
        required_operations=["align", "insert", "screw", "verify"],
    )
    
    # 执行多次检测
    for i in range(10):
        result = inspector.inspect(product, assembly_quality=95.0 - i * 2)
    
    stats = inspector.get_statistics()
    print(f"  ✅ 质量检测统计: 通过率={stats['pass_rate']:.1%}, 平均分={stats['average_score']:.1f}")
    
    # 创建装配站
    assembler = RealisticAssembler(name="test_assembler", defect_rate=0.05)
    
    # 开始装配
    assembler.start_assembly(product)
    print(f"  ✅ 开始装配: {product.name}")
    
    # 执行操作
    operations = assembler.get_required_operations()
    for op in operations:
        # 更换合适的工具
        if op.required_tool != ToolType.GRIPPER:
            tool_changer.change_tool(op.required_tool)
        assembler.execute_operation(op)
    
    # 完成装配
    result = assembler.complete_assembly()
    print(f"  ✅ 装配完成: 等级={result.grade.value}, 分数={result.score:.1f}")
    
    # 创建磨损模拟器
    wear_sim = WearSimulator()
    wear_sim.register_component("joint_1", "joint", wear_rate=0.001)
    wear_sim.register_component("motor_1", "motor", wear_rate=0.002)
    
    # 模拟磨损
    for _ in range(100):
        wear_sim.apply_wear("joint_1", 1.0)
        wear_sim.apply_wear("motor_1", 1.0)
    
    status = wear_sim.get_all_status()
    print(f"  ✅ 磨损状态: {status['total_wear_events']} 次磨损事件")
    
    print("✅ 真实制造系统测试通过")
    return True


def test_semiconductor_fab():
    """测试芯片制造模拟"""
    print("\n📦 测试模块: semiconductor_fab")
    
    from workstation.semiconductor_fab import (
        SemiconductorFab, Wafer, WaferSpec, ProcessStage,
        ChipManufacturingWorkflow,
    )
    
    # 创建半导体制造厂
    fab = SemiconductorFab(name="genesis_fab")
    print(f"  ✅ 制造厂初始化: {len(fab._stations)} 个工艺站")
    
    # 创建晶圆
    wafer = fab.create_wafer()
    print(f"  ✅ 创建晶圆: {wafer.spec.wafer_id}")
    
    # 处理晶圆
    fab.process_wafer(wafer)
    
    # 模拟工艺过程
    for _ in range(100):
        fab.update(10.0)  # 每次10秒
    
    # 获取状态
    status = fab.get_status()
    print(f"  ✅ 制造厂状态: {status['wafers_completed']} 个晶圆完成")
    
    # 获取良率统计
    yield_stats = fab.get_yield_statistics()
    if yield_stats['total_wafers'] > 0:
        print(f"  ✅ 良率统计: 平均良率={yield_stats['average_yield']:.1f}%")
    
    # 创建工作流
    workflow = ChipManufacturingWorkflow(fab)
    transfers = workflow.plan_transfers()
    print(f"  ✅ 工作流规划: {len(transfers)} 个转移任务")
    
    print("✅ 芯片制造模拟测试通过")
    return True


def test_self_repair():
    """测试自我修复机制"""
    print("\n📦 测试模块: self_repair")
    
    from genesis.control.self_repair import (
        SelfRepairSystem, HealthMonitor, RepairCoordinator,
        ComponentType, HealthStatus, RepairPriority,
    )
    
    # 创建健康监控器
    monitor = HealthMonitor()
    
    # 注册组件
    monitor.register_component("joint_1", ComponentType.JOINT)
    monitor.register_component("motor_1", ComponentType.MOTOR)
    monitor.register_component("gripper_left", ComponentType.GRIPPER)
    print(f"  ✅ 注册组件: {len(monitor._components)} 个")
    
    # 模拟磨损
    for _ in range(50):
        monitor.update_health("joint_1", -0.5, operation_count=1)
        monitor.update_health("motor_1", -0.3, operation_count=1)
    
    # 检查健康状态
    status = monitor.get_health_status("joint_1")
    print(f"  ✅ 关节健康状态: {status.value}")
    
    # 获取需要修复的组件
    needs_repair = monitor.get_components_needing_repair()
    print(f"  ✅ 需要修复: {len(needs_repair)} 个组件")
    
    # 创建修复协调器
    coordinator = RepairCoordinator(monitor)
    
    # 创建修复任务
    if needs_repair:
        component_id, priority = needs_repair[0]
        task = coordinator.create_repair_task(component_id, priority)
        print(f"  ✅ 创建修复任务: {task.task_id}")
        
        # 分配任务
        coordinator.assign_repair(task.task_id, "robot_001")
        
        # 完成修复
        coordinator.complete_repair(task.task_id, health_restored=95.0)
        print(f"  ✅ 完成修复任务")
    
    # 创建完整的自我修复系统
    repair_system = SelfRepairSystem()
    
    # 注册组件
    repair_system.register_component("joint_1", ComponentType.JOINT)
    repair_system.register_component("motor_1", ComponentType.MOTOR)
    
    # 更新系统
    repair_system.update(60.0, {"joint_1": 10, "motor_1": 5})
    
    # 获取系统状态
    status = repair_system.get_system_status()
    print(f"  ✅ 系统状态: {status['health_monitor']['total_components']} 个组件")
    
    # 检查预防性维护
    preventive = repair_system.check_preventive_maintenance()
    print(f"  ✅ 预防性维护: {len(preventive)} 个组件")
    
    print("✅ 自我修复机制测试通过")
    return True


def test_sim_to_real():
    """测试 Sim-to-Real 桥接"""
    print("\n📦 测试模块: sim_to_real")
    
    from genesis.control.self_repair import SimToRealBridge
    
    # 创建桥接
    bridge = SimToRealBridge()
    
    # 配置域随机化
    bridge.configure_domain_randomization(
        physics_variance=0.1,
        visual_variance=0.15,
        sensor_noise=0.05,
    )
    print(f"  ✅ 配置域随机化")
    
    # 应用域随机化
    original_params = {
        "mass": 10.0,
        "friction": 0.7,
        "position": [1.0, 2.0, 3.0],
    }
    
    randomized = bridge.apply_domain_randomization(original_params)
    print(f"  ✅ 原始参数: mass={original_params['mass']}")
    print(f"  ✅ 随机化参数: mass={randomized['mass']:.2f}")
    
    # 估计现实差距
    sim_performance = {"success_rate": 0.95, "precision": 0.01, "speed": 1.0}
    gap = bridge.estimate_reality_gap(sim_performance)
    print(f"  ✅ 现实差距估计: 成功率差距={gap['success_rate_gap']:.1%}")
    
    # 生成迁移策略
    strategy = bridge.generate_transfer_strategy()
    print(f"  ✅ 迁移策略: {len(strategy['recommendations'])} 条建议")
    
    for rec in strategy['recommendations']:
        print(f"     - {rec['type']}: {rec['description']}")
    
    # 获取状态
    status = bridge.get_status()
    print(f"  ✅ 桥接状态: {status}")
    
    print("✅ Sim-to-Real 桥接测试通过")
    return True


def run_all_tests(verbose: bool = False):
    """运行所有测试"""
    print("=" * 60)
    print("🧪 GENESIS P10 拓展测试")
    print("=" * 60)
    
    results = {}
    
    # 运行各模块测试
    test_functions = [
        ("multi_robot", test_multi_robot),
        ("realistic_energy", test_realistic_energy),
        ("realistic_manufacturing", test_realistic_manufacturing),
        ("semiconductor_fab", test_semiconductor_fab),
        ("self_repair", test_self_repair),
        ("sim_to_real", test_sim_to_real),
    ]
    
    for name, test_func in test_functions:
        try:
            success = test_func()
            results[name] = success
        except Exception as e:
            print(f"❌ {name} 测试失败: {e}")
            results[name] = False
    
    # 打印汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
    
    print("=" * 60)
    print(f"总计: {total} 个测试")
    print(f"通过: {passed} 个")
    print(f"失败: {total - passed} 个")
    print("=" * 60)
    
    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败")
    
    return passed == total


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GENESIS P10 拓展测试")
    parser.add_argument(
        "--test",
        type=str,
        default="all",
        choices=["all", "multi_robot", "realistic_energy", "realistic_manufacturing",
                 "semiconductor_fab", "self_repair", "sim_to_real"],
        help="要运行的测试模块",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出",
    )
    
    args = parser.parse_args()
    
    if args.test == "all":
        success = run_all_tests(args.verbose)
    else:
        test_map = {
            "multi_robot": test_multi_robot,
            "realistic_energy": test_realistic_energy,
            "realistic_manufacturing": test_realistic_manufacturing,
            "semiconductor_fab": test_semiconductor_fab,
            "self_repair": test_self_repair,
            "sim_to_real": test_sim_to_real,
        }
        
        test_func = test_map.get(args.test)
        if test_func:
            try:
                success = test_func()
                print(f"\n✅ {args.test} 测试通过")
            except Exception as e:
                print(f"\n❌ {args.test} 测试失败: {e}")
                success = False
        else:
            print(f"未知测试模块: {args.test}")
            success = False
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
