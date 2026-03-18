"""
GENESIS Path Follower - 路径跟踪控制器

实现 Pure Pursuit 路径跟踪算法，用于跟踪路径点序列。

功能:
- Pure Pursuit 算法
- 可调节的前视距离
- 路径点跟踪
- 到达检测
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


class FollowerState(Enum):
    """路径跟踪状态"""
    IDLE = "idle"
    FOLLOWING = "following"
    REACHED = "reached"
    ERROR = "error"


@dataclass
class PathFollowerConfig:
    """路径跟踪器配置"""
    lookahead_distance: float = 0.5  # 前视距离 (m)
    min_lookahead: float = 0.3  # 最小前视距离 (m)
    max_lookahead: float = 1.5  # 最大前视距离 (m)
    lookahead_gain: float = 0.3  # 前视距离增益 (与速度相关)
    goal_tolerance: float = 0.1  # 目标容差 (m)
    waypoint_tolerance: float = 0.15  # 路径点容差 (m)
    max_linear_speed: float = 1.5  # 最大线速度 (m/s)
    max_angular_speed: float = 1.0  # 最大角速度 (rad/s)
    goal_yaw_tolerance: float = 0.1  # 目标朝向容差 (rad)


@dataclass
class PathPoint:
    """路径点"""
    x: float
    y: float
    yaw: float = 0.0  # 期望朝向 (rad)
    speed: float = 1.0  # 期望速度 (m/s)

    def to_array(self) -> np.ndarray:
        """转换为 numpy 数组"""
        return np.array([self.x, self.y])

    @classmethod
    def from_tuple(cls, t: Tuple[float, float], yaw: float = 0.0, speed: float = 1.0) -> "PathPoint":
        """从元组创建"""
        return cls(t[0], t[1], yaw, speed)


class PurePursuitController:
    """
    Pure Pursuit 路径跟踪控制器

    实现经典的 Pure Pursuit 算法，用于跟踪路径。
    """

    def __init__(self, config: PathFollowerConfig):
        """
        初始化 Pure Pursuit 控制器

        Args:
            config: 配置参数
        """
        self.config = config

        # 路径
        self._path: List[PathPoint] = []
        self._current_waypoint_idx = 0

        # 状态
        self._state = FollowerState.IDLE
        self._lookahead_point: Optional[PathPoint] = None

    def set_path(self, path: List[PathPoint]):
        """
        设置路径

        Args:
            path: 路径点列表
        """
        if len(path) < 2:
            self._state = FollowerState.ERROR
            return

        self._path = path
        self._current_waypoint_idx = 0
        self._state = FollowerState.FOLLOWING
        self._lookahead_point = None

    def compute_velocity(
        self,
        current_x: float,
        current_y: float,
        current_yaw: float,
        current_speed: float = 0.0,
    ) -> Tuple[float, float]:
        """
        计算速度指令

        Args:
            current_x: 当前 x 坐标 (m)
            current_y: 当前 y 坐标 (m)
            current_yaw: 当前偏航角 (rad)
            current_speed: 当前速度 (m/s)

        Returns:
            (linear, angular) 速度指令
        """
        if self._state != FollowerState.FOLLOWING or len(self._path) < 2:
            return (0.0, 0.0)

        # 检查是否到达终点
        goal = self._path[-1]
        dist_to_goal = np.sqrt((goal.x - current_x)**2 + (goal.y - current_y)**2)

        if dist_to_goal < self.config.goal_tolerance:
            # 检查朝向
            yaw_error = self._normalize_angle(goal.yaw - current_yaw)
            if abs(yaw_error) < self.config.goal_yaw_tolerance:
                self._state = FollowerState.REACHED
                return (0.0, 0.0)

        # 计算自适应前视距离
        lookahead = self._compute_lookahead_distance(current_speed)

        # 找到前视点
        lookahead_point = self._find_lookahead_point(
            current_x, current_y, lookahead
        )

        if lookahead_point is None:
            return (0.0, 0.0)

        self._lookahead_point = lookahead_point

        # 计算到前视点的向量
        dx = lookahead_point.x - current_x
        dy = lookahead_point.y - current_y

        # 转换到机器人坐标系
        local_x = dx * np.cos(current_yaw) + dy * np.sin(current_yaw)
        local_y = -dx * np.sin(current_yaw) + dy * np.cos(current_yaw)

        # 计算曲率
        if abs(local_x) < 1e-6:
            curvature = 0.0
        else:
            # Pure Pursuit 公式
            L = np.sqrt(local_x**2 + local_y**2)
            curvature = 2 * local_y / (L * L)

        # 计算速度
        target_speed = self._get_target_speed()
        linear_speed = min(target_speed, self.config.max_linear_speed)

        # 计算角速度
        angular_speed = np.clip(
            curvature * linear_speed,
            -self.config.max_angular_speed,
            self.config.max_angular_speed
        )

        return (linear_speed, angular_speed)

    def _compute_lookahead_distance(self, speed: float) -> float:
        """
        计算自适应前视距离

        Args:
            speed: 当前速度 (m/s)

        Returns:
            前视距离 (m)
        """
        # 前视距离与速度成正比
        lookahead = self.config.lookahead_distance + self.config.lookahead_gain * speed
        return np.clip(
            lookahead,
            self.config.min_lookahead,
            self.config.max_lookahead
        )

    def _find_lookahead_point(
        self,
        x: float,
        y: float,
        lookahead: float
    ) -> Optional[PathPoint]:
        """
        找到前视点

        Args:
            x: 当前 x 坐标
            y: 当前 y 坐标
            lookahead: 前视距离

        Returns:
            前视点，如果未找到返回 None
        """
        # 更新当前路径点
        while self._current_waypoint_idx < len(self._path) - 1:
            wp = self._path[self._current_waypoint_idx]
            dist = np.sqrt((wp.x - x)**2 + (wp.y - y)**2)

            if dist < self.config.waypoint_tolerance:
                self._current_waypoint_idx += 1
            else:
                break

        # 在当前路径点和下一个路径点之间寻找前视点
        if self._current_waypoint_idx >= len(self._path) - 1:
            return self._path[-1]

        # 检查从当前位置到每个路径点的距离
        for i in range(self._current_waypoint_idx, len(self._path) - 1):
            p1 = self._path[i]
            p2 = self._path[i + 1]

            # 在线段上寻找前视点
            point = self._find_lookahead_on_segment(
                x, y, lookahead,
                p1.x, p1.y, p2.x, p2.y
            )

            if point is not None:
                return PathPoint(point[0], point[1])

        # 返回最后一个点
        return self._path[-1]

    def _find_lookahead_on_segment(
        self,
        x: float, y: float, lookahead: float,
        x1: float, y1: float, x2: float, y2: float
    ) -> Optional[Tuple[float, float]]:
        """
        在线段上寻找前视点

        Args:
            x, y: 当前位置
            lookahead: 前视距离
            x1, y1: 线段起点
            x2, y2: 线段终点

        Returns:
            前视点坐标，如果未找到返回 None
        """
        # 线段向量
        dx = x2 - x1
        dy = y2 - y1

        # 线段长度
        seg_len = np.sqrt(dx*dx + dy*dy)
        if seg_len < 1e-6:
            return None

        # 单位向量
        ux = dx / seg_len
        uy = dy / seg_len

        # 从当前位置到线段起点的向量
        ax = x - x1
        ay = y - y1

        # 投影到线段上
        proj = ax * ux + ay * uy
        proj = np.clip(proj, 0, seg_len)

        # 最近点
        closest_x = x1 + proj * ux
        closest_y = y1 + proj * uy

        # 到最近点的距离
        dist_to_closest = np.sqrt((x - closest_x)**2 + (y - closest_y)**2)

        # 前视距离与最近点距离的关系
        if dist_to_closest > lookahead:
            return None

        # 计算沿线的距离
        along_line = np.sqrt(lookahead**2 - dist_to_closest**2)

        # 前视点位置
        lookahead_proj = proj + along_line

        if lookahead_proj > seg_len:
            # 超出当前线段
            return None

        lookahead_x = x1 + lookahead_proj * ux
        lookahead_y = y1 + lookahead_proj * uy

        return (lookahead_x, lookahead_y)

    def _get_target_speed(self) -> float:
        """获取目标速度"""
        if self._current_waypoint_idx < len(self._path):
            return self._path[self._current_waypoint_idx].speed
        return 1.0

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """归一化角度到 [-pi, pi]"""
        while angle > np.pi:
            angle -= 2 * np.pi
        while angle < -np.pi:
            angle += 2 * np.pi
        return angle

    @property
    def state(self) -> FollowerState:
        """获取状态"""
        return self._state

    @property
    def current_waypoint_idx(self) -> int:
        """获取当前路径点索引"""
        return self._current_waypoint_idx

    @property
    def lookahead_point(self) -> Optional[PathPoint]:
        """获取前视点"""
        return self._lookahead_point

    def reset(self):
        """重置控制器"""
        self._path = []
        self._current_waypoint_idx = 0
        self._state = FollowerState.IDLE
        self._lookahead_point = None


class PathFollower:
    """
    路径跟踪器

    高级路径跟踪接口，结合 Pure Pursuit 和速度控制。
    """

    def __init__(self, config: PathFollowerConfig):
        """
        初始化路径跟踪器

        Args:
            config: 配置参数
        """
        self.config = config
        self.pure_pursuit = PurePursuitController(config)

        # 状态
        self._path: List[PathPoint] = []
        self._state = FollowerState.IDLE

    def set_path(self, path: List[PathPoint]):
        """
        设置路径

        Args:
            path: 路径点列表
        """
        self._path = path
        self.pure_pursuit.set_path(path)
        self._state = self.pure_pursuit.state

    def set_path_from_tuples(self, path: List[Tuple[float, float]]):
        """
        从元组列表设置路径

        Args:
            path: (x, y) 元组列表
        """
        path_points = [PathPoint(p[0], p[1]) for p in path]
        self.set_path(path_points)

    def update(
        self,
        current_x: float,
        current_y: float,
        current_yaw: float,
        current_speed: float = 0.0,
    ) -> Tuple[float, float]:
        """
        更新并获取速度指令

        Args:
            current_x: 当前 x 坐标 (m)
            current_y: 当前 y 坐标 (m)
            current_yaw: 当前偏航角 (rad)
            current_speed: 当前速度 (m/s)

        Returns:
            (linear, angular) 速度指令
        """
        linear, angular = self.pure_pursuit.compute_velocity(
            current_x, current_y, current_yaw, current_speed
        )
        self._state = self.pure_pursuit.state
        return (linear, angular)

    def get_progress(self) -> float:
        """
        获取路径进度

        Returns:
            进度 (0.0 - 1.0)
        """
        if len(self._path) < 2:
            return 0.0

        return self.pure_pursuit.current_waypoint_idx / (len(self._path) - 1)

    @property
    def state(self) -> FollowerState:
        """获取状态"""
        return self._state

    @property
    def is_following(self) -> bool:
        """是否正在跟踪"""
        return self._state == FollowerState.FOLLOWING

    @property
    def reached_goal(self) -> bool:
        """是否到达目标"""
        return self._state == FollowerState.REACHED

    def reset(self):
        """重置"""
        self.pure_pursuit.reset()
        self._path = []
        self._state = FollowerState.IDLE


__all__ = [
    "FollowerState",
    "PathFollowerConfig",
    "PathPoint",
    "PurePursuitController",
    "PathFollower",
]
