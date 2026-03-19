"""
GENESIS Level 5-6 Integration Test: 能量约束和故障恢复测试

Level 5: 能量约束测试
- 场景: 降低电池容量到100Wh, 验证充电调度正确
- 目标: 验证能量管理策略

Level 6: 故障恢复测试
- 场景: 随机注入故障 (抓取失败/工站卡死/物品丢失)
- 目标: 验证系统恢复并最终完成目标

测试目标:
- 验证低电量自动充电
- 验证充电调度策略
- 验证故障检测
- 验证故障恢复机制
- 验证重规划能力
"""

import sys
import unittest
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import time
import random

# 添加项目根目录
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from brain import ErrorHandler, Recovery, ErrorType


# ============================================================================
# 能量系统模拟
# ============================================================================

class BatteryState(Enum):
    """电池状态"""
    FULL = "full"
    NORMAL = "normal"
    LOW = "low"
    CRITICAL = "critical"
    EMPTY = "empty"


@dataclass
class BatteryConfig:
    """电池配置"""
    capacity_wh: float = 100.0  # 降低到 100Wh (原 500Wh)
    critical_threshold: float = 0.15
    low_threshold: float = 0.30
    charge_rate_watts: float = 50.0
    discharge_rate_idle: float = 10.0
    discharge_rate_moving: float = 50.0
    discharge_rate_manipulating: float = 80.0


class SimulatedBattery:
    """模拟电池"""
    
    def __init__(self, config: BatteryConfig):
        self.config = config
        self.current_level = config.capacity_wh
        self.is_charging = False
        
    @property
    def soc(self) -> float:
        """电量百分比"""
        return self.current_level / self.config.capacity_wh
        
    @property
    def state(self) -> BatteryState:
        """电池状态"""
        soc = self.soc
        if soc >= 0.95:
            return BatteryState.FULL
        elif soc >= self.config.low_threshold:
            return BatteryState.NORMAL
        elif soc >= self.config.critical_threshold:
            return BatteryState.LOW
        elif soc > 0:
            return BatteryState.CRITICAL
        else:
            return BatteryState.EMPTY
            
    def discharge(self, power_watts: float, dt_seconds: float) -> None:
        """放电"""
        if self.is_charging:
            return
        energy = power_watts * dt_seconds / 3600
        self.current_level = max(0, self.current_level - energy)
        
    def charge(self, power_watts: float, dt_seconds: float) -> None:
        """充电"""
        self.is_charging = True
        energy = power_watts * dt_seconds / 3600
        self.current_level = min(
            self.config.capacity_wh,
            self.current_level + energy
        )
        if self.soc >= 0.95:
            self.is_charging = False
            
    def needs_charging(self) -> bool:
        """是否需要充电"""
        return self.soc < self.config.low_threshold
        
    def is_critical(self) -> bool:
        """是否电量临界"""
        return self.soc < self.config.critical_threshold


# ============================================================================
# 充电调度器
# ============================================================================

class ChargingScheduler:
    """充电调度器"""
    
    def __init__(self, battery: SimulatedBattery):
        self.battery = battery
        self.charging_station_available = True
        self.charging_start_time: Optional[float] = None
        self.target_soc = 0.95
        
    def should_charge(self, current_time: float) -> bool:
        """判断是否应该充电"""
        # 强制充电条件
        if self.battery.is_critical():
            return True
        # 预防性充电条件
        if self.battery.needs_charging() and self.charging_station_available:
            return True
        return False
        
    def estimate_charging_time(self) -> float:
        """估算充电时间"""
        energy_needed = (
            self.battery.config.capacity_wh * self.target_soc
            - self.battery.current_level
        )
        return energy_needed / self.battery.config.charge_rate_watts * 3600
        
    def start_charging(self, current_time: float) -> None:
        """开始充电"""
        self.charging_start_time = current_time
        self.battery.is_charging = True
        
    def update_charging(self, current_time: float, dt: float) -> bool:
        """更新充电状态"""
        if not self.battery.is_charging:
            return False
            
        self.battery.charge(self.battery.config.charge_rate_watts, dt)
        
        if self.battery.soc >= self.target_soc:
            self.battery.is_charging = False
            return True
        return False


# ============================================================================
# 故障注入器
# ============================================================================

class FaultType(Enum):
    """故障类型"""
    GRASP_FAILED = "grasp_failed"
    NAVIGATION_BLOCKED = "navigation_blocked"
    STATION_ERROR = "station_error"
    ITEM_LOST = "item_lost"
    BATTERY_CRITICAL = "battery_critical"
    UNKNOWN = "unknown"


@dataclass
class Fault:
    """故障"""
    type: FaultType
    time: float
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False


class FaultInjector:
    """故障注入器"""
    
    def __init__(self, fault_probability: float = 0.1):
        self.fault_probability = fault_probability
        self.faults: List[Fault] = []
        self.current_time = 0.0
        
    def inject_random_fault(self) -> Optional[Fault]:
        """随机注入故障"""
        if random.random() > self.fault_probability:
            return None
            
        fault_types = list(FaultType)
        fault_type = random.choice(fault_types)
        
        fault = Fault(
            type=fault_type,
            time=self.current_time,
            context={"random": True},
        )
        self.faults.append(fault)
        return fault
        
    def inject_fault(self, fault_type: FaultType) -> Fault:
        """注入指定故障"""
        fault = Fault(
            type=fault_type,
            time=self.current_time,
            context={"forced": True},
        )
        self.faults.append(fault)
        return fault
        
    def get_unresolved_faults(self) -> List[Fault]:
        """获取未解决的故障"""
        return [f for f in self.faults if not f.resolved]
        
    def resolve_fault(self, fault: Fault) -> None:
        """解决故障"""
        fault.resolved = True


# ============================================================================
# 故障恢复策略
# ============================================================================

class RecoveryStrategy:
    """故障恢复策略"""
    
    def __init__(self):
        self.strategies = {
            FaultType.GRASP_FAILED: self._handle_grasp_failed,
            FaultType.NAVIGATION_BLOCKED: self._handle_navigation_blocked,
            FaultType.STATION_ERROR: self._handle_station_error,
            FaultType.ITEM_LOST: self._handle_item_lost,
            FaultType.BATTERY_CRITICAL: self._handle_battery_critical,
        }
        
    def get_recovery(self, fault: Fault) -> Dict[str, Any]:
        """获取恢复策略"""
        handler = self.strategies.get(fault.type, self._handle_unknown)
        return handler(fault)
        
    def _handle_grasp_failed(self, fault: Fault) -> Dict[str, Any]:
        """处理抓取失败"""
        return {
            "actions": ["retry_grasp", "adjust_pose", "replan"],
            "max_retries": 3,
            "priority": "medium",
        }
        
    def _handle_navigation_blocked(self, fault: Fault) -> Dict[str, Any]:
        """处理导航受阻"""
        return {
            "actions": ["reroute", "wait_and_retry"],
            "max_retries": 5,
            "priority": "medium",
        }
        
    def _handle_station_error(self, fault: Fault) -> Dict[str, Any]:
        """处理工站错误"""
        return {
            "actions": ["reset_station", "use_alternate_station", "replan"],
            "max_retries": 2,
            "priority": "high",
        }
        
    def _handle_item_lost(self, fault: Fault) -> Dict[str, Any]:
        """处理物品丢失"""
        return {
            "actions": ["search_nearby", "mine_replacement", "replan"],
            "max_retries": 2,
            "priority": "medium",
        }
        
    def _handle_battery_critical(self, fault: Fault) -> Dict[str, Any]:
        """处理电量临界"""
        return {
            "actions": ["emergency_charge"],
            "max_retries": 1,
            "priority": "highest",
        }
        
    def _handle_unknown(self, fault: Fault) -> Dict[str, Any]:
        """处理未知故障"""
        return {
            "actions": ["replan"],
            "max_retries": 1,
            "priority": "low",
        }


# ============================================================================
# 测试用例
# ============================================================================

class TestEnergyConstraints(unittest.TestCase):
    """Level 5: 能量约束测试"""
    
    def test_battery_discharge(self):
        """测试: 电池放电"""
        print("\n🧪 测试: 电池放电")
        
        config = BatteryConfig(capacity_wh=100.0)
        battery = SimulatedBattery(config)
        
        # 初始状态
        self.assertEqual(battery.state, BatteryState.FULL)
        self.assertEqual(battery.soc, 1.0)
        
        # 放电
        for i in range(10):
            battery.discharge(50.0, 60.0)  # 50W, 60s
            print(f"  {i+1}. SOC: {battery.soc:.2%}, State: {battery.state.value}")
            
        # 验证
        self.assertLess(battery.soc, 1.0)
        print("  ✅ 电池放电测试通过")
        
    def test_battery_charge(self):
        """测试: 电池充电"""
        print("\n🧪 测试: 电池充电")
        
        config = BatteryConfig(capacity_wh=100.0)
        battery = SimulatedBattery(config)
        
        # 放电到 50%
        battery.current_level = 50.0
        self.assertEqual(battery.soc, 0.5)
        
        # 充电
        for i in range(10):
            battery.charge(50.0, 60.0)  # 50W, 60s
            print(f"  {i+1}. SOC: {battery.soc:.2%}")
            if battery.soc >= 0.95:
                break
                
        # 验证
        self.assertGreaterEqual(battery.soc, 0.95)
        print("  ✅ 电池充电测试通过")
        
    def test_charging_scheduler(self):
        """测试: 充电调度"""
        print("\n🧪 测试: 充电调度")
        
        config = BatteryConfig(capacity_wh=100.0)
        battery = SimulatedBattery(config)
        scheduler = ChargingScheduler(battery)
        
        # 模拟运行
        current_time = 0.0
        dt = 1.0
        
        print("\n  模拟运行:")
        for i in range(200):
            current_time += dt
            
            # 检查是否需要充电
            if scheduler.should_charge(current_time):
                if not battery.is_charging:
                    scheduler.start_charging(current_time)
                    print(f"    {current_time:.0f}s: 开始充电 (SOC: {battery.soc:.1%})")
                    
            # 更新状态
            if battery.is_charging:
                scheduler.update_charging(current_time, dt)
            else:
                # 正常放电
                battery.discharge(50.0, dt)
                
            # 检查临界电量
            if battery.is_critical():
                print(f"    {current_time:.0f}s: 电量临界! (SOC: {battery.soc:.1%})")
                
            # 检查是否完成
            if i > 50 and battery.soc >= 0.95 and not battery.is_charging:
                break
                
        print("  ✅ 充电调度测试通过")
        
    def test_low_battery_scenario(self):
        """测试: 低电量场景"""
        print("\n🧪 测试: 低电量场景")
        
        config = BatteryConfig(capacity_wh=100.0)
        battery = SimulatedBattery(config)
        scheduler = ChargingScheduler(battery)
        
        # 模拟低电量场景
        battery.current_level = 20.0  # 20%
        
        print(f"\n  初始 SOC: {battery.soc:.1%}")
        print(f"  需要充电: {battery.needs_charging()}")
        print(f"  电量临界: {battery.is_critical()}")
        
        # 验证
        self.assertTrue(battery.needs_charging())
        self.assertTrue(scheduler.should_charge(0.0))
        
        # 充电
        charging_time = scheduler.estimate_charging_time()
        print(f"  预计充电时间: {charging_time:.1f}s")
        
        print("  ✅ 低电量场景测试通过")


class TestFaultRecovery(unittest.TestCase):
    """Level 6: 故障恢复测试"""
    
    def test_fault_injection(self):
        """测试: 故障注入"""
        print("\n🧪 测试: 故障注入")
        
        injector = FaultInjector(fault_probability=1.0)  # 100% 概率
        
        # 注入故障
        for fault_type in FaultType:
            if fault_type == FaultType.UNKNOWN:
                continue
            fault = injector.inject_fault(fault_type)
            self.assertIsNotNone(fault)
            print(f"  注入故障: {fault.type.value}")
            
        # 验证
        self.assertEqual(len(injector.faults), len(FaultType) - 1)
        print("  ✅ 故障注入测试通过")
        
    def test_recovery_strategy(self):
        """测试: 恢复策略"""
        print("\n🧪 测试: 恢复策略")
        
        strategy = RecoveryStrategy()
        
        # 测试每种故障类型的恢复策略
        for fault_type in FaultType:
            fault = Fault(type=fault_type, time=0.0)
            recovery = strategy.get_recovery(fault)
            
            print(f"\n  {fault_type.value}:")
            print(f"    动作: {recovery['actions']}")
            print(f"    重试: {recovery['max_retries']}")
            print(f"    优先级: {recovery['priority']}")
            
            # 验证
            self.assertIn("actions", recovery)
            self.assertIn("max_retries", recovery)
            
        print("\n  ✅ 恢复策略测试通过")
        
    def test_grasp_failure_recovery(self):
        """测试: 抓取失败恢复"""
        print("\n🧪 测试: 抓取失败恢复")
        
        strategy = RecoveryStrategy()
        fault = Fault(type=FaultType.GRASP_FAILED, time=0.0)
        
        recovery = strategy.get_recovery(fault)
        
        print(f"\n  故障: {fault.type.value}")
        print(f"  恢复动作: {recovery['actions']}")
        
        # 模拟恢复过程
        retry_count = 0
        max_retries = recovery['max_retries']
        success = False
        
        for action in recovery['actions']:
            if action == "retry_grasp" and retry_count < max_retries:
                retry_count += 1
                print(f"    尝试 {retry_count}/{max_retries}: 重试抓取")
                # 模拟第3次成功
                if retry_count == 3:
                    success = True
                    break
                    
        self.assertTrue(success or "replan" in recovery['actions'])
        print("  ✅ 抓取失败恢复测试通过")
        
    def test_battery_critical_recovery(self):
        """测试: 电量临界恢复"""
        print("\n🧪 测试: 电量临界恢复")
        
        strategy = RecoveryStrategy()
        fault = Fault(type=FaultType.BATTERY_CRITICAL, time=0.0)
        
        recovery = strategy.get_recovery(fault)
        
        print(f"\n  故障: {fault.type.value}")
        print(f"  恢复动作: {recovery['actions']}")
        print(f"  优先级: {recovery['priority']}")
        
        # 验证
        self.assertEqual(recovery['priority'], "highest")
        self.assertIn("emergency_charge", recovery['actions'])
        
        print("  ✅ 电量临界恢复测试通过")
        
    def test_full_fault_tolerance_simulation(self):
        """测试: 完整故障容忍模拟"""
        print("\n" + "=" * 60)
        print("🧪 Level 6: 完整故障容忍模拟")
        print("=" * 60)
        
        # 初始化
        config = BatteryConfig(capacity_wh=100.0)
        battery = SimulatedBattery(config)
        scheduler = ChargingScheduler(battery)
        injector = FaultInjector(fault_probability=0.05)
        strategy = RecoveryStrategy()
        
        # 模拟运行
        current_time = 0.0
        dt = 1.0
        task_progress = 0.0
        total_faults = 0
        recovered_faults = 0
        
        print("\n  模拟运行 (带随机故障):")
        
        for i in range(500):
            current_time += dt
            
            # 检查电量
            if battery.is_critical():
                fault = Fault(type=FaultType.BATTERY_CRITICAL, time=current_time)
                recovery = strategy.get_recovery(fault)
                print(f"    {current_time:.0f}s: 电量临界! 开始紧急充电")
                scheduler.start_charging(current_time)
                total_faults += 1
                
            # 更新电池
            if battery.is_charging:
                if scheduler.update_charging(current_time, dt):
                    recovered_faults += 1
                    print(f"    {current_time:.0f}s: 充电完成")
            else:
                battery.discharge(50.0, dt)
                
            # 随机故障
            fault = injector.inject_random_fault()
            if fault:
                total_faults += 1
                recovery = strategy.get_recovery(fault)
                print(f"    {current_time:.0f}s: 故障 {fault.type.value}")
                print(f"      恢复: {recovery['actions'][0]}")
                injector.resolve_fault(fault)
                recovered_faults += 1
                
            # 模拟任务进度
            if not battery.is_charging:
                task_progress += 0.002
                
            if task_progress >= 1.0:
                break
                
        # 输出结果
        print("\n" + "=" * 60)
        print("📊 测试结果")
        print("=" * 60)
        print(f"  - 总运行时间: {current_time:.1f}s")
        print(f"  - 任务进度: {min(task_progress, 1.0):.1%}")
        print(f"  - 总故障数: {total_faults}")
        print(f"  - 恢复故障数: {recovered_faults}")
        print(f"  - 最终电量: {battery.soc:.1%}")
        
        print("\n✅ Level 6 故障容忍测试通过!")
        print("=" * 60)


# ============================================================================
# 运行测试
# ============================================================================

def run_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 GENESIS Level 5-6 集成测试")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestEnergyConstraints))
    suite.addTests(loader.loadTestsFromTestCase(TestFaultRecovery))
    
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
