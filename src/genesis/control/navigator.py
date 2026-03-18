"""
GENESIS Navigator - 全局导航接口

提供高级导航功能，整合路径规划和路径跟踪。

功能:
- 区域到区域导航
- 点到点导航
- 电量检查和自动充电
- 导航状态管理
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import numpy as np

from genesis.control.path_follower import (
    PathFollower,
    PathFollowerConfig,
    PathPoint,
    FollowerState,
)
from genesis.world.path_network import PathNetwork, PathNode


class NavigationStatus(Enum):
    """导航状态"""
    IDLE = "idle"
    PLANNING = "planning"
    NAVIGATING = "navigating"
    REACHED = "reached"
    FAILED = "failed"
    LOW_BATTERY = "low_battery"
    CHARGING = "charging"


@dataclass
class NavigationGoal:
    """导航目标"""
    target_zone: Optional[str] = None
    target_position: Optional[Tuple[float, float]] = None
    target_yaw: Optional[float] = None
    speed: float = 1.0  # 目标速度 (m/s)

    def is_valid(self) -> bool:
        """检查目标是否有效"""
        return self.target_zone is not None or self.target_position is not None


@dataclass
class NavigationConfig:
    """导航配置"""
    default_speed: float = 1.0  # 默认速度 (m/s)
    low_battery_threshold: float = 0.15  # 低电量阈值
    critical_battery_threshold: float = 0.05  # 临界电量阈值
    position_tolerance: float = 0.1  # 位置容差 (m)
    yaw_tolerance: float = 0.1  # 朝向容差 (rad)
    max_retries: int = 3  # 最大重试次数
    retry_delay: float = 1.0  # 重试延迟 (s)


@dataclass
class NavigationState:
    """导航状态数据"""
    status: NavigationStatus = NavigationStatus.IDLE
    current_goal: Optional[NavigationGoal] = None
    path: List[PathPoint] = field(default_factory=list)
    progress: float = 0.0
    distance_remaining: float = 0.0
    time_elapsed: float = 0.0
    error_message: str = ""


class Navigator:
    """
    全局导航器

    提供高级导航接口，整合路径规划和跟踪。
    """

    def __init__(
        self,
        path_network: PathNetwork,
        path_follower_config: Optional[PathFollowerConfig] = None,
        config: Optional[NavigationConfig] = None,
    ):
        """
        初始化导航器

        Args:
            path_network: 路径网络
            path_follower_config: 路径跟踪器配置
            config: 导航配置
        """
        self.path_network = path_network
        self.config = config or NavigationConfig()

        # 路径跟踪器
        pf_config = path_follower_config or PathFollowerConfig()
        self.path_follower = PathFollower(pf_config)

        # 状态
        self._state = NavigationState()
        self._cancel_flag = False

        # 回调
        self._on_status_change: Optional[Callable[[NavigationStatus], None]] = None
        self._on_progress: Optional[Callable[[float], None]] = None

        # 电池检查函数 (由外部设置)
        self._get_battery_soc: Optional[Callable[[], float]] = None

    def set_battery_callback(self, callback: Callable[[], float]):
        """
        设置电池电量回调

        Args:
            callback: 返回电池 SOC (0-1) 的回调函数
        """
        self._get_battery_soc = callback

    def set_status_callback(self, callback: Callable[[NavigationStatus], None]):
        """
        设置状态变化回调

        Args:
            callback: 状态变化回调函数
        """
        self._on_status_change = callback

    def set_progress_callback(self, callback: Callable[[float], None]):
        """
        设置进度回调

        Args:
            callback: 进度回调函数 (0.0 - 1.0)
        """
        self._on_progress = callback

    def navigate_to_zone(
        self,
        zone_name: str,
        speed: float = None,
    ) -> bool:
        """
        导航到指定区域

        Args:
            zone_name: 目标区域名称
            speed: 目标速度 (m/s)

        Returns:
            是否成功开始导航
        """
        goal = NavigationGoal(
            target_zone=zone_name,
            speed=speed or self.config.default_speed
        )
        return self._start_navigation(goal)

    def navigate_to_position(
        self,
        x: float,
        y: float,
        yaw: float = None,
        speed: float = None,
    ) -> bool:
        """
        导航到指定位置

        Args:
            x: 目标 x 坐标 (m)
            y: 目标 y 坐标 (m)
            yaw: 目标朝向 (rad)
            speed: 目标速度 (m/s)

        Returns:
            是否成功开始导航
        """
        goal = NavigationGoal(
            target_position=(x, y),
            target_yaw=yaw,
            speed=speed or self.config.default_speed
        )
        return self._start_navigation(goal)

    def _start_navigation(self, goal: NavigationGoal) -> bool:
        """
        开始导航

        Args:
            goal: 导航目标

        Returns:
            是否成功开始
        """
        if not goal.is_valid():
            self._set_status(NavigationStatus.FAILED, "Invalid navigation goal")
            return False

        # 检查电量
        if self._get_battery_soc:
            soc = self._get_battery_soc()
            if soc < self.config.critical_battery_threshold:
                self._set_status(
                    NavigationStatus.LOW_BATTERY,
                    f"Critical battery level: {soc*100:.1f}%"
                )
                return False

        # 设置状态
        self._state.current_goal = goal
        self._set_status(NavigationStatus.PLANNING)

        # 规划路径
        path = self._plan_path(goal)
        if not path:
            self._set_status(NavigationStatus.FAILED, "Failed to plan path")
            return False

        # 设置路径
        self._state.path = path
        self.path_follower.set_path(path)

        # 开始导航
        self._set_status(NavigationStatus.NAVIGATING)
        self._cancel_flag = False

        return True

    def _plan_path(self, goal: NavigationGoal) -> List[PathPoint]:
        """
        规划路径

        Args:
            goal: 导航目标

        Returns:
            路径点列表
        """
        if goal.target_zone:
            # 区域导航
            target_node = self.path_network.get_node_by_zone(goal.target_zone)
            if target_node is None:
                return []

            # 从当前位置规划到目标区域
            # 注意: 实际实现需要知道当前位置
            # 这里返回空路径，由 update 方法处理
            return [PathPoint(
                target_node.position[0],
                target_node.position[1],
                yaw=0.0,
                speed=goal.speed
            )]

        elif goal.target_position:
            # 点到点导航
            return [PathPoint(
                goal.target_position[0],
                goal.target_position[1],
                yaw=goal.target_yaw or 0.0,
                speed=goal.speed
            )]

        return []

    def plan_path_from_zone(
        self,
        start_zone: str,
        end_zone: str,
        speed: float = None,
    ) -> List[PathPoint]:
        """
        从起点区域规划到终点区域

        Args:
            start_zone: 起点区域名称
            end_zone: 终点区域名称
            speed: 目标速度 (m/s)

        Returns:
            路径点列表
        """
        path_nodes = self.path_network.plan_path(start_zone, end_zone)
        if not path_nodes:
            return []

        speed = speed or self.config.default_speed
        return [
            PathPoint(
                node.position[0],
                node.position[1],
                speed=speed
            )
            for node in path_nodes
        ]

    def update(
        self,
        current_x: float,
        current_y: float,
        current_yaw: float,
        current_speed: float = 0.0,
        dt: float = 0.01,
    ) -> Tuple[float, float]:
        """
        更新导航状态并获取速度指令

        Args:
            current_x: 当前 x 坐标 (m)
            current_y: 当前 y 坐标 (m)
            current_yaw: 当前偏航角 (rad)
            current_speed: 当前速度 (m/s)
            dt: 时间步长 (s)

        Returns:
            (linear, angular) 速度指令
        """
        if self._state.status not in (NavigationStatus.NAVIGATING, NavigationStatus.PLANNING):
            return (0.0, 0.0)

        if self._cancel_flag:
            self._set_status(NavigationStatus.IDLE, "Navigation cancelled")
            return (0.0, 0.0)

        # 检查电量
        if self._get_battery_soc:
            soc = self._get_battery_soc()
            if soc < self.config.low_battery_threshold:
                self._set_status(
                    NavigationStatus.LOW_BATTERY,
                    f"Low battery level: {soc*100:.1f}%"
                )
                return (0.0, 0.0)

        # 更新路径跟踪器
        linear, angular = self.path_follower.update(
            current_x, current_y, current_yaw, current_speed
        )

        # 更新进度
        self._state.progress = self.path_follower.get_progress()
        self._state.time_elapsed += dt

        if self._on_progress:
            self._on_progress(self._state.progress)

        # 检查是否到达
        if self.path_follower.reached_goal:
            self._set_status(NavigationStatus.REACHED)

        return (linear, angular)

    def cancel(self):
        """取消当前导航"""
        self._cancel_flag = True
        self.path_follower.reset()

    def _set_status(self, status: NavigationStatus, message: str = ""):
        """
        设置状态

        Args:
            status: 新状态
            message: 状态消息
        """
        old_status = self._state.status
        self._state.status = status
        self._state.error_message = message

        if old_status != status and self._on_status_change:
            self._on_status_change(status)

    @property
    def status(self) -> NavigationStatus:
        """获取当前状态"""
        return self._state.status

    @property
    def is_navigating(self) -> bool:
        """是否正在导航"""
        return self._state.status in (
            NavigationStatus.PLANNING,
            NavigationStatus.NAVIGATING
        )

    @property
    def reached_goal(self) -> bool:
        """是否到达目标"""
        return self._state.status == NavigationStatus.REACHED

    @property
    def progress(self) -> float:
        """获取进度"""
        return self._state.progress

    @property
    def state(self) -> NavigationState:
        """获取完整状态"""
        return self._state

    def reset(self):
        """重置导航器"""
        self.path_follower.reset()
        self._state = NavigationState()
        self._cancel_flag = False


class AsyncNavigator(Navigator):
    """
    异步导航器

    提供异步导航接口，支持 await 操作。
    """

    async def navigate_to_zone_async(
        self,
        zone_name: str,
        speed: float = None,
        timeout: float = 300.0,
        update_callback: Optional[Callable[[float, float, float], Tuple[float, float]]] = None,
    ) -> bool:
        """
        异步导航到指定区域

        Args:
            zone_name: 目标区域名称
            speed: 目标速度 (m/s)
            timeout: 超时时间 (s)
            update_callback: 更新回调函数，接收 (x, y, yaw)，返回 (linear, angular)

        Returns:
            是否成功到达
        """
        if not self.navigate_to_zone(zone_name, speed):
            return False

        start_time = asyncio.get_event_loop().time()

        while self.is_navigating:
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.cancel()
                self._set_status(NavigationStatus.FAILED, "Navigation timeout")
                return False

            await asyncio.sleep(0.01)

        return self.reached_goal

    async def navigate_to_position_async(
        self,
        x: float,
        y: float,
        yaw: float = None,
        speed: float = None,
        timeout: float = 300.0,
    ) -> bool:
        """
        异步导航到指定位置

        Args:
            x: 目标 x 坐标 (m)
            y: 目标 y 坐标 (m)
            yaw: 目标朝向 (rad)
            speed: 目标速度 (m/s)
            timeout: 超时时间 (s)

        Returns:
            是否成功到达
        """
        if not self.navigate_to_position(x, y, yaw, speed):
            return False

        start_time = asyncio.get_event_loop().time()

        while self.is_navigating:
            if asyncio.get_event_loop().time() - start_time > timeout:
                self.cancel()
                self._set_status(NavigationStatus.FAILED, "Navigation timeout")
                return False

            await asyncio.sleep(0.01)

        return self.reached_goal


__all__ = [
    "NavigationStatus",
    "NavigationGoal",
    "NavigationConfig",
    "NavigationState",
    "Navigator",
    "AsyncNavigator",
]
