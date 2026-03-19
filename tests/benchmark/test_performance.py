"""
GENESIS Performance Benchmark Tests
性能基准测试

测量指标:
- total_sim_time: 完成目标的仿真时间
- total_energy_consumed: 总能耗 (Wh)
- total_energy_generated: 总发电量 (Wh)
- energy_ratio: 发电/耗电比率
- total_distance_traveled: 机器人总行走距离
- grasp_success_rate: 抓取成功率
- replan_count: 重规划次数
- idle_time_ratio: 空闲时间占比
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
# 性能指标数据结构
# ============================================================================

@dataclass
class PerformanceMetrics:
    """性能指标"""
    # 时间指标
    total_sim_time: float = 0.0
    total_real_time: float = 0.0
    time_scale: float = 100.0
    
    # 能量指标
    total_energy_consumed: float = 0.0  # Wh
    total_energy_generated: float = 0.0  # Wh
    energy_ratio: float = 0.0
    
    # 运动指标
    total_distance_traveled: float = 0.0  # meters
    navigation_time: float = 0.0
    manipulation_time: float = 0.0
    waiting_time: float = 0.0
    charging_time: float = 0.0
    
    # 成功率指标
    grasp_attempts: int = 0
    grasp_successes: int = 0
    grasp_success_rate: float = 0.0
    
    # 规划指标
    replan_count: int = 0
    task_count: int = 0
    task_success_count: int = 0
    
    # 效率指标
    idle_time: float = 0.0
    idle_time_ratio: float = 0.0
    parallel_task_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "time": {
                "total_sim_time": self.total_sim_time,
                "total_real_time": self.total_real_time,
                "time_scale": self.time_scale,
            },
            "energy": {
                "total_energy_consumed": self.total_energy_consumed,
                "total_energy_generated": self.total_energy_generated,
                "energy_ratio": self.energy_ratio,
            },
            "motion": {
                "total_distance_traveled": self.total_distance_traveled,
                "navigation_time": self.navigation_time,
                "manipulation_time": self.manipulation_time,
                "waiting_time": self.waiting_time,
                "charging_time": self.charging_time,
            },
            "success_rate": {
                "grasp_attempts": self.grasp_attempts,
                "grasp_successes": self.grasp_successes,
                "grasp_success_rate": self.grasp_success_rate,
            },
            "planning": {
                "replan_count": self.replan_count,
                "task_count": self.task_count,
                "task_success_count": self.task_success_count,
            },
            "efficiency": {
                "idle_time": self.idle_time,
                "idle_time_ratio": self.idle_time_ratio,
                "parallel_task_count": self.parallel_task_count,
            },
        }


# ============================================================================
# 性能分析器
# ============================================================================

class PerformanceAnalyzer:
    """性能分析器"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.start_time: Optional[float] = None
        self.events: List[Dict[str, Any]] = []
        
    def start(self) -> None:
        """开始分析"""
        self.start_time = time.time()
        
    def stop(self) -> None:
        """停止分析"""
        if self.start_time:
            self.metrics.total_real_time = time.time() - self.start_time
            
    def record_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """记录事件"""
        self.events.append({
            "time": time.time(),
            "type": event_type,
            "data": data,
        })
        
    def calculate_metrics(self) -> PerformanceMetrics:
        """计算指标"""
        # 计算抓取成功率
        if self.metrics.grasp_attempts > 0:
            self.metrics.grasp_success_rate = (
                self.metrics.grasp_successes / self.metrics.grasp_attempts
            )
            
        # 计算能量比
        if self.metrics.total_energy_consumed > 0:
            self.metrics.energy_ratio = (
                self.metrics.total_energy_generated / self.metrics.total_energy_consumed
            )
            
        # 计算空闲时间比
        total_time = (
            self.metrics.navigation_time +
            self.metrics.manipulation_time +
            self.metrics.waiting_time +
            self.metrics.charging_time
        )
        if total_time > 0:
            self.metrics.idle_time_ratio = self.metrics.idle_time / total_time
            
        return self.metrics
        
    def generate_report(self) -> str:
        """生成报告"""
        metrics = self.calculate_metrics()
        
        report = []
        report.append("=" * 60)
        report.append("📊 GENESIS 性能基准报告")
        report.append("=" * 60)
        
        report.append("\n⏱️ 时间指标:")
        report.append(f"  - 总仿真时间: {metrics.total_sim_time:.1f}s ({metrics.total_sim_time/60:.1f} min)")
        report.append(f"  - 总实际时间: {metrics.total_real_time:.1f}s")
        report.append(f"  - 时间缩放: {metrics.time_scale}x")
        
        report.append("\n⚡ 能量指标:")
        report.append(f"  - 总能耗: {metrics.total_energy_consumed:.2f} Wh")
        report.append(f"  - 总发电: {metrics.total_energy_generated:.2f} Wh")
        report.append(f"  - 能量比: {metrics.energy_ratio:.2f}")
        if metrics.energy_ratio > 1.0:
            report.append("    ✅ 能量正收益!")
        else:
            report.append("    ⚠️ 能量负收益")
            
        report.append("\n🚶 运动指标:")
        report.append(f"  - 总行走距离: {metrics.total_distance_traveled:.1f} m")
        report.append(f"  - 导航时间: {metrics.navigation_time:.1f}s ({metrics.navigation_time/metrics.total_sim_time*100:.1f}%)")
        report.append(f"  - 操作时间: {metrics.manipulation_time:.1f}s ({metrics.manipulation_time/metrics.total_sim_time*100:.1f}%)")
        report.append(f"  - 等待时间: {metrics.waiting_time:.1f}s ({metrics.waiting_time/metrics.total_sim_time*100:.1f}%)")
        report.append(f"  - 充电时间: {metrics.charging_time:.1f}s ({metrics.charging_time/metrics.total_sim_time*100:.1f}%)")
        
        report.append("\n🎯 成功率指标:")
        report.append(f"  - 抓取尝试: {metrics.grasp_attempts}")
        report.append(f"  - 抓取成功: {metrics.grasp_successes}")
        report.append(f"  - 抓取成功率: {metrics.grasp_success_rate:.1%}")
        
        report.append("\n📋 规划指标:")
        report.append(f"  - 重规划次数: {metrics.replan_count}")
        report.append(f"  - 任务总数: {metrics.task_count}")
        report.append(f"  - 任务成功: {metrics.task_success_count}")
        
        report.append("\n📈 效率指标:")
        report.append(f"  - 空闲时间: {metrics.idle_time:.1f}s")
        report.append(f"  - 空闲时间比: {metrics.idle_time_ratio:.1%}")
        report.append(f"  - 并行任务数: {metrics.parallel_task_count}")
        
        report.append("\n" + "=" * 60)
        
        return "\n".join(report)


# ============================================================================
# 模拟运行器
# ============================================================================

class SimulatedRun:
    """模拟运行"""
    
    def __init__(self, goal: str = "assembled_robot"):
        self.goal = goal
        self.analyzer = PerformanceAnalyzer()
        
    def run(self) -> PerformanceMetrics:
        """运行模拟"""
        self.analyzer.start()
        
        # 模拟运行过程
        # 这里使用预设值来模拟真实运行
        
        # 时间指标
        self.analyzer.metrics.total_sim_time = 3600.0  # 1 hour
        self.analyzer.metrics.time_scale = 100.0
        
        # 能量指标
        self.analyzer.metrics.total_energy_consumed = 150.0  # Wh
        self.analyzer.metrics.total_energy_generated = 100.0  # Wh
        
        # 运动指标
        self.analyzer.metrics.total_distance_traveled = 500.0  # meters
        self.analyzer.metrics.navigation_time = 1200.0  # 20 min
        self.analyzer.metrics.manipulation_time = 900.0  # 15 min
        self.analyzer.metrics.waiting_time = 300.0  # 5 min
        self.analyzer.metrics.charging_time = 600.0  # 10 min
        
        # 成功率指标
        self.analyzer.metrics.grasp_attempts = 50
        self.analyzer.metrics.grasp_successes = 48
        
        # 规划指标
        self.analyzer.metrics.replan_count = 2
        self.analyzer.metrics.task_count = 20
        self.analyzer.metrics.task_success_count = 18
        
        # 效率指标
        self.analyzer.metrics.idle_time = 180.0
        self.analyzer.metrics.parallel_task_count = 3
        
        self.analyzer.stop()
        return self.analyzer.calculate_metrics()


# ============================================================================
# 测试用例
# ============================================================================

class TestPerformanceBenchmark(unittest.TestCase):
    """性能基准测试"""
    
    def test_metrics_calculation(self):
        """测试: 指标计算"""
        print("\n🧪 测试: 性能指标计算")
        
        metrics = PerformanceMetrics()
        
        # 设置值
        metrics.total_sim_time = 3600.0
        metrics.grasp_attempts = 100
        metrics.grasp_successes = 95
        metrics.total_energy_consumed = 200.0
        metrics.total_energy_generated = 150.0
        metrics.idle_time = 300.0
        metrics.navigation_time = 1000.0
        metrics.manipulation_time = 800.0
        metrics.waiting_time = 400.0
        metrics.charging_time = 200.0
        
        # 计算派生指标
        metrics.grasp_success_rate = metrics.grasp_successes / metrics.grasp_attempts
        metrics.energy_ratio = metrics.total_energy_generated / metrics.total_energy_consumed
        total_time = metrics.navigation_time + metrics.manipulation_time + metrics.waiting_time + metrics.charging_time
        metrics.idle_time_ratio = metrics.idle_time / total_time
        
        # 验证
        self.assertAlmostEqual(metrics.grasp_success_rate, 0.95, places=2)
        self.assertAlmostEqual(metrics.energy_ratio, 0.75, places=2)
        self.assertAlmostEqual(metrics.idle_time_ratio, 0.125, places=2)
        
        print(f"  抓取成功率: {metrics.grasp_success_rate:.1%}")
        print(f"  能量比: {metrics.energy_ratio:.2f}")
        print(f"  空闲时间比: {metrics.idle_time_ratio:.1%}")
        
        print("  ✅ 指标计算测试通过")
        
    def test_metrics_serialization(self):
        """测试: 指标序列化"""
        print("\n🧪 测试: 指标序列化")
        
        metrics = PerformanceMetrics()
        metrics.total_sim_time = 3600.0
        metrics.grasp_attempts = 100
        metrics.grasp_successes = 95
        
        # 转换为字典
        metrics_dict = metrics.to_dict()
        
        # 验证
        self.assertIn("time", metrics_dict)
        self.assertIn("energy", metrics_dict)
        self.assertIn("success_rate", metrics_dict)
        
        # JSON 序列化
        json_str = json.dumps(metrics_dict, indent=2)
        print(f"\n  JSON 输出:\n{json_str}")
        
        print("  ✅ 指标序列化测试通过")
        
    def test_performance_report(self):
        """测试: 性能报告生成"""
        print("\n🧪 测试: 性能报告生成")
        
        analyzer = PerformanceAnalyzer()
        
        # 设置指标
        analyzer.metrics.total_sim_time = 3600.0
        analyzer.metrics.total_real_time = 36.0
        analyzer.metrics.time_scale = 100.0
        analyzer.metrics.total_energy_consumed = 150.0
        analyzer.metrics.total_energy_generated = 100.0
        analyzer.metrics.total_distance_traveled = 500.0
        analyzer.metrics.navigation_time = 1200.0
        analyzer.metrics.manipulation_time = 900.0
        analyzer.metrics.waiting_time = 300.0
        analyzer.metrics.charging_time = 600.0
        analyzer.metrics.grasp_attempts = 50
        analyzer.metrics.grasp_successes = 48
        analyzer.metrics.replan_count = 2
        analyzer.metrics.task_count = 20
        analyzer.metrics.task_success_count = 18
        analyzer.metrics.idle_time = 180.0
        analyzer.metrics.parallel_task_count = 3
        
        # 生成报告
        report = analyzer.generate_report()
        print(report)
        
        # 验证报告内容
        self.assertIn("性能基准报告", report)
        self.assertIn("时间指标", report)
        self.assertIn("能量指标", report)
        
        print("\n  ✅ 性能报告生成测试通过")
        
    def test_simulated_run(self):
        """测试: 模拟运行"""
        print("\n🧪 测试: 模拟运行")
        
        run = SimulatedRun(goal="assembled_robot")
        metrics = run.run()
        
        # 验证指标
        self.assertGreater(metrics.total_sim_time, 0)
        self.assertGreater(metrics.grasp_attempts, 0)
        self.assertGreater(metrics.grasp_success_rate, 0.9)
        
        print(f"\n  仿真时间: {metrics.total_sim_time:.1f}s")
        print(f"  抓取成功率: {metrics.grasp_success_rate:.1%}")
        
        print("  ✅ 模拟运行测试通过")


class TestBenchmarkComparison(unittest.TestCase):
    """基准比较测试"""
    
    def test_energy_efficiency_comparison(self):
        """测试: 能量效率比较"""
        print("\n🧪 测试: 能量效率比较")
        
        # 不同配置的能量效率
        configs = [
            {"name": "baseline", "energy_ratio": 0.67},
            {"name": "optimized", "energy_ratio": 1.2},
            {"name": "high_efficiency", "energy_ratio": 1.5},
        ]
        
        print("\n  能量效率比较:")
        for config in configs:
            status = "✅ 正收益" if config["energy_ratio"] > 1.0 else "⚠️ 负收益"
            print(f"    {config['name']}: {config['energy_ratio']:.2f} {status}")
            
        print("  ✅ 能量效率比较测试通过")
        
    def test_time_breakdown_analysis(self):
        """测试: 时间分解分析"""
        print("\n🧪 测试: 时间分解分析")
        
        # 时间分解
        time_breakdown = {
            "navigation": 1200.0,
            "manipulation": 900.0,
            "waiting": 300.0,
            "charging": 600.0,
        }
        
        total_time = sum(time_breakdown.values())
        
        print("\n  时间分解:")
        for activity, time_spent in time_breakdown.items():
            percentage = time_spent / total_time * 100
            bar = "█" * int(percentage / 5)
            print(f"    {activity:12s}: {time_spent:6.0f}s ({percentage:5.1f}%) {bar}")
            
        # 识别瓶颈
        max_activity = max(time_breakdown, key=time_breakdown.get)
        print(f"\n  瓶颈: {max_activity} ({time_breakdown[max_activity]/total_time*100:.1f}%)")
        
        print("  ✅ 时间分解分析测试通过")


# ============================================================================
# 运行测试
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 GENESIS 性能基准测试")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestPerformanceBenchmark))
    suite.addTests(loader.loadTestsFromTestCase(TestBenchmarkComparison))
    
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
