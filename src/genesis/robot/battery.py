"""
GENESIS Robot Battery Module

电池与能源管理系统，包括：
- Battery: 电池类，管理电量状态
- PowerMode: 功耗模式枚举
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

import numpy as np


class PowerMode(Enum):
    """
    功耗模式枚举
    
    定义机器人的不同工作状态及其功耗。
    """
    IDLE = "idle"           # 待机模式: 10W
    MOBILE = "mobile"       # 移动模式: 50W
    MANIPULATION = "manipulation"  # 操作模式: 80W
    PERCEPTION = "perception"  # 感知模式: 20W
    CHARGING = "charging"   # 充电模式
    
    @property
    def default_power(self) -> float:
        """获取默认功耗 (W)"""
        power_map = {
            PowerMode.IDLE: 10.0,
            PowerMode.MOBILE: 50.0,
            PowerMode.MANIPULATION: 80.0,
            PowerMode.PERCEPTION: 20.0,
            PowerMode.CHARGING: 0.0,
        }
        return power_map.get(self, 10.0)


@dataclass
class BatteryConfig:
    """
    电池配置
    
    定义电池的容量和功耗参数。
    """
    capacity_wh: float = 500.0  # 电池容量 (Wh)
    initial_soc: float = 1.0    # 初始电量状态 (0-1)
    critical_soc: float = 0.15  # 临界电量阈值 (0-1)
    
    # 功耗参数 (W)
    idle_power: float = 10.0
    mobile_power: float = 50.0
    manipulation_power: float = 80.0
    perception_power: float = 20.0
    
    # 充电参数
    max_charge_rate: float = 50.0  # 最大充电功率 (W)
    charge_efficiency: float = 0.9  # 充电效率


class Battery:
    """
    电池类
    
    管理机器人电池的电量状态、功耗计算和充电逻辑。
    
    使用示例:
        >>> battery = Battery(500)  # 500Wh 电池
        >>> battery.consume(50, 60)  # 50W 功耗，60秒
        >>> battery.soc  # 查看电量状态
        0.9
        >>> battery.charge(50, 60)  # 50W 充电，60秒
    """
    
    def __init__(
        self,
        capacity_wh: float = 500.0,
        initial_soc: float = 1.0,
        critical_soc: float = 0.15,
        config: Optional[BatteryConfig] = None,
    ):
        """
        初始化电池
        
        Args:
            capacity_wh: 电池容量 (Wh)
            initial_soc: 初始电量状态 (0-1)
            critical_soc: 临界电量阈值 (0-1)
            config: 电池配置 (可选，覆盖其他参数)
        """
        if config is not None:
            self._capacity = config.capacity_wh
            self._current_level = config.capacity_wh * config.initial_soc
            self._critical_soc = config.critical_soc
            self._config = config
        else:
            self._capacity = capacity_wh
            self._current_level = capacity_wh * initial_soc
            self._critical_soc = critical_soc
            self._config = BatteryConfig(
                capacity_wh=capacity_wh,
                initial_soc=initial_soc,
                critical_soc=critical_soc,
            )
        
        # 状态追踪
        self._total_consumed: float = 0.0  # 总消耗能量 (Wh)
        self._total_charged: float = 0.0   # 总充入能量 (Wh)
        self._current_mode: PowerMode = PowerMode.IDLE
        self._is_charging: bool = False
        
    @property
    def capacity(self) -> float:
        """电池容量 (Wh)"""
        return self._capacity
    
    @property
    def current_level(self) -> float:
        """当前电量 (Wh)"""
        return self._current_level
    
    @property
    def soc(self) -> float:
        """
        电量状态 (State of Charge)
        
        Returns:
            电量百分比 (0-1)
        """
        return self._current_level / self._capacity
    
    @property
    def is_critical(self) -> bool:
        """
        检查电量是否处于临界状态
        
        Returns:
            是否低于临界阈值
        """
        return self.soc < self._critical_soc
    
    @property
    def is_low(self) -> bool:
        """
        检查电量是否偏低 (低于 30%)
        
        Returns:
            是否低于 30%
        """
        return self.soc < 0.3
    
    @property
    def is_full(self) -> bool:
        """
        检查电池是否已满
        
        Returns:
            是否已满 (>= 99%)
        """
        return self.soc >= 0.99
    
    @property
    def current_mode(self) -> PowerMode:
        """当前功耗模式"""
        return self._current_mode
    
    @property
    def is_charging(self) -> bool:
        """是否正在充电"""
        return self._is_charging
    
    @property
    def remaining_time_hours(self) -> float:
        """
        估算剩余使用时间 (小时)
        
        基于当前功耗模式估算。
        
        Returns:
            预计剩余时间 (小时)
        """
        current_power = self._get_power_for_mode(self._current_mode)
        if current_power <= 0:
            return float('inf')
        return self._current_level / current_power
    
    @property
    def remaining_time_minutes(self) -> float:
        """
        估算剩余使用时间 (分钟)
        
        Returns:
            预计剩余时间 (分钟)
        """
        return self.remaining_time_hours * 60
    
    @property
    def total_consumed(self) -> float:
        """总消耗能量 (Wh)"""
        return self._total_consumed
    
    @property
    def total_charged(self) -> float:
        """总充入能量 (Wh)"""
        return self._total_charged
    
    @property
    def net_energy(self) -> float:
        """
        净能量变化 (Wh)
        
        正值表示充电多于消耗，负值表示消耗多于充电。
        """
        return self._total_charged - self._total_consumed
    
    def _get_power_for_mode(self, mode: PowerMode) -> float:
        """
        获取指定模式的功耗
        
        Args:
            mode: 功耗模式
            
        Returns:
            功耗 (W)
        """
        power_map = {
            PowerMode.IDLE: self._config.idle_power,
            PowerMode.MOBILE: self._config.mobile_power,
            PowerMode.MANIPULATION: self._config.manipulation_power,
            PowerMode.PERCEPTION: self._config.perception_power,
            PowerMode.CHARGING: 0.0,
        }
        return power_map.get(mode, self._config.idle_power)
    
    def consume(self, power_watts: float, dt_seconds: float) -> float:
        """
        消耗电量
        
        Args:
            power_watts: 功耗 (W)
            dt_seconds: 时间间隔 (秒)
            
        Returns:
            消耗的能量 (Wh)
        """
        if power_watts <= 0:
            return 0.0
        
        # 计算消耗的能量 (Wh)
        energy_wh = power_watts * dt_seconds / 3600.0
        
        # 更新电量
        self._current_level = max(0.0, self._current_level - energy_wh)
        self._total_consumed += energy_wh
        
        return energy_wh
    
    def consume_mode(self, mode: PowerMode, dt_seconds: float) -> float:
        """
        按功耗模式消耗电量
        
        Args:
            mode: 功耗模式
            dt_seconds: 时间间隔 (秒)
            
        Returns:
            消耗的能量 (Wh)
        """
        self._current_mode = mode
        power = self._get_power_for_mode(mode)
        return self.consume(power, dt_seconds)
    
    def charge(self, power_watts: float, dt_seconds: float) -> float:
        """
        充电
        
        Args:
            power_watts: 充电功率 (W)
            dt_seconds: 时间间隔 (秒)
            
        Returns:
            实际充入的能量 (Wh)
        """
        if power_watts <= 0:
            return 0.0
        
        self._is_charging = True
        
        # 考虑充电效率
        effective_power = power_watts * self._config.charge_efficiency
        
        # 计算充入的能量 (Wh)
        energy_wh = effective_power * dt_seconds / 3600.0
        
        # 更新电量 (不超过容量)
        actual_energy = min(energy_wh, self._capacity - self._current_level)
        self._current_level = min(self._capacity, self._current_level + actual_energy)
        self._total_charged += actual_energy
        
        return actual_energy
    
    def stop_charging(self):
        """停止充电"""
        self._is_charging = False
        self._current_mode = PowerMode.IDLE
    
    def set_mode(self, mode: PowerMode):
        """
        设置功耗模式
        
        Args:
            mode: 功耗模式
        """
        self._current_mode = mode
        if mode == PowerMode.CHARGING:
            self._is_charging = True
    
    def reset(self, soc: float = 1.0):
        """
        重置电池状态
        
        Args:
            soc: 重置后的电量状态 (默认满电)
        """
        self._current_level = self._capacity * soc
        self._total_consumed = 0.0
        self._total_charged = 0.0
        self._current_mode = PowerMode.IDLE
        self._is_charging = False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取电池状态
        
        Returns:
            包含电池状态的字典
        """
        return {
            'capacity_wh': self._capacity,
            'current_level_wh': self._current_level,
            'soc': self.soc,
            'soc_percent': self.soc * 100,
            'is_critical': self.is_critical,
            'is_low': self.is_low,
            'is_full': self.is_full,
            'is_charging': self._is_charging,
            'current_mode': self._current_mode.value,
            'remaining_time_hours': self.remaining_time_hours,
            'remaining_time_minutes': self.remaining_time_minutes,
            'total_consumed_wh': self._total_consumed,
            'total_charged_wh': self._total_charged,
            'net_energy_wh': self.net_energy,
        }
    
    def estimate_time_to_charge(
        self,
        target_soc: float = 1.0,
        charge_power: float = 50.0,
    ) -> float:
        """
        估算充电时间
        
        Args:
            target_soc: 目标电量状态 (默认满电)
            charge_power: 充电功率 (W)
            
        Returns:
            预计充电时间 (秒)
        """
        target_level = self._capacity * target_soc
        energy_needed = target_level - self._current_level
        
        if energy_needed <= 0:
            return 0.0
        
        # 考虑充电效率
        effective_power = charge_power * self._config.charge_efficiency
        time_hours = energy_needed / effective_power
        
        return time_hours * 3600.0  # 转换为秒
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "Battery":
        """
        从配置字典创建电池实例
        
        Args:
            config: 配置字典
            
        Returns:
            电池实例
        """
        battery_config = BatteryConfig(
            capacity_wh=config.get('capacity', 500.0),
            initial_soc=config.get('initial_soc', 1.0),
            critical_soc=config.get('critical_soc', 0.15),
            idle_power=config.get('power_consumption', {}).get('idle', 10.0),
            mobile_power=config.get('power_consumption', {}).get('mobile', 50.0),
            manipulation_power=config.get('power_consumption', {}).get('manipulation', 80.0),
            perception_power=config.get('power_consumption', {}).get('perception', 20.0),
            max_charge_rate=config.get('charging', {}).get('max_rate', 50.0),
            charge_efficiency=config.get('charging', {}).get('efficiency', 0.9),
        )
        return cls(config=battery_config)
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Battery(capacity={self._capacity}Wh, "
            f"soc={self.soc:.1%}, "
            f"mode={self._current_mode.value})"
        )
    
    def __str__(self) -> str:
        """友好字符串表示"""
        status = "charging" if self._is_charging else self._current_mode.value
        return (
            f"Battery: {self.soc * 100:.1f}% "
            f"({self._current_level:.1f}/{self._capacity:.1f} Wh) "
            f"[{status}]"
        )
