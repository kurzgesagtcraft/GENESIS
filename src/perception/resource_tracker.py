"""
GENESIS Perception - Resource Tracker Module

资源状态感知模块，包括：
- 矿区资源追踪
- 仓库库存管理
- 工站状态监控
- 能量状态追踪
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional

import numpy as np


class ZoneState(Enum):
    """区域状态"""
    UNKNOWN = 0
    ACTIVE = 1  # 有资源可用
    DEPLETED = 2  # 资源耗尽
    PROCESSING = 3  # 正在处理
    IDLE = 4  # 空闲
    ERROR = 5  # 错误


@dataclass
class ResourceState:
    """资源状态"""
    resource_type: str
    estimated_quantity: int
    confidence: float  # 估计置信度
    last_observed_time: float
    position: Optional[np.ndarray] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "resource_type": self.resource_type,
            "estimated_quantity": self.estimated_quantity,
            "confidence": self.confidence,
            "last_observed_time": self.last_observed_time,
            "position": self.position.tolist() if self.position is not None else None,
        }


@dataclass
class StationState:
    """工站状态"""
    station_name: str
    station_type: str
    state: ZoneState
    input_buffer: Dict[str, int] = field(default_factory=dict)
    output_buffer: Dict[str, int] = field(default_factory=dict)
    current_recipe: Optional[str] = None
    process_remaining: float = 0.0
    last_observed_time: float = 0.0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "station_name": self.station_name,
            "station_type": self.station_type,
            "state": self.state.name,
            "input_buffer": self.input_buffer,
            "output_buffer": self.output_buffer,
            "current_recipe": self.current_recipe,
            "process_remaining": self.process_remaining,
            "last_observed_time": self.last_observed_time,
        }


@dataclass
class EnergyState:
    """能量状态"""
    battery_soc: float  # 电池电量 (0-1)
    solar_output: float  # 太阳能输出 (W)
    consumption_rate: float  # 消耗率 (W)
    net_energy: float  # 净能量 (Wh)
    last_updated: float = 0.0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "battery_soc": self.battery_soc,
            "solar_output": self.solar_output,
            "consumption_rate": self.consumption_rate,
            "net_energy": self.net_energy,
            "last_updated": self.last_updated,
        }


class ResourceTracker:
    """
    资源追踪器

    维护全局资源状态估计，包括矿区、仓库、工站等。
    """

    def __init__(
        self,
        decay_rate: float = 0.1,  # 置信度衰减率 (每秒)
        min_confidence: float = 0.3,  # 最小置信度
    ):
        """
        初始化资源追踪器

        Args:
            decay_rate: 置信度衰减率
            min_confidence: 最小置信度阈值
        """
        self.decay_rate = decay_rate
        self.min_confidence = min_confidence

        # 矿区资源状态
        self._mine_resources: Dict[str, ResourceState] = {}

        # 仓库库存 (精确记录)
        self._warehouse_inventory: Dict[str, int] = {}

        # 工站状态
        self._station_states: Dict[str, StationState] = {}

        # 能量状态
        self._energy_state: Optional[EnergyState] = None

        # 观察历史
        self._observation_history: List[Dict[str, Any]] = []

    def update_mine_observation(
        self,
        mine_name: str,
        resource_type: str,
        observed_quantity: int,
        timestamp: float,
        position: Optional[np.ndarray] = None,
    ):
        """
        更新矿区观察

        Args:
            mine_name: 矿区名称
            resource_type: 资源类型
            observed_quantity: 观察到的数量
            timestamp: 时间戳
            position: 观察位置
        """
        # 创建或更新资源状态
        if mine_name in self._mine_resources:
            state = self._mine_resources[mine_name]
            # 使用指数移动平均更新估计
            alpha = 0.3  # 新观察的权重
            state.estimated_quantity = int(
                alpha * observed_quantity + (1 - alpha) * state.estimated_quantity
            )
            state.confidence = min(1.0, state.confidence + 0.1)
            state.last_observed_time = timestamp
        else:
            self._mine_resources[mine_name] = ResourceState(
                resource_type=resource_type,
                estimated_quantity=observed_quantity,
                confidence=1.0,
                last_observed_time=timestamp,
                position=position,
            )

        # 记录观察历史
        self._observation_history.append({
            "type": "mine",
            "mine_name": mine_name,
            "resource_type": resource_type,
            "quantity": observed_quantity,
            "timestamp": timestamp,
        })

    def update_warehouse_item(
        self,
        item_type: str,
        quantity_delta: int,
        timestamp: float,
    ):
        """
        更新仓库物品

        Args:
            item_type: 物品类型
            quantity_delta: 数量变化 (正数=增加, 负数=减少)
            timestamp: 时间戳
        """
        current = self._warehouse_inventory.get(item_type, 0)
        new_quantity = max(0, current + quantity_delta)
        self._warehouse_inventory[item_type] = new_quantity

        # 记录观察历史
        self._observation_history.append({
            "type": "warehouse",
            "item_type": item_type,
            "quantity_delta": quantity_delta,
            "new_quantity": new_quantity,
            "timestamp": timestamp,
        })

    def set_warehouse_inventory(
        self,
        inventory: Dict[str, int],
        timestamp: float,
    ):
        """
        设置仓库库存 (覆盖)

        Args:
            inventory: 库存字典
            timestamp: 时间戳
        """
        self._warehouse_inventory = inventory.copy()

        self._observation_history.append({
            "type": "warehouse_full",
            "inventory": inventory.copy(),
            "timestamp": timestamp,
        })

    def update_station_state(
        self,
        station_name: str,
        station_type: str,
        state: ZoneState,
        input_buffer: Optional[Dict[str, int]] = None,
        output_buffer: Optional[Dict[str, int]] = None,
        current_recipe: Optional[str] = None,
        process_remaining: float = 0.0,
        timestamp: float = 0.0,
    ):
        """
        更新工站状态

        Args:
            station_name: 工站名称
            station_type: 工站类型
            state: 区域状态
            input_buffer: 输入缓冲区
            output_buffer: 输出缓冲区
            current_recipe: 当前配方
            process_remaining: 剩余处理时间
            timestamp: 时间戳
        """
        self._station_states[station_name] = StationState(
            station_name=station_name,
            station_type=station_type,
            state=state,
            input_buffer=input_buffer or {},
            output_buffer=output_buffer or {},
            current_recipe=current_recipe,
            process_remaining=process_remaining,
            last_observed_time=timestamp,
        )

        self._observation_history.append({
            "type": "station",
            "station_name": station_name,
            "state": state.name,
            "timestamp": timestamp,
        })

    def update_energy_state(
        self,
        battery_soc: float,
        solar_output: float,
        consumption_rate: float,
        net_energy: float,
        timestamp: float,
    ):
        """
        更新能量状态

        Args:
            battery_soc: 电池电量
            solar_output: 太阳能输出
            consumption_rate: 消耗率
            net_energy: 净能量
            timestamp: 时间戳
        """
        self._energy_state = EnergyState(
            battery_soc=battery_soc,
            solar_output=solar_output,
            consumption_rate=consumption_rate,
            net_energy=net_energy,
            last_updated=timestamp,
        )

    def decay_confidence(self, current_time: float):
        """
        衰减所有观察的置信度

        Args:
            current_time: 当前时间
        """
        for state in self._mine_resources.values():
            time_since_obs = current_time - state.last_observed_time
            state.confidence = max(
                self.min_confidence,
                state.confidence * np.exp(-self.decay_rate * time_since_obs)
            )

    def get_mine_state(self, mine_name: str) -> Optional[ResourceState]:
        """获取矿区状态"""
        return self._mine_resources.get(mine_name)

    def get_all_mines(self) -> Dict[str, ResourceState]:
        """获取所有矿区状态"""
        return self._mine_resources.copy()

    def get_warehouse_inventory(self) -> Dict[str, int]:
        """获取仓库库存"""
        return self._warehouse_inventory.copy()

    def get_station_state(self, station_name: str) -> Optional[StationState]:
        """获取工站状态"""
        return self._station_states.get(station_name)

    def get_all_stations(self) -> Dict[str, StationState]:
        """获取所有工站状态"""
        return self._station_states.copy()

    def get_energy_state(self) -> Optional[EnergyState]:
        """获取能量状态"""
        return self._energy_state

    def get_total_resources(self) -> Dict[str, int]:
        """
        获取总资源估计

        Returns:
            各类型资源的总量估计
        """
        totals = {}

        # 矿区资源
        for state in self._mine_resources.values():
            resource_type = state.resource_type
            if resource_type not in totals:
                totals[resource_type] = 0
            totals[resource_type] += state.estimated_quantity

        # 仓库库存
        for item_type, quantity in self._warehouse_inventory.items():
            if item_type not in totals:
                totals[item_type] = 0
            totals[item_type] += quantity

        return totals

    def compare_with_ground_truth(
        self,
        ground_truth: Dict[str, Any],
    ) -> Dict[str, float]:
        """
        与真实状态比较

        Args:
            ground_truth: 真实状态字典

        Returns:
            误差统计
        """
        errors = {}

        # 比较矿区资源
        if "mine_remaining" in ground_truth:
            for mine_name, true_quantity in ground_truth["mine_remaining"].items():
                if mine_name in self._mine_resources:
                    estimated = self._mine_resources[mine_name].estimated_quantity
                    error = abs(estimated - true_quantity) / max(1, true_quantity)
                    errors[f"mine_{mine_name}"] = error

        # 比较仓库库存
        if "warehouse_inventory" in ground_truth:
            for item_type, true_quantity in ground_truth["warehouse_inventory"].items():
                estimated = self._warehouse_inventory.get(item_type, 0)
                error = abs(estimated - true_quantity) / max(1, true_quantity)
                errors[f"warehouse_{item_type}"] = error

        return errors

    def get_summary(self) -> Dict[str, Any]:
        """
        获取状态摘要

        Returns:
            状态摘要字典
        """
        return {
            "mines": {
                name: state.to_dict()
                for name, state in self._mine_resources.items()
            },
            "warehouse": self._warehouse_inventory.copy(),
            "stations": {
                name: state.to_dict()
                for name, state in self._station_states.items()
            },
            "energy": self._energy_state.to_dict() if self._energy_state else None,
        }

    def reset(self):
        """重置所有状态"""
        self._mine_resources.clear()
        self._warehouse_inventory.clear()
        self._station_states.clear()
        self._energy_state = None
        self._observation_history.clear()
