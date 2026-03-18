"""
GENESIS Base Controller - 底盘基础运动控制

实现差速驱动底盘的运动控制，包括:
- 差速驱动运动学
- PID 速度跟踪控制器
- 速度限制和加速度限制

注意: 此文件是对 robot_interface.py 中 BaseController 的扩展，
提供更完整的运动控制功能。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Tuple, List
import numpy as np


class MotionState(Enum):
    """运动状态"""
    IDLE = "idle"
    MOVING = "moving"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class PIDGains:
    """PID 控制器增益"""
    kp: float = 1.0  # 比例增益
    ki: float = 0.0  # 积分增益
    kd: float = 0.0  # 微分增益
    i_max: float = 1.0  # 积分限幅


@dataclass
class MotionConstraints:
    """运动约束"""
    max_linear_speed: float = 1.5  # 最大线速度 (m/s)
    max_angular_speed: float = 1.0  # 最大角速度 (rad/s)
    max_linear_accel: float = 2.0  # 最大线加速度 (m/s²)
    max_angular_accel: float = 2.0  # 最大角加速度 (rad/s²)
    linear_tolerance: float = 0.01  # 线速度容差 (m/s)
    angular_tolerance: float = 0.01  # 角速度容差 (rad/s)


@dataclass
class VelocityCommand:
    """速度指令"""
    linear: float = 0.0  # 线速度 (m/s)
    angular: float = 0.0  # 角速度 (rad/s)
    timestamp: float = 0.0  # 时间戳


@dataclass
class WheelVelocities:
    """四轮速度"""
    front_left: float = 0.0  # 前左轮速度 (rad/s)
    front_right: float = 0.0  # 前右轮速度 (rad/s)
    rear_left: float = 0.0  # 后左轮速度 (rad/s)
    rear_right: float = 0.0  # 后右轮速度 (rad/s)

    def to_tuple(self) -> Tuple[float, float, float, float]:
        """转换为元组"""
        return (self.front_left, self.front_right, self.rear_left, self.rear_right)

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float, float]) -> "WheelVelocities":
        """从元组创建"""
        return cls(t[0], t[1], t[2], t[3])


class PIDController:
    """
    PID 控制器

    实现带积分限幅的标准 PID 控制器。
    """

    def __init__(self, gains: PIDGains):
        """
        初始化 PID 控制器

        Args:
            gains: PID 增益参数
        """
        self.gains = gains
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time: Optional[float] = None

    def compute(self, error: float, dt: float) -> float:
        """
        计算 PID 输出

        Args:
            error: 误差值
            dt: 时间步长 (s)

        Returns:
            控制输出
        """
        if dt <= 0:
            return 0.0

        # 比例项
        p_term = self.gains.kp * error

        # 积分项 (带限幅)
        self._integral += error * dt
        self._integral = np.clip(self._integral, -self.gains.i_max, self.gains.i_max)
        i_term = self.gains.ki * self._integral

        # 微分项
        derivative = (error - self._prev_error) / dt
        d_term = self.gains.kd * derivative

        # 更新状态
        self._prev_error = error

        return p_term + i_term + d_term

    def reset(self):
        """重置控制器状态"""
        self._integral = 0.0
        self._prev_error = 0.0
        self._prev_time = None


class DifferentialDriveController:
    """
    差速驱动控制器

    实现差速驱动底盘的运动学和控制。
    """

    def __init__(
        self,
        wheel_base: float = 0.5,
        wheel_radius: float = 0.08,
        constraints: Optional[MotionConstraints] = None,
        linear_pid: Optional[PIDGains] = None,
        angular_pid: Optional[PIDGains] = None,
    ):
        """
        初始化差速驱动控制器

        Args:
            wheel_base: 轮距 (m)
            wheel_radius: 轮子半径 (m)
            constraints: 运动约束
            linear_pid: 线速度 PID 增益
            angular_pid: 角速度 PID 增益
        """
        self.wheel_base = wheel_base
        self.wheel_radius = wheel_radius

        # 运动约束
        self.constraints = constraints or MotionConstraints()

        # PID 控制器
        self.linear_pid = PIDController(linear_pid or PIDGains(kp=2.0, ki=0.1, kd=0.05))
        self.angular_pid = PIDController(angular_pid or PIDGains(kp=3.0, ki=0.2, kd=0.1))

        # 状态
        self._current_velocity = VelocityCommand()
        self._target_velocity = VelocityCommand()
        self._state = MotionState.IDLE

        # 实际速度 (来自编码器或仿真)
        self._actual_linear = 0.0
        self._actual_angular = 0.0

    def set_target_velocity(self, linear: float, angular: float):
        """
        设置目标速度

        Args:
            linear: 目标线速度 (m/s)
            angular: 目标角速度 (rad/s)
        """
        # 应用速度限制
        linear = np.clip(
            linear,
            -self.constraints.max_linear_speed,
            self.constraints.max_linear_speed
        )
        angular = np.clip(
            angular,
            -self.constraints.max_angular_speed,
            self.constraints.max_angular_speed
        )

        self._target_velocity = VelocityCommand(linear, angular)
        self._state = MotionState.MOVING

    def stop(self, gradual: bool = True):
        """
        停止运动

        Args:
            gradual: 是否逐渐停止
        """
        if gradual:
            self._state = MotionState.STOPPING
        else:
            self._target_velocity = VelocityCommand()
            self._current_velocity = VelocityCommand()
            self._state = MotionState.IDLE

    def update(self, dt: float, actual_linear: float = None, actual_angular: float = None):
        """
        更新控制器

        Args:
            dt: 时间步长 (s)
            actual_linear: 实际线速度 (来自编码器)
            actual_angular: 实际角速度 (来自编码器)
        """
        # 更新实际速度
        if actual_linear is not None:
            self._actual_linear = actual_linear
        if actual_angular is not None:
            self._actual_angular = actual_angular

        # 处理停止状态
        if self._state == MotionState.STOPPING:
            # 逐渐减速
            self._target_velocity.linear *= 0.9
            self._target_velocity.angular *= 0.9

            if (abs(self._current_velocity.linear) < self.constraints.linear_tolerance and
                abs(self._current_velocity.angular) < self.constraints.angular_tolerance):
                self._state = MotionState.IDLE
                self._current_velocity = VelocityCommand()
                return

        # 计算速度误差
        linear_error = self._target_velocity.linear - self._actual_linear
        angular_error = self._target_velocity.angular - self._actual_angular

        # PID 控制
        linear_correction = self.linear_pid.compute(linear_error, dt)
        angular_correction = self.angular_pid.compute(angular_error, dt)

        # 应用加速度限制
        target_linear = self._current_velocity.linear + linear_correction * dt
        target_angular = self._current_velocity.angular + angular_correction * dt

        # 限制加速度
        linear_diff = np.clip(
            target_linear - self._current_velocity.linear,
            -self.constraints.max_linear_accel * dt,
            self.constraints.max_linear_accel * dt
        )
        angular_diff = np.clip(
            target_angular - self._current_velocity.angular,
            -self.constraints.max_angular_accel * dt,
            self.constraints.max_angular_accel * dt
        )

        # 更新当前速度
        self._current_velocity.linear += linear_diff
        self._current_velocity.angular += angular_diff

    def get_wheel_velocities(self) -> WheelVelocities:
        """
        计算四轮速度

        Returns:
            四轮速度 (rad/s)
        """
        linear = self._current_velocity.linear
        angular = self._current_velocity.angular

        # 差速驱动运动学
        v_left = linear - angular * self.wheel_base / 2
        v_right = linear + angular * self.wheel_base / 2

        # 转换为轮子角速度
        w_left = v_left / self.wheel_radius
        w_right = v_right / self.wheel_radius

        # 四轮配置，前后轮同速
        return WheelVelocities(
            front_left=w_left,
            front_right=w_right,
            rear_left=w_left,
            rear_right=w_right
        )

    def get_velocity_command(self) -> VelocityCommand:
        """获取当前速度指令"""
        return self._current_velocity

    @property
    def state(self) -> MotionState:
        """获取运动状态"""
        return self._state

    @property
    def is_moving(self) -> bool:
        """是否正在移动"""
        return self._state in (MotionState.MOVING, MotionState.STOPPING)

    def reset(self):
        """重置控制器"""
        self.linear_pid.reset()
        self.angular_pid.reset()
        self._current_velocity = VelocityCommand()
        self._target_velocity = VelocityCommand()
        self._actual_linear = 0.0
        self._actual_angular = 0.0
        self._state = MotionState.IDLE


class OdometryEstimator:
    """
    里程计估计器

    从轮子编码器数据估计机器人位姿。
    """

    def __init__(self, wheel_base: float = 0.5, wheel_radius: float = 0.08):
        """
        初始化里程计估计器

        Args:
            wheel_base: 轮距 (m)
            wheel_radius: 轮子半径 (m)
        """
        self.wheel_base = wheel_base
        self.wheel_radius = wheel_radius

        # 位姿状态
        self._x = 0.0
        self._y = 0.0
        self._yaw = 0.0

        # 速度状态
        self._linear_vel = 0.0
        self._angular_vel = 0.0

        # 上一次的轮子位置
        self._prev_left_pos = 0.0
        self._prev_right_pos = 0.0
        self._initialized = False

    def update(self, left_pos: float, right_pos: float, dt: float):
        """
        更新里程计

        Args:
            left_pos: 左轮位置 (rad)
            right_pos: 右轮位置 (rad)
            dt: 时间步长 (s)
        """
        if not self._initialized:
            self._prev_left_pos = left_pos
            self._prev_right_pos = right_pos
            self._initialized = True
            return

        # 计算轮子位移
        left_delta = left_pos - self._prev_left_pos
        right_delta = right_pos - self._prev_right_pos

        self._prev_left_pos = left_pos
        self._prev_right_pos = right_pos

        # 计算线位移和角位移
        left_dist = left_delta * self.wheel_radius
        right_dist = right_delta * self.wheel_radius

        linear_dist = (left_dist + right_dist) / 2
        angular_dist = (right_dist - left_dist) / self.wheel_base

        # 更新位姿
        if abs(angular_dist) < 1e-6:
            # 直线运动
            self._x += linear_dist * np.cos(self._yaw)
            self._y += linear_dist * np.sin(self._yaw)
        else:
            # 弧线运动
            radius = linear_dist / angular_dist
            self._x += radius * (np.sin(self._yaw + angular_dist) - np.sin(self._yaw))
            self._y += radius * (np.cos(self._yaw) - np.cos(self._yaw + angular_dist))

        self._yaw += angular_dist

        # 归一化角度到 [-pi, pi]
        self._yaw = np.arctan2(np.sin(self._yaw), np.cos(self._yaw))

        # 计算速度
        if dt > 0:
            self._linear_vel = linear_dist / dt
            self._angular_vel = angular_dist / dt

    def get_pose(self) -> Tuple[float, float, float]:
        """
        获取当前位姿

        Returns:
            (x, y, yaw) 元组
        """
        return (self._x, self._y, self._yaw)

    def get_velocity(self) -> Tuple[float, float]:
        """
        获取当前速度

        Returns:
            (linear, angular) 元组
        """
        return (self._linear_vel, self._angular_vel)

    def set_pose(self, x: float, y: float, yaw: float):
        """
        设置位姿 (用于重置或外部校正)

        Args:
            x: x 坐标 (m)
            y: y 坐标 (m)
            yaw: 偏航角 (rad)
        """
        self._x = x
        self._y = y
        self._yaw = yaw

    def reset(self):
        """重置里程计"""
        self._x = 0.0
        self._y = 0.0
        self._yaw = 0.0
        self._linear_vel = 0.0
        self._angular_vel = 0.0
        self._initialized = False


# 为了向后兼容，提供 BaseController 别名
# 注意: 更完整的实现在 robot_interface.py 中
__all__ = [
    "MotionState",
    "PIDGains",
    "MotionConstraints",
    "VelocityCommand",
    "WheelVelocities",
    "PIDController",
    "DifferentialDriveController",
    "OdometryEstimator",
]
