"""
GENESIS Impedance Controller - 阻抗控制器

实现笛卡尔阻抗控制，用于精细装配操作。

功能:
- 笛卡尔阻抗控制
- 可调刚度和阻尼
- 力/力矩控制
- 柔顺操作支持
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import numpy as np
from numpy.typing import NDArray

from genesis.utils.geometry import SE3, SO3


class ImpedanceMode(Enum):
    """阻抗模式"""
    POSITION = "position"  # 位置控制
    FORCE = "force"  # 力控制
    COMPLIANT = "compliant"  # 柔顺控制
    ADMITTANCE = "admittance"  # 导纳控制


@dataclass
class ImpedanceParams:
    """阻抗参数"""
    # 平动刚度 (N/m)
    stiffness_linear: np.ndarray = field(default_factory=lambda: np.array([500.0, 500.0, 500.0]))
    # 转动刚度 (Nm/rad)
    stiffness_angular: np.ndarray = field(default_factory=lambda: np.array([50.0, 50.0, 50.0]))
    # 平动阻尼 (Ns/m)
    damping_linear: np.ndarray = field(default_factory=lambda: np.array([50.0, 50.0, 50.0]))
    # 转动阻尼 (Nms/rad)
    damping_angular: np.ndarray = field(default_factory=lambda: np.array([5.0, 5.0, 5.0]))
    # 平动质量 (kg)
    mass_linear: np.ndarray = field(default_factory=lambda: np.array([1.0, 1.0, 1.0]))
    # 转动惯量 (kg*m^2)
    inertia_angular: np.ndarray = field(default_factory=lambda: np.array([0.1, 0.1, 0.1]))

    @classmethod
    def stiff(cls) -> "ImpedanceParams":
        """创建刚性参数"""
        return cls(
            stiffness_linear=np.array([2000.0, 2000.0, 2000.0]),
            stiffness_angular=np.array([200.0, 200.0, 200.0]),
            damping_linear=np.array([100.0, 100.0, 100.0]),
            damping_angular=np.array([10.0, 10.0, 10.0]),
        )

    @classmethod
    def compliant(cls) -> "ImpedanceParams":
        """创建柔顺参数"""
        return cls(
            stiffness_linear=np.array([100.0, 100.0, 100.0]),
            stiffness_angular=np.array([10.0, 10.0, 10.0]),
            damping_linear=np.array([30.0, 30.0, 30.0]),
            damping_angular=np.array([3.0, 3.0, 3.0]),
        )

    @classmethod
    def insertion(cls) -> "ImpedanceParams":
        """创建插入操作参数"""
        return cls(
            stiffness_linear=np.array([100.0, 100.0, 500.0]),  # z 方向较硬
            stiffness_angular=np.array([20.0, 20.0, 50.0]),
            damping_linear=np.array([20.0, 20.0, 50.0]),
            damping_angular=np.array([5.0, 5.0, 10.0]),
        )


@dataclass
class ForceLimit:
    """力限制"""
    max_force: float = 50.0  # 最大力 (N)
    max_torque: float = 5.0  # 最大力矩 (Nm)
    force_threshold: float = 5.0  # 力阈值 (N)
    torque_threshold: float = 0.5  # 力矩阈值 (Nm)


@dataclass
class CartesianWrench:
    """笛卡尔力/力矩"""
    force: np.ndarray = field(default_factory=lambda: np.zeros(3))
    torque: np.ndarray = field(default_factory=lambda: np.zeros(3))

    @property
    def wrench(self) -> np.ndarray:
        """获取 6 维 wrench 向量"""
        return np.concatenate([self.force, self.torque])

    @classmethod
    def from_array(cls, arr: np.ndarray) -> "CartesianWrench":
        """从数组创建"""
        return cls(force=arr[:3], torque=arr[3:6])


class ImpedanceController:
    """
    笛卡尔阻抗控制器

    实现末端执行器的柔顺控制。
    """

    def __init__(
        self,
        params: ImpedanceParams = None,
        force_limit: ForceLimit = None,
    ):
        """
        初始化阻抗控制器

        Args:
            params: 阻抗参数
            force_limit: 力限制
        """
        self.params = params or ImpedanceParams()
        self.force_limit = force_limit or ForceLimit()

        # 目标状态
        self._target_pose: Optional[SE3] = None
        self._target_velocity: np.ndarray = np.zeros(6)
        self._target_wrench: CartesianWrench = CartesianWrench()

        # 当前状态
        self._current_pose: Optional[SE3] = None
        self._current_velocity: np.ndarray = np.zeros(6)
        self._current_wrench: CartesianWrench = CartesianWrench()

        # 控制模式
        self._mode = ImpedanceMode.POSITION

        # 雅可比矩阵回调
        self._jacobian_callback: Optional[Callable[[], np.ndarray]] = None

    def set_jacobian_callback(self, callback: Callable[[], np.ndarray]):
        """
        设置雅可比矩阵回调

        Args:
            callback: 返回雅可比矩阵的回调函数
        """
        self._jacobian_callback = callback

    def set_target_pose(self, pose: SE3, velocity: np.ndarray = None):
        """
        设置目标位姿

        Args:
            pose: 目标位姿
            velocity: 目标速度 (可选)
        """
        self._target_pose = pose
        self._target_velocity = velocity if velocity is not None else np.zeros(6)
        self._mode = ImpedanceMode.POSITION

    def set_target_wrench(self, wrench: CartesianWrench):
        """
        设置目标力/力矩

        Args:
            wrench: 目标 wrench
        """
        self._target_wrench = wrench
        self._mode = ImpedanceMode.FORCE

    def set_compliant_mode(self, stiffness: np.ndarray = None):
        """
        设置柔顺模式

        Args:
            stiffness: 刚度 (可选)
        """
        self._mode = ImpedanceMode.COMPLIANT
        if stiffness is not None:
            self.params.stiffness_linear = stiffness[:3]
            self.params.stiffness_angular = stiffness[3:6]

    def update(
        self,
        current_pose: SE3,
        current_velocity: np.ndarray = None,
        current_wrench: np.ndarray = None,
        dt: float = 0.01,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        更新控制器

        Args:
            current_pose: 当前位姿
            current_velocity: 当前速度 (6维)
            current_wrench: 当前 wrench (6维)
            dt: 时间步长

        Returns:
            (joint_torques, cartesian_wrench) 关节力矩和笛卡尔 wrench
        """
        self._current_pose = current_pose
        self._current_velocity = current_velocity if current_velocity is not None else np.zeros(6)

        if current_wrench is not None:
            self._current_wrench = CartesianWrench.from_array(current_wrench)

        # 计算误差
        pose_error = self._compute_pose_error()
        velocity_error = self._target_velocity - self._current_velocity

        # 阻抗控制律
        # F = K * (x_d - x) + D * (xd_d - xd) + M * (xdd_d - xdd)
        # 简化版: F = K * e_p + D * e_v

        # 位置误差力
        force = (
            self.params.stiffness_linear * pose_error[:3] +
            self.params.damping_linear * velocity_error[:3]
        )

        # 姿态误差力矩
        torque = (
            self.params.stiffness_angular * pose_error[3:6] +
            self.params.damping_angular * velocity_error[3:6]
        )

        # 根据模式调整
        if self._mode == ImpedanceMode.FORCE:
            # 力控制模式：添加目标 wrench
            force = force + self._target_wrench.force
            torque = torque + self._target_wrench.torque

        elif self._mode == ImpedanceMode.COMPLIANT:
            # 柔顺模式：使用当前 wrench 补偿
            force = force - self._current_wrench.force * 0.5
            torque = torque - self._current_wrench.torque * 0.5

        # 应用力限制
        force = np.clip(force, -self.force_limit.max_force, self.force_limit.max_force)
        torque = np.clip(torque, -self.force_limit.max_torque, self.force_limit.max_torque)

        # 组合 wrench
        wrench = np.concatenate([force, torque])

        # 转换到关节空间
        if self._jacobian_callback is not None:
            J = self._jacobian_callback()
            joint_torques = J.T @ wrench
        else:
            joint_torques = np.zeros(6)  # 需要雅可比矩阵

        return joint_torques, wrench

    def _compute_pose_error(self) -> np.ndarray:
        """
        计算位姿误差

        Returns:
            6 维误差向量 [位置误差, 姿态误差]
        """
        if self._target_pose is None or self._current_pose is None:
            return np.zeros(6)

        # 位置误差
        pos_error = np.array(self._target_pose.position) - np.array(self._current_pose.position)

        # 姿态误差
        R_target = self._target_pose.rotation.to_rotation_matrix()
        R_current = self._current_pose.rotation.to_rotation_matrix()
        R_error = R_target @ R_current.T

        # 提取轴角
        angle = np.arccos(np.clip((np.trace(R_error) - 1) / 2, -1, 1))

        if angle < 1e-6:
            ori_error = np.zeros(3)
        else:
            axis = np.array([
                R_error[2, 1] - R_error[1, 2],
                R_error[0, 2] - R_error[2, 0],
                R_error[1, 0] - R_error[0, 1]
            ]) / (2 * np.sin(angle))
            ori_error = axis * angle

        return np.concatenate([pos_error, ori_error])

    def compute_insertion_force(
        self,
        target_position: np.ndarray,
        current_position: np.ndarray,
        insertion_axis: np.ndarray = None,
        insertion_force: float = 10.0,
    ) -> np.ndarray:
        """
        计算插入力

        Args:
            target_position: 目标位置
            current_position: 当前位置
            insertion_axis: 插入方向 (默认 z 轴)
            insertion_force: 插入力大小

        Returns:
            力向量
        """
        if insertion_axis is None:
            insertion_axis = np.array([0, 0, 1])

        insertion_axis = insertion_axis / np.linalg.norm(insertion_axis)

        # 计算插入方向上的位置误差
        pos_error = target_position - current_position
        along_axis = np.dot(pos_error, insertion_axis)

        # 如果还在插入方向上，施加插入力
        if along_axis > 0:
            return insertion_axis * insertion_force
        else:
            return np.zeros(3)

    def check_force_limit(self) -> bool:
        """
        检查是否超过力限制

        Returns:
            是否超过限制
        """
        force_mag = np.linalg.norm(self._current_wrench.force)
        torque_mag = np.linalg.norm(self._current_wrench.torque)

        return (force_mag > self.force_limit.max_force or
                torque_mag > self.force_limit.max_torque)

    @property
    def mode(self) -> ImpedanceMode:
        """获取控制模式"""
        return self._mode

    @property
    def current_wrench(self) -> CartesianWrench:
        """获取当前 wrench"""
        return self._current_wrench

    def reset(self):
        """重置控制器"""
        self._target_pose = None
        self._target_velocity = np.zeros(6)
        self._target_wrench = CartesianWrench()
        self._current_pose = None
        self._current_velocity = np.zeros(6)
        self._current_wrench = CartesianWrench()
        self._mode = ImpedanceMode.POSITION


class ForceController:
    """
    力控制器

    实现简单的力控制。
    """

    def __init__(
        self,
        kp: float = 0.1,
        ki: float = 0.01,
        kd: float = 0.0,
        max_force: float = 50.0,
    ):
        """
        初始化力控制器

        Args:
            kp: 比例增益
            ki: 积分增益
            kd: 微分增益
            max_force: 最大力
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_force = max_force

        self._integral = 0.0
        self._prev_error = 0.0

    def compute(
        self,
        target_force: float,
        current_force: float,
        dt: float,
    ) -> float:
        """
        计算控制输出

        Args:
            target_force: 目标力
            current_force: 当前力
            dt: 时间步长

        Returns:
            位置修正量
        """
        error = target_force - current_force

        # PID
        self._integral += error * dt
        derivative = (error - self._prev_error) / dt if dt > 0 else 0

        output = self.kp * error + self.ki * self._integral + self.kd * derivative

        self._prev_error = error

        return np.clip(output, -self.max_force, self.max_force)

    def reset(self):
        """重置控制器"""
        self._integral = 0.0
        self._prev_error = 0.0


__all__ = [
    "ImpedanceMode",
    "ImpedanceParams",
    "ForceLimit",
    "CartesianWrench",
    "ImpedanceController",
    "ForceController",
]
