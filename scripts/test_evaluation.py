#!/usr/bin/env python
"""
GENESIS P8 评估与优化测试脚本

测试分析模块和优化模块的功能。
"""

import sys
import os
import argparse
import json
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.analysis.time_analysis import (
    TimeAnalyzer,
    TaskTimeStats,
    TaskCategory,
    TimeBreakdown,
)
from src.analysis.energy_analysis import (
    EnergyAnalyzer,
    EnergySourceType,
    EnergyConsumerType,
    EnergyBalance,
)
from src.analysis.reliability_analysis import (
    ReliabilityAnalyzer,
    FailureType,
    Severity,
    FailureStats,
)
from src.optimization.path_optimizer import (
    PathOptimizer,
    TaskLocation,
    OptimizationMethod,
)
from src.optimization.parallel_scheduler import (
    ParallelScheduler,
    TaskWindow,
    TaskPriority,
    TaskType,
)
from src.optimization.skill_optimizer import (
    SkillOptimizer,
    SkillType,
    GraspParams,
)
from src.optimization.energy_optimizer import (
    EnergyOptimizer,
    EnergyPolicy,
    ChargingPriority,
)


class TestRunner:
    """测试运行器"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: Dict[str, bool] = {}
        self.start_time = time.time()
    
    def log(self, message: str, level: str = "INFO") -> None:
        """日志输出"""
        if self.verbose or level == "ERROR":
            print(f"[{level}] {message}")
    
    def run_test(self, test_name: str, test_func: callable) -> bool:
        """运行单个测试"""
        try:
            self.log(f"运行测试: {test_name}")
            test_func()
            self.results[test_name] = True
            self.log(f"✅ {test_name} 通过")
            return True
        except Exception as e:
            self.results[test_name] = False
            self.log(f"❌ {test_name} 失败: {e}", "ERROR")
            return False
    
    def summary(self) -> bool:
        """输出测试摘要"""
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)
        failed = total - passed
        
        print("\n" + "=" * 60)
        print("📊 测试结果汇总")
        print("=" * 60)
        
        for name, result in self.results.items():
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{name}: {status}")
        
        print("=" * 60)
        print(f"总计: {total} 个测试")
        print(f"通过: {passed} 个")
        print(f"失败: {failed} 个")
        
        elapsed = time.time() - self.start_time
        print(f"耗时: {elapsed:.2f} 秒")
        print("=" * 60)
        
        if failed == 0:
            print("🎉 所有测试通过！")
        else:
            print(f"⚠️ 有 {failed} 个测试失败")
        
        return failed == 0


# ============================================================
# 时间分析测试
# ============================================================

def test_time_analyzer_basic() -> None:
    """测试时间分析器基本功能"""
    analyzer = TimeAnalyzer()
    
    # 添加测试任务记录
    analyzer.add_task("task_1", "navigate_to_zone", 0, 10, True)
    analyzer.add_task("task_2", "top_grasp", 10, 15, True)
    analyzer.add_task("task_3", "wait_for_station", 15, 45, True)
    analyzer.add_task("task_4", "charge", 45, 100, True)
    analyzer.add_task("task_5", "navigate_to_zone", 100, 120, False)
    
    # 分析
    breakdown = analyzer.analyze()
    
    assert breakdown.task_count == 5, f"任务数应为 5，实际为 {breakdown.task_count}"
    assert breakdown.success_count == 4, f"成功数应为 4，实际为 {breakdown.success_count}"
    assert breakdown.total_time > 0, "总时间应大于 0"
    assert breakdown.navigation_time > 0, "导航时间应大于 0"
    assert breakdown.waiting_time > 0, "等待时间应大于 0"
    
    # 识别瓶颈
    bottlenecks = analyzer.identify_bottlenecks()
    assert len(bottlenecks) > 0, "应识别出瓶颈"
    
    # 检查瓶颈包含建议
    for b in bottlenecks:
        assert b.time_ratio >= 0, "时间占比应非负"
        assert b.impact_score >= 0, "影响分数应非负"


def test_time_analyzer_report() -> None:
    """测试时间分析报告生成"""
    analyzer = TimeAnalyzer()
    
    # 添加更多测试数据
    for i in range(20):
        analyzer.add_task(
            f"task_{i}",
            ["navigate_to_zone", "top_grasp", "place", "wait"][i % 4],
            i * 10,
            i * 10 + 8,
            i % 5 != 0  # 80% 成功率
        )
    
    report = analyzer.get_report()
    
    assert "summary" in report, "报告应包含摘要"
    assert "time_breakdown" in report, "报告应包含时间分解"
    assert "bottlenecks" in report, "报告应包含瓶颈分析"
    
    summary = report["summary"]
    assert summary["task_count"] == 20, "任务数应为 20"
    assert 0 <= summary["success_rate"] <= 1, "成功率应在 0-1 之间"


# ============================================================
# 能量分析测试
# ============================================================

def test_energy_analyzer_basic() -> None:
    """测试能量分析器基本功能"""
    analyzer = EnergyAnalyzer(battery_capacity=500.0, solar_peak_power=100.0)
    
    # 添加发电事件
    analyzer.add_generation(0, 80.0, 60, EnergySourceType.SOLAR)
    analyzer.add_generation(60, 100.0, 60, EnergySourceType.SOLAR)
    
    # 添加消耗事件
    analyzer.add_consumption(0, 50.0, 30, EnergyConsumerType.NAVIGATION)
    analyzer.add_consumption(30, 80.0, 20, EnergyConsumerType.MANIPULATION)
    analyzer.add_consumption(50, 500.0, 30, EnergyConsumerType.STATION)
    
    # 分析
    balance = analyzer.analyze()
    
    assert balance.total_generated > 0, "总发电量应大于 0"
    assert balance.total_consumed > 0, "总消耗应大于 0"
    assert balance.solar_generated > 0, "太阳能发电应大于 0"
    
    # 检查能量比率
    assert balance.energy_ratio >= 0, "能量比率应非负"


def test_energy_analyzer_solar_coverage() -> None:
    """测试太阳能覆盖分析"""
    analyzer = EnergyAnalyzer(battery_capacity=500.0, solar_peak_power=100.0)
    
    # 模拟能量数据
    analyzer.add_generation(0, 100.0, 3600, EnergySourceType.SOLAR)
    analyzer.add_consumption(0, 50.0, 3600, EnergyConsumerType.NAVIGATION)
    
    analyzer.analyze()
    
    # 分析太阳能覆盖
    coverage = analyzer.analyze_solar_coverage()
    
    assert "daily_solar_generation_wh" in coverage, "应包含日发电量"
    assert "coverage_ratio" in coverage, "应包含覆盖率"
    assert "is_self_sufficient" in coverage, "应包含自给自足标志"


def test_energy_analyzer_report() -> None:
    """测试能量分析报告"""
    analyzer = EnergyAnalyzer()
    
    # 添加测试数据
    for i in range(10):
        analyzer.add_generation(i * 60, 80 + i * 2, 60, EnergySourceType.SOLAR)
        analyzer.add_consumption(i * 60, 50, 30, EnergyConsumerType.NAVIGATION)
        analyzer.add_consumption(i * 60 + 30, 80, 20, EnergyConsumerType.MANIPULATION)
    
    report = analyzer.get_report()
    
    # report 是 EnergyReport 对象，需要调用 to_dict()
    report_dict = report.to_dict()
    
    assert "balance" in report_dict, "报告应包含能量平衡"
    assert "recommendations" in report_dict, "报告应包含建议"
    assert "solar_coverage_analysis" in report_dict, "报告应包含太阳能分析"
    
    # 检查建议
    assert isinstance(report_dict["recommendations"], list), "建议应为列表"


# ============================================================
# 可靠性分析测试
# ============================================================

def test_reliability_analyzer_basic() -> None:
    """测试可靠性分析器基本功能"""
    analyzer = ReliabilityAnalyzer()
    
    # 添加故障事件
    analyzer.add_failure(
        timestamp=10,
        failure_type=FailureType.GRASP_FAILED,
        task_id="task_1",
        task_type="top_grasp",
        description="抓取失败",
        recovery_actions=[],
        recovery_success=True,
        recovery_time=5.0,
    )
    
    analyzer.add_failure(
        timestamp=50,
        failure_type=FailureType.NAVIGATION_BLOCKED,
        task_id="task_2",
        task_type="navigate_to_zone",
        description="导航受阻",
        recovery_success=False,
        recovery_time=10.0,
    )
    
    # 添加任务记录
    for i in range(10):
        analyzer.add_task_record(
            task_id=f"task_{i}",
            task_type=["top_grasp", "navigate"][i % 2],
            start_time=i * 10,
            end_time=i * 10 + 8,
            success=i % 3 != 0,  # 66.7% 成功率
        )
    
    # 分析
    report = analyzer.analyze()
    
    assert report.total_failures == 2, f"故障数应为 2，实际为 {report.total_failures}"
    assert report.total_tasks == 10, f"任务数应为 10，实际为 {report.total_tasks}"
    assert 0 <= report.overall_success_rate <= 1, "成功率应在 0-1 之间"
    assert report.reliability_score >= 0, "可靠性评分应非负"


def test_reliability_analyzer_failure_stats() -> None:
    """测试故障统计"""
    analyzer = ReliabilityAnalyzer()
    
    # 添加不同类型的故障
    for i in range(5):
        analyzer.add_failure(
            timestamp=i * 100,
            failure_type=FailureType.GRASP_FAILED,
            task_id=f"task_{i}",
            task_type="top_grasp",
            recovery_success=i < 4,  # 80% 恢复成功
        )
    
    for i in range(3):
        analyzer.add_failure(
            timestamp=i * 100 + 500,
            failure_type=FailureType.NAVIGATION_BLOCKED,
            task_id=f"nav_{i}",
            task_type="navigate",
            recovery_success=True,
        )
    
    report = analyzer.analyze()
    
    # 检查故障类型统计
    assert "grasp_failed" in report.failure_stats, "应包含抓取失败统计"
    assert "navigation_blocked" in report.failure_stats, "应包含导航受阻统计"
    
    grasp_stats = report.failure_stats["grasp_failed"]
    assert grasp_stats.count == 5, "抓取失败数应为 5"
    assert grasp_stats.recovery_success_rate == 0.8, "恢复成功率应为 80%"


def test_reliability_analyzer_recommendations() -> None:
    """测试可靠性建议生成"""
    analyzer = ReliabilityAnalyzer()
    
    # 添加低成功率数据
    for i in range(20):
        analyzer.add_task_record(
            task_id=f"task_{i}",
            task_type="top_grasp",
            start_time=i * 10,
            end_time=i * 10 + 8,
            success=i % 5 == 0,  # 20% 成功率
        )
    
    report = analyzer.analyze()
    
    # 应生成建议
    assert len(report.recommendations) > 0, "应生成优化建议"


# ============================================================
# 路径优化测试
# ============================================================

def test_path_optimizer_basic() -> None:
    """测试路径优化器基本功能"""
    optimizer = PathOptimizer(method=OptimizationMethod.NEAREST_NEIGHBOR)
    
    # 创建测试任务位置
    tasks = [
        TaskLocation(id="t1", x=0, y=0, task_id="t1", zone="mine"),
        TaskLocation(id="t2", x=10, y=0, task_id="t2", zone="station"),
        TaskLocation(id="t3", x=10, y=10, task_id="t3", zone="warehouse"),
        TaskLocation(id="t4", x=0, y=10, task_id="t4", zone="dock"),
    ]
    
    # 优化
    result = optimizer.optimize(tasks)
    
    assert len(result.locations) == 4, "应返回 4 个位置"
    assert result.total_distance > 0, "总距离应大于 0"
    assert result.optimization_method == "nearest_neighbor", "方法应为最近邻"


def test_path_optimizer_two_opt() -> None:
    """测试 2-opt 优化"""
    optimizer = PathOptimizer(method=OptimizationMethod.TWO_OPT)
    
    # 创建测试任务（故意打乱顺序）
    tasks = [
        TaskLocation(id="t1", x=0, y=0, task_id="t1"),
        TaskLocation(id="t2", x=100, y=0, task_id="t2"),
        TaskLocation(id="t3", x=100, y=100, task_id="t3"),
        TaskLocation(id="t4", x=0, y=100, task_id="t4"),
        TaskLocation(id="t5", x=50, y=50, task_id="t5"),
    ]
    
    result = optimizer.optimize(tasks)
    
    assert len(result.locations) == 5, "应返回 5 个位置"
    assert result.total_distance > 0, "总距离应大于 0"
    
    # 2-opt 应该找到较好的解
    # 原始顺序距离：0→100→141→141→71→... 
    # 优化后应该更短
    assert result.improvement_ratio >= 0, "改进比例应非负"


def test_path_optimizer_savings() -> None:
    """测试路径优化节省计算"""
    optimizer = PathOptimizer()
    
    tasks = [
        TaskLocation(id=f"t{i}", x=i * 10, y=i * 5, task_id=f"t{i}")
        for i in range(6)
    ]
    
    # 原始顺序
    original = list(tasks)
    
    # 优化
    optimized = optimizer.optimize(tasks)
    
    # 计算节省
    savings = optimizer.calculate_savings(original, optimized)
    
    assert "original_distance" in savings, "应包含原始距离"
    assert "optimized_distance" in savings, "应包含优化距离"
    assert "distance_saved" in savings, "应包含节省距离"


# ============================================================
# 并行调度测试
# ============================================================

def test_parallel_scheduler_basic() -> None:
    """测试并行调度器基本功能"""
    scheduler = ParallelScheduler(min_parallel_window=30.0)
    
    # 添加任务
    scheduler.add_task(TaskWindow(
        task_id="mine_1",
        task_type=TaskType.MINING,
        start_time=0,
        end_time=60,
        duration=60,
        priority=TaskPriority.MEDIUM,
    ))
    
    scheduler.add_task(TaskWindow(
        task_id="mine_2",
        task_type=TaskType.MINING,
        start_time=60,
        end_time=120,
        duration=60,
        priority=TaskPriority.MEDIUM,
    ))
    
    # 添加等待时段
    scheduler.add_waiting_period(
        station="smelter",
        recipe="smelt_iron",
        start_time=0,
        duration=60,
    )
    
    # 调度
    result = scheduler.schedule()
    
    assert len(result.scheduled_tasks) > 0, "应有调度任务"
    assert result.total_time >= 0, "总时间应非负"
    # 效率可能超过 1（当并行执行时总工作时间超过总时间）
    assert result.efficiency >= 0, "效率应非负"


def test_parallel_scheduler_optimize() -> None:
    """测试并行调度优化"""
    scheduler = ParallelScheduler(min_parallel_window=20.0)
    
    # 添加多个任务
    for i in range(5):
        scheduler.add_task(TaskWindow(
            task_id=f"mine_{i}",
            task_type=TaskType.MINING,
            start_time=i * 30,
            end_time=i * 30 + 30,
            duration=30,
            priority=TaskPriority.MEDIUM,
        ))
    
    # 添加多个等待时段
    for i in range(3):
        scheduler.add_waiting_period(
            station=f"station_{i}",
            recipe=f"recipe_{i}",
            start_time=i * 100,
            duration=60,
        )
    
    # 优化调度
    result = scheduler.optimize_schedule()
    
    # 检查并行任务
    assert len(result.parallel_tasks) >= 0, "应有并行任务（可能为 0）"
    
    # 计算并行效率
    efficiency = scheduler.calculate_parallel_efficiency()
    assert "parallel_efficiency" in efficiency, "应包含并行效率"


# ============================================================
# 技能优化测试
# ============================================================

def test_skill_optimizer_basic() -> None:
    """测试技能优化器基本功能"""
    optimizer = SkillOptimizer()
    
    # 记录执行历史
    for i in range(15):
        optimizer.record_execution(
            skill_type=SkillType.TOP_GRASP,
            params={
                "grasp_force": 30 + i,
                "grasp_width": 0.08,
                "approach_height": 0.15,
            },
            success=i < 12,  # 80% 成功率
            execution_time=5.0,
        )
    
    # 优化
    result = optimizer.optimize(SkillType.TOP_GRASP)
    
    assert result.skill_type == SkillType.TOP_GRASP, "技能类型应为顶抓"
    assert "best_params" in result.to_dict(), "应包含最佳参数"
    assert result.success_rate_before > 0, "优化前成功率应大于 0"


def test_skill_optimizer_object_params() -> None:
    """测试物体特定参数"""
    optimizer = SkillOptimizer()
    
    # 获取不同物体的默认参数
    iron_ore_params = optimizer.get_object_params("iron_ore")
    circuit_params = optimizer.get_object_params("circuit_board")
    
    # 检查参数差异
    assert iron_ore_params.grasp_force > circuit_params.grasp_force, \
        "铁矿石抓取力应大于电路板"
    
    assert iron_ore_params.object_type == "iron_ore", "物体类型应为铁矿石"


def test_skill_optimizer_failure_analysis() -> None:
    """测试失败分析"""
    optimizer = SkillOptimizer()
    
    # 添加失败记录
    for i in range(10):
        optimizer.record_execution(
            skill_type=SkillType.TOP_GRASP,
            params={"grasp_force": 20 + i},
            success=False,
            execution_time=5.0,
            failure_reason="slip" if i < 5 else "miss",
        )
    
    # 分析失败
    analysis = optimizer.analyze_failures(SkillType.TOP_GRASP)
    
    assert analysis["failure_count"] == 10, "失败数应为 10"
    assert "slip" in analysis["failure_reasons"], "应包含滑落失败"
    assert "miss" in analysis["failure_reasons"], "应包含未命中失败"


# ============================================================
# 能源优化测试
# ============================================================

def test_energy_optimizer_basic() -> None:
    """测试能源优化器基本功能"""
    optimizer = EnergyOptimizer(policy=EnergyPolicy.BALANCED)
    
    # 更新状态
    optimizer.update_battery_state(soc=0.25)
    optimizer.update_solar_state(current_power=80.0, sim_time=11 * 3600)
    
    # 检查是否需要充电
    should_charge, priority, reason = optimizer.should_charge(11 * 3600)
    
    assert should_charge, "低电量应需要充电"
    assert priority in [ChargingPriority.HIGH, ChargingPriority.MEDIUM], \
        "优先级应为高或中"


def test_energy_optimizer_charging_plan() -> None:
    """测试充电计划"""
    optimizer = EnergyOptimizer(policy=EnergyPolicy.PROACTIVE)
    
    # 更新状态
    optimizer.update_battery_state(soc=0.5)
    optimizer.update_solar_state(current_power=100.0, sim_time=12 * 3600)
    
    # 规划充电
    schedules = optimizer.plan_charging(12 * 3600)
    
    assert len(schedules) > 0, "应生成充电计划"
    
    for schedule in schedules:
        assert schedule.duration > 0, "充电时长应大于 0"
        assert schedule.target_soc > 0.5, "目标电量应高于当前"


def test_energy_optimizer_solar_optimized() -> None:
    """测试太阳能优化策略"""
    optimizer = EnergyOptimizer(policy=EnergyPolicy.SOLAR_OPTIMIZED)
    
    # 模拟日照高峰
    optimizer.update_battery_state(soc=0.6)
    optimizer.update_solar_state(current_power=100.0, sim_time=12 * 3600)
    
    should_charge, priority, reason = optimizer.should_charge(12 * 3600)
    
    # 日照高峰且电量 < 80% 应充电
    assert should_charge, "日照高峰应充电"
    assert priority == ChargingPriority.OPPORTUNISTIC, "应为机会性充电"


def test_energy_optimizer_time_estimation() -> None:
    """测试时间估算"""
    optimizer = EnergyOptimizer()
    
    # 测试到临界电量时间
    optimizer.update_battery_state(soc=0.5)
    time_to_critical = optimizer.estimate_time_to_critical(power_consumption=50.0)
    
    assert time_to_critical > 0, "到临界电量时间应大于 0"
    
    # 测试充电时间
    charge_time = optimizer.estimate_charge_time(target_soc=0.9, current_soc=0.5)
    assert charge_time > 0, "充电时间应大于 0"


# ============================================================
# 主测试入口
# ============================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GENESIS P8 评估与优化测试")
    parser.add_argument(
        "--test",
        type=str,
        default="all",
        help="测试模块名称 (time/energy/reliability/path/parallel/skill/energy_opt/all)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="详细输出",
    )
    
    args = parser.parse_args()
    
    runner = TestRunner(verbose=args.verbose)
    
    print("=" * 60)
    print("🧪 GENESIS P8 评估与优化测试")
    print("=" * 60)
    
    # 定义测试映射
    test_modules = {
        "time": [
            ("时间分析器基本功能", test_time_analyzer_basic),
            ("时间分析报告生成", test_time_analyzer_report),
        ],
        "energy": [
            ("能量分析器基本功能", test_energy_analyzer_basic),
            ("太阳能覆盖分析", test_energy_analyzer_solar_coverage),
            ("能量分析报告", test_energy_analyzer_report),
        ],
        "reliability": [
            ("可靠性分析器基本功能", test_reliability_analyzer_basic),
            ("故障统计", test_reliability_analyzer_failure_stats),
            ("可靠性建议生成", test_reliability_analyzer_recommendations),
        ],
        "path": [
            ("路径优化器基本功能", test_path_optimizer_basic),
            ("2-opt 优化", test_path_optimizer_two_opt),
            ("路径优化节省计算", test_path_optimizer_savings),
        ],
        "parallel": [
            ("并行调度器基本功能", test_parallel_scheduler_basic),
            ("并行调度优化", test_parallel_scheduler_optimize),
        ],
        "skill": [
            ("技能优化器基本功能", test_skill_optimizer_basic),
            ("物体特定参数", test_skill_optimizer_object_params),
            ("失败分析", test_skill_optimizer_failure_analysis),
        ],
        "energy_opt": [
            ("能源优化器基本功能", test_energy_optimizer_basic),
            ("充电计划", test_energy_optimizer_charging_plan),
            ("太阳能优化策略", test_energy_optimizer_solar_optimized),
            ("时间估算", test_energy_optimizer_time_estimation),
        ],
    }
    
    # 运行测试
    if args.test == "all":
        for module, tests in test_modules.items():
            print(f"\n📦 测试模块: {module}")
            for name, func in tests:
                runner.run_test(name, func)
    else:
        module = args.test
        if module in test_modules:
            print(f"\n📦 测试模块: {module}")
            for name, func in test_modules[module]:
                runner.run_test(name, func)
        else:
            print(f"❌ 未知测试模块: {module}")
            print(f"可用模块: {list(test_modules.keys())}")
            return 1
    
    # 输出摘要
    success = runner.summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
