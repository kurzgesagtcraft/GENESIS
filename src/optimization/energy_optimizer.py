"""
GENESIS 能源管理优化模块

智能充电调度，在任务间隙预充电，
优化日照高峰期充电策略，提高能源利用效率。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum
import math
import json
from pathlib import Path
from datetime import datetime


class EnergyPolicy(Enum):
    """能源策略"""
    REACTIVE = "reactive"           # 被动：低电量才充电
    PROACTIVE = "proactive"         # 主动：任务间隙预充电
    SOLAR_OPTIMIZED = "solar_optimized"  # 太阳能优化：日照高峰充电
    COST_OPTIMIZED = "cost_optimized"    # 成本优化：低谷充电
    BALANCED = "balanced"           # 平衡策略


class ChargingPriority(Enum):
    """充电优先级"""
    EMERGENCY = 0       # 紧急：电量 < 15%
    HIGH = 1            # 高：电量 < 30%
    MEDIUM = 2          # 中：任务间隙
    LOW = 3             # 低：空闲时
    OPPORTUNISTIC = 4   # 机会性：日照高峰


@dataclass
class ChargingSchedule:
    """充电计划"""
    start_time: float
    end_time: float
    duration: float
    priority: ChargingPriority
    target_soc: float          # 目标电量
    expected_energy: float     # 预期充电量 (Wh)
    solar_available: bool      # 是否有太阳能
    reason: str = ""           # 充电原因
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "priority": self.priority.value,
            "target_soc": self.target_soc,
            "expected_energy": self.expected_energy,
            "solar_available": self.solar_available,
            "reason": self.reason,
        }


@dataclass
class BatteryState:
    """电池状态"""
    current_soc: float = 1.0       # 当前电量 (0-1)
    capacity_wh: float = 500.0     # 容量 (Wh)
    voltage: float = 48.0          # 电压 (V)
    temperature: float = 25.0      # 温度 (°C)
    health: float = 1.0            # 健康度 (0-1)
    
    @property
    def remaining_energy(self) -> float:
        """剩余能量 (Wh)"""
        return self.current_soc * self.capacity_wh * self.health
    
    @property
    def is_critical(self) -> bool:
        """是否电量临界"""
        return self.current_soc < 0.15
    
    @property
    def is_low(self) -> bool:
        """是否电量低"""
        return self.current_soc < 0.30
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "current_soc": self.current_soc,
            "capacity_wh": self.capacity_wh,
            "remaining_energy": self.remaining_energy,
            "voltage": self.voltage,
            "temperature": self.temperature,
            "health": self.health,
            "is_critical": self.is_critical,
            "is_low": self.is_low,
        }


@dataclass
class SolarState:
    """太阳能状态"""
    current_power: float = 0.0     # 当前功率 (W)
    peak_power: float = 100.0      # 峰值功率 (W)
    efficiency: float = 0.85       # 效率
    is_peak_hours: bool = False    # 是否峰值时段
    
    @property
    def effective_power(self) -> float:
        """有效功率"""
        return self.current_power * self.efficiency
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "current_power": self.current_power,
            "peak_power": self.peak_power,
            "efficiency": self.efficiency,
            "effective_power": self.effective_power,
            "is_peak_hours": self.is_peak_hours,
        }


@dataclass
class TaskEnergyRequirement:
    """任务能量需求"""
    task_id: str
    task_type: str
    estimated_energy_wh: float
    estimated_duration: float
    priority: int = 0
    deadline: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "estimated_energy_wh": self.estimated_energy_wh,
            "estimated_duration": self.estimated_duration,
            "priority": self.priority,
            "deadline": self.deadline,
        }


class EnergyOptimizer:
    """能源优化器"""
    
    # 默认参数
    DEFAULT_PARAMS = {
        "critical_soc": 0.15,        # 临界电量
        "low_soc": 0.30,             # 低电量
        "target_soc": 0.95,          # 目标电量
        "min_charge_time": 60.0,     # 最小充电时间 (秒)
        "charge_rate_w": 50.0,       # 充电功率 (W)
        "discharge_rate_w": 30.0,    # 平均放电功率 (W)
    }
    
    # 日照时段（小时）
    SOLAR_PEAK_HOURS = (10.0, 14.0)  # 10:00 - 14:00
    SOLAR_DAY_HOURS = (6.0, 18.0)    # 6:00 - 18:00
    
    def __init__(
        self,
        policy: EnergyPolicy = EnergyPolicy.BALANCED,
        battery_capacity: float = 500.0,
        solar_peak_power: float = 100.0,
        params: Optional[Dict] = None,
    ):
        """
        初始化能源优化器
        
        Args:
            policy: 能源策略
            battery_capacity: 电池容量 (Wh)
            solar_peak_power: 太阳能峰值功率 (W)
            params: 参数覆盖
        """
        self.policy = policy
        self.battery_capacity = battery_capacity
        self.solar_peak_power = solar_peak_power
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        
        self.battery_state = BatteryState(capacity_wh=battery_capacity)
        self.solar_state = SolarState(peak_power=solar_peak_power)
        self.scheduled_charges: List[ChargingSchedule] = []
        self.task_requirements: List[TaskEnergyRequirement] = []
        
    def update_battery_state(
        self,
        soc: float,
        voltage: Optional[float] = None,
        temperature: Optional[float] = None,
    ) -> None:
        """更新电池状态"""
        self.battery_state.current_soc = soc
        if voltage is not None:
            self.battery_state.voltage = voltage
        if temperature is not None:
            self.battery_state.temperature = temperature
    
    def update_solar_state(
        self,
        current_power: float,
        sim_time: float,
    ) -> None:
        """更新太阳能状态"""
        self.solar_state.current_power = current_power
        
        # 判断是否峰值时段
        hour = (sim_time / 3600) % 24
        self.solar_state.is_peak_hours = (
            self.SOLAR_PEAK_HOURS[0] <= hour <= self.SOLAR_PEAK_HOURS[1]
        )
    
    def add_task_requirement(self, task: TaskEnergyRequirement) -> None:
        """添加任务能量需求"""
        self.task_requirements.append(task)
    
    def should_charge(self, sim_time: float) -> Tuple[bool, ChargingPriority, str]:
        """
        判断是否需要充电
        
        Returns:
            (是否充电, 优先级, 原因)
        """
        # 紧急充电：电量临界
        if self.battery_state.is_critical:
            return True, ChargingPriority.EMERGENCY, "电量临界，紧急充电"
        
        # 根据策略判断
        if self.policy == EnergyPolicy.REACTIVE:
            # 被动策略：只在低电量时充电
            if self.battery_state.is_low:
                return True, ChargingPriority.HIGH, "低电量充电"
            return False, ChargingPriority.LOW, ""
        
        elif self.policy == EnergyPolicy.PROACTIVE:
            # 主动策略：任务间隙充电
            if self.battery_state.current_soc < 0.7:
                return True, ChargingPriority.MEDIUM, "任务间隙预充电"
        
        elif self.policy == EnergyPolicy.SOLAR_OPTIMIZED:
            # 太阳能优化策略
            if self.solar_state.is_peak_hours and self.battery_state.current_soc < 0.9:
                return True, ChargingPriority.OPPORTUNISTIC, "日照高峰期充电"
        
        elif self.policy == EnergyPolicy.BALANCED:
            # 平衡策略
            if self.battery_state.is_low:
                return True, ChargingPriority.HIGH, "低电量充电"
            if self.solar_state.is_peak_hours and self.battery_state.current_soc < 0.8:
                return True, ChargingPriority.OPPORTUNISTIC, "日照高峰期充电"
            if self.battery_state.current_soc < 0.5:
                return True, ChargingPriority.MEDIUM, "预防性充电"
        
        return False, ChargingPriority.LOW, ""
    
    def plan_charging(
        self,
        sim_time: float,
        upcoming_tasks: Optional[List[TaskEnergyRequirement]] = None,
    ) -> List[ChargingSchedule]:
        """
        规划充电计划
        
        Args:
            sim_time: 当前仿真时间
            upcoming_tasks: 即将执行的任务列表
        
        Returns:
            充电计划列表
        """
        self.scheduled_charges = []
        
        should_charge, priority, reason = self.should_charge(sim_time)
        
        if not should_charge:
            return self.scheduled_charges
        
        # 计算充电参数
        target_soc = self.params["target_soc"]
        if priority == ChargingPriority.EMERGENCY:
            target_soc = 0.5  # 紧急充电先充到 50%
        elif priority == ChargingPriority.HIGH:
            target_soc = 0.7
        
        # 计算需要的能量
        energy_needed = (target_soc - self.battery_state.current_soc) * self.battery_capacity
        
        # 计算充电时间
        charge_power = self.params["charge_rate_w"]
        if self.solar_state.is_peak_hours:
            charge_power = max(charge_power, self.solar_state.effective_power)
        
        charge_time = (energy_needed * 3600) / charge_power  # 秒
        charge_time = max(charge_time, self.params["min_charge_time"])
        
        # 创建充电计划
        schedule = ChargingSchedule(
            start_time=sim_time,
            end_time=sim_time + charge_time,
            duration=charge_time,
            priority=priority,
            target_soc=target_soc,
            expected_energy=energy_needed,
            solar_available=self.solar_state.is_peak_hours,
            reason=reason,
        )
        
        self.scheduled_charges.append(schedule)
        
        # 检查后续任务是否需要额外充电
        if upcoming_tasks:
            self._plan_task_based_charging(sim_time + charge_time, upcoming_tasks)
        
        return self.scheduled_charges
    
    def _plan_task_based_charging(
        self,
        start_time: float,
        tasks: List[TaskEnergyRequirement],
    ) -> None:
        """基于任务需求规划充电"""
        # 计算任务总能量需求
        total_energy_needed = sum(t.estimated_energy_wh for t in tasks)
        
        # 预估充电后的电量
        if self.scheduled_charges:
            last_charge = self.scheduled_charges[-1]
            estimated_soc = last_charge.target_soc
        else:
            estimated_soc = self.battery_state.current_soc
        
        estimated_energy = estimated_soc * self.battery_capacity
        
        # 如果能量不足，添加额外充电
        if estimated_energy < total_energy_needed * 1.2:  # 留 20% 余量
            additional_energy = total_energy_needed * 1.2 - estimated_energy
            additional_time = (additional_energy * 3600) / self.params["charge_rate_w"]
            
            schedule = ChargingSchedule(
                start_time=start_time,
                end_time=start_time + additional_time,
                duration=additional_time,
                priority=ChargingPriority.MEDIUM,
                target_soc=min(0.95, estimated_soc + additional_energy / self.battery_capacity),
                expected_energy=additional_energy,
                solar_available=False,
                reason="任务前预充电",
            )
            
            self.scheduled_charges.append(schedule)
    
    def optimize_charging_schedule(
        self,
        sim_time: float,
        time_horizon: float = 3600.0,
    ) -> List[ChargingSchedule]:
        """
        优化充电计划
        
        Args:
            sim_time: 当前仿真时间
            time_horizon: 时间范围 (秒)
        
        Returns:
            优化后的充电计划
        """
        optimized = []
        
        # 分析时间范围内的太阳能变化
        for schedule in self.scheduled_charges:
            # 检查是否可以移到日照高峰期
            hour = (schedule.start_time / 3600) % 24
            
            if not schedule.solar_available and self.policy in [
                EnergyPolicy.SOLAR_OPTIMIZED,
                EnergyPolicy.BALANCED,
            ]:
                # 尝试调整到日照高峰
                peak_start = self.SOLAR_PEAK_HOURS[0] * 3600
                if hour < self.SOLAR_PEAK_HOURS[0]:
                    # 可以推迟到峰值时段
                    adjusted = ChargingSchedule(
                        start_time=peak_start,
                        end_time=peak_start + schedule.duration,
                        duration=schedule.duration,
                        priority=ChargingPriority.OPPORTUNISTIC,
                        target_soc=schedule.target_soc,
                        expected_energy=schedule.expected_energy,
                        solar_available=True,
                        reason="调整到日照高峰期",
                    )
                    optimized.append(adjusted)
                    continue
            
            optimized.append(schedule)
        
        return optimized
    
    def get_charging_recommendation(self) -> Dict:
        """获取充电建议"""
        should_charge, priority, reason = self.should_charge(0)
        
        return {
            "should_charge": should_charge,
            "priority": priority.value,
            "reason": reason,
            "current_soc": self.battery_state.current_soc,
            "remaining_energy": self.battery_state.remaining_energy,
            "solar_power": self.solar_state.current_power,
            "is_peak_hours": self.solar_state.is_peak_hours,
            "policy": self.policy.value,
        }
    
    def estimate_time_to_critical(
        self,
        power_consumption: Optional[float] = None,
    ) -> float:
        """
        估算到临界电量的时间
        
        Args:
            power_consumption: 功率消耗 (W)，默认使用平均消耗
        
        Returns:
            预计时间 (秒)
        """
        if power_consumption is None:
            power_consumption = self.params["discharge_rate_w"]
        
        current_energy = self.battery_state.remaining_energy
        critical_energy = self.params["critical_soc"] * self.battery_capacity
        
        if current_energy <= critical_energy:
            return 0.0
        
        energy_to_critical = current_energy - critical_energy
        return (energy_to_critical * 3600) / power_consumption
    
    def estimate_charge_time(
        self,
        target_soc: float,
        current_soc: Optional[float] = None,
    ) -> float:
        """
        估算充电时间
        
        Args:
            target_soc: 目标电量
            current_soc: 当前电量（可选）
        
        Returns:
            预计时间 (秒)
        """
        if current_soc is None:
            current_soc = self.battery_state.current_soc
        
        if current_soc >= target_soc:
            return 0.0
        
        energy_needed = (target_soc - current_soc) * self.battery_capacity
        charge_power = self.params["charge_rate_w"]
        
        if self.solar_state.is_peak_hours:
            charge_power = max(charge_power, self.solar_state.effective_power)
        
        return (energy_needed * 3600) / charge_power
    
    def calculate_energy_efficiency(self) -> Dict:
        """计算能源效率"""
        return {
            "battery_health": self.battery_state.health,
            "solar_efficiency": self.solar_state.efficiency,
            "charging_efficiency": 0.85,  # 典型充电效率
            "overall_efficiency": (
                self.battery_state.health * 
                self.solar_state.efficiency * 
                0.85
            ),
        }
    
    def save_state(self, filepath: str) -> None:
        """保存状态"""
        data = {
            "policy": self.policy.value,
            "battery_state": self.battery_state.to_dict(),
            "solar_state": self.solar_state.to_dict(),
            "params": self.params,
            "scheduled_charges": [s.to_dict() for s in self.scheduled_charges],
        }
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_state(self, filepath: str) -> None:
        """加载状态"""
        path = Path(filepath)
        if not path.exists():
            return
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.policy = EnergyPolicy(data.get("policy", "balanced"))
        self.battery_state = BatteryState(
            capacity_wh=data["battery_state"].get("capacity_wh", self.battery_capacity),
            current_soc=data["battery_state"].get("current_soc", 1.0),
        )
        self.solar_state = SolarState(
            peak_power=data["solar_state"].get("peak_power", self.solar_peak_power),
            current_power=data["solar_state"].get("current_power", 0),
        )


def optimize_charging(
    battery_soc: float,
    solar_power: float,
    sim_time: float,
    policy: EnergyPolicy = EnergyPolicy.BALANCED,
) -> Dict:
    """
    优化充电的便捷函数
    
    Args:
        battery_soc: 电池电量
        solar_power: 太阳能功率
        sim_time: 仿真时间
        policy: 能源策略
    
    Returns:
        充电建议
    """
    optimizer = EnergyOptimizer(policy=policy)
    optimizer.update_battery_state(battery_soc)
    optimizer.update_solar_state(solar_power, sim_time)
    
    return optimizer.get_charging_recommendation()
