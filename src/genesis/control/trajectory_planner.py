"""
GENESIS Trajectory Planner - 轨迹规划器

实现机械臂的轨迹规划，包括:
- 关节空间轨迹 (五次多项式)
- 笛卡尔空间轨迹 (直线插值)
- 碰撞检测接口
- 轨迹执行器

支持平滑、无冲击的运动。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import numpy as np
from numpy.typing import NDArray

from genesis.utils.geometry import SE3, SO3


class TrajectoryStatus(Enum):
    """轨迹状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    PAUSED = "paused"
    FAILED = "failed"


@dataclass
class TrajectoryPoint:
    """轨迹点"""
    time: float  # 时间 (s)
    position: np.ndarray  # 位置
    velocity: np.ndarray  # 速度
    acceleration: np.ndarray  # 加速度

    def __post_init__(self):
        self.position = np.asarray(self.position, dtype=np.float64)
        self.velocity = np.asarray(self.velocity, dtype=np.float64)
        self.acceleration = np.asarray(self.acceleration, dtype=np.float64)


@dataclass
class JointTrajectory:
    """关节轨迹"""
    points: List[TrajectoryPoint] = field(default_factory=list)
    joint_names: List[str] = field(default_factory=list)
    duration: float = 0.0

    def get_point_at_time(self, t: float) -> Optional[TrajectoryPoint]:
        """
        获取指定时间的轨迹点

        Args:
            t: 时间 (s)

        Returns:
            轨迹点，如果超出范围返回 None
        """
        if not self.points or t < 0 or t > self.duration:
            return None

        # 找到最近的两个点
        for i in range(len(self.points) - 1):
            if self.points[i].time <= t <= self.points[i + 1].time:
                # 线性插值
                p1, p2 = self.points[i], self.points[i + 1]
                alpha = (t - p1.time) / (p2.time - p1.time) if p2.time > p1.time else 0

                return TrajectoryPoint(
                    time=t,
                    position=(1 - alpha) * p1.position + alpha * p2.position,
                    velocity=(1 - alpha) * p1.velocity + alpha * p2.velocity,
                    acceleration=(1 - alpha) * p1.acceleration + alpha * p2.acceleration,
                )

        # 返回最后一个点
        return self.points[-1] if self.points else None


@dataclass
class CartesianTrajectory:
    """笛卡尔轨迹"""
    points: List[Tuple[float, SE3, np.ndarray, np.ndarray]] = field(default_factory=list)
    # (time, pose, velocity, acceleration)
    duration: float = 0.0

    def get_pose_at_time(self, t: float) -> Optional[SE3]:
        """
        获取指定时间的位姿

        Args:
            t: 时间 (s)

        Returns:
            位姿，如果超出范围返回 None
        """
        if not self.points or t < 0 or t > self.duration:
            return None

        # 找到最近的两个点
        for i in range(len(self.points) - 1):
            t1, pose1, _, _ = self.points[i]
            t2, pose2, _, _ = self.points[i + 1]

            if t1 <= t <= t2:
                alpha = (t - t1) / (t2 - t1) if t2 > t1 else 0

                # 插值位置
                pos = (1 - alpha) * np.array(pose1.position) + alpha * np.array(pose2.position)

                # 插值姿态 (使用球面线性插值)
                rot = self._slerp(pose1.rotation, pose2.rotation, alpha)

                return SE3(tuple(pos), rot)

        # 返回最后一个位姿
        return self.points[-1][1] if self.points else None

    @staticmethod
    def _slerp(rot1: SO3, rot2: SO3, alpha: float) -> SO3:
        """
        球面线性插值

        Args:
            rot1: 起始旋转
            rot2: 终止旋转
            alpha: 插值参数 [0, 1]

        Returns:
            插值旋转
        """
        q1 = np.array(rot1.quaternion)
        q2 = np.array(rot2.quaternion)

        # 计算点积
        dot = np.dot(q1, q2)

        # 如果点积为负，取反以选择较短的路径
        if dot < 0:
            q2 = -q2
            dot = -dot

        # 如果四元数非常接近，使用线性插值
        if dot > 0.9995:
            result = q1 + alpha * (q2 - q1)
            result /= np.linalg.norm(result)
            return SO3(tuple(result))

        # 球面线性插值
        theta = np.arccos(dot)
        sin_theta = np.sin(theta)

        w1 = np.sin((1 - alpha) * theta) / sin_theta
        w2 = np.sin(alpha * theta) / sin_theta

        result = w1 * q1 + w2 * q2
        result /= np.linalg.norm(result)

        return SO3(tuple(result))


@dataclass
class TrajectoryConstraints:
    """轨迹约束"""
    max_velocity: np.ndarray  # 最大速度
    max_acceleration: np.ndarray  # 最大加速度
    max_jerk: Optional[np.ndarray] = None  # 最大加加速度 (可选)


class QuinticPolynomial:
    """
    五次多项式插值器

    生成平滑的轨迹，保证位置、速度、加速度连续。
    """

    @staticmethod
    def compute_coefficients(
        q0: float, qf: float,
        v0: float = 0.0, vf: float = 0.0,
        a0: float = 0.0, af: float = 0.0,
        T: float = 1.0
    ) -> np.ndarray:
        """
        计算五次多项式系数

        q(t) = a0 + a1*t + a2*t^2 + a3*t^3 + a4*t^4 + a5*t^5

        Args:
            q0, qf: 起始和终止位置
            v0, vf: 起始和终止速度
            a0, af: 起始和终止加速度
            T: 运动时间

        Returns:
            系数 [a0, a1, a2, a3, a4, a5]
        """
        # 边界条件矩阵
        # q(0) = q0, q(T) = qf
        # q'(0) = v0, q'(T) = vf
        # q''(0) = a0, q''(T) = af

        T2 = T * T
        T3 = T2 * T
        T4 = T3 * T
        T5 = T4 * T

        # 求解线性方程组
        # [1   0    0     0      0      0    ] [a0]   [q0]
        # [1   T    T2    T3     T4     T5   ] [a1] = [qf]
        # [0   1    0     0      0      0    ] [a2]   [v0]
        # [0   1   2T   3T2    4T3    5T4   ] [a3]   [vf]
        # [0   0    2     0      0      0    ] [a4]   [a0]
        # [0   0    2   6T    12T2   20T3   ] [a5]   [af]

        # 简化计算
        a0_coef = q0
        a1_coef = v0
        a2_coef = a0 / 2

        # 求解剩余系数
        # 使用矩阵求解
        A = np.array([
            [T3, T4, T5],
            [3*T2, 4*T3, 5*T4],
            [6*T, 12*T2, 20*T3]
        ])

        b = np.array([
            qf - q0 - v0*T - 0.5*a0*T2,
            vf - v0 - a0*T,
            af - a0
        ])

        try:
            x = np.linalg.solve(A, b)
            a3, a4, a5 = x
        except np.linalg.LinAlgError:
            # 如果矩阵奇异，使用简单线性插值
            a3 = (qf - q0) / T3
            a4 = 0
            a5 = 0

        return np.array([a0_coef, a1_coef, a2_coef, a3, a4, a5])

    @staticmethod
    def evaluate(coeffs: np.ndarray, t: float) -> Tuple[float, float, float]:
        """
        计算五次多项式在时间 t 的值

        Args:
            coeffs: 系数 [a0, a1, a2, a3, a4, a5]
            t: 时间

        Returns:
            (position, velocity, acceleration)
        """
        t2 = t * t
        t3 = t2 * t
        t4 = t3 * t
        t5 = t4 * t

        # 位置
        pos = coeffs[0] + coeffs[1]*t + coeffs[2]*t2 + coeffs[3]*t3 + coeffs[4]*t4 + coeffs[5]*t5

        # 速度
        vel = coeffs[1] + 2*coeffs[2]*t + 3*coeffs[3]*t2 + 4*coeffs[4]*t3 + 5*coeffs[5]*t4

        # 加速度
        acc = 2*coeffs[2] + 6*coeffs[3]*t + 12*coeffs[4]*t2 + 20*coeffs[5]*t3

        return pos, vel, acc


class TrajectoryPlanner:
    """
    轨迹规划器

    生成平滑的关节和笛卡尔轨迹。
    """

    def __init__(
        self,
        n_joints: int = 6,
        default_duration: float = 2.0,
        dt: float = 0.01,
    ):
        """
        初始化轨迹规划器

        Args:
            n_joints: 关节数量
            default_duration: 默认运动时间 (s)
            dt: 时间步长 (s)
        """
        self.n_joints = n_joints
        self.default_duration = default_duration
        self.dt = dt

        # 碰撞检测回调
        self._collision_checker: Optional[Callable[[np.ndarray], bool]] = None

    def set_collision_checker(self, checker: Callable[[np.ndarray], bool]):
        """
        设置碰撞检测器

        Args:
            checker: 碰撞检测函数，返回 True 表示碰撞
        """
        self._collision_checker = checker

    def plan_joint_trajectory(
        self,
        start: np.ndarray,
        end: np.ndarray,
        duration: float = None,
        start_velocity: np.ndarray = None,
        end_velocity: np.ndarray = None,
    ) -> JointTrajectory:
        """
        规划关节空间轨迹

        Args:
            start: 起始关节位置
            end: 终止关节位置
            duration: 运动时间 (s)
            start_velocity: 起始速度
            end_velocity: 终止速度

        Returns:
            关节轨迹
        """
        start = np.asarray(start)
        end = np.asarray(end)

        if duration is None:
            # 根据距离计算时间
            distance = np.max(np.abs(end - start))
            duration = max(self.default_duration, distance / 1.0)  # 假设最大速度 1 rad/s

        if start_velocity is None:
            start_velocity = np.zeros(self.n_joints)
        if end_velocity is None:
            end_velocity = np.zeros(self.n_joints)

        # 为每个关节计算五次多项式
        all_coeffs = []
        for i in range(self.n_joints):
            coeffs = QuinticPolynomial.compute_coefficients(
                start[i], end[i],
                start_velocity[i], end_velocity[i],
                0.0, 0.0,  # 加速度边界条件
                duration
            )
            all_coeffs.append(coeffs)

        # 生成轨迹点
        points = []
        t = 0.0
        while t <= duration + self.dt / 2:
            positions = np.zeros(self.n_joints)
            velocities = np.zeros(self.n_joints)
            accelerations = np.zeros(self.n_joints)

            for i, coeffs in enumerate(all_coeffs):
                pos, vel, acc = QuinticPolynomial.evaluate(coeffs, t)
                positions[i] = pos
                velocities[i] = vel
                accelerations[i] = acc

            points.append(TrajectoryPoint(
                time=t,
                position=positions,
                velocity=velocities,
                acceleration=accelerations
            ))

            t += self.dt

        return JointTrajectory(
            points=points,
            joint_names=[f"joint_{i}" for i in range(self.n_joints)],
            duration=duration
        )

    def plan_cartesian_trajectory(
        self,
        start_pose: SE3,
        end_pose: SE3,
        duration: float = None,
        num_points: int = 100,
    ) -> CartesianTrajectory:
        """
        规划笛卡尔空间直线轨迹

        Args:
            start_pose: 起始位姿
            end_pose: 终止位姿
            duration: 运动时间 (s)
            num_points: 轨迹点数量

        Returns:
            笛卡尔轨迹
        """
        if duration is None:
            # 根据距离计算时间
            distance = np.linalg.norm(
                np.array(end_pose.position) - np.array(start_pose.position)
            )
            duration = max(self.default_duration, distance / 0.5)  # 假设最大速度 0.5 m/s

        points = []

        for i in range(num_points + 1):
            t = duration * i / num_points
            alpha = i / num_points

            # 插值位置
            pos = (1 - alpha) * np.array(start_pose.position) + alpha * np.array(end_pose.position)

            # 插值姿态
            rot = CartesianTrajectory._slerp(start_pose.rotation, end_pose.rotation, alpha)

            pose = SE3(tuple(pos), rot)

            # 计算速度和加速度 (数值微分)
            if i == 0:
                vel = np.zeros(6)
                acc = np.zeros(6)
            elif i == num_points:
                vel = np.zeros(6)
                acc = np.zeros(6)
            else:
                # 使用中心差分
                dt_local = duration / num_points
                alpha_prev = (i - 1) / num_points
                alpha_next = (i + 1) / num_points

                pos_prev = (1 - alpha_prev) * np.array(start_pose.position) + alpha_prev * np.array(end_pose.position)
                pos_next = (1 - alpha_next) * np.array(start_pose.position) + alpha_next * np.array(end_pose.position)

                vel[:3] = (pos_next - pos_prev) / (2 * dt_local)
                acc[:3] = (pos_next - 2 * pos + pos_prev) / (dt_local ** 2)

                # 角速度和角加速度 (简化处理)
                vel[3:] = 0
                acc[3:] = 0

            points.append((t, pose, vel, acc))

        return CartesianTrajectory(points=points, duration=duration)

    def check_trajectory_collision(
        self,
        trajectory: JointTrajectory,
        sample_rate: int = 10
    ) -> Tuple[bool, int]:
        """
        检查轨迹碰撞

        Args:
            trajectory: 关节轨迹
            sample_rate: 采样率

        Returns:
            (是否碰撞, 碰撞点索引)
        """
        if self._collision_checker is None:
            return False, -1

        for i, point in enumerate(trajectory.points[::sample_rate]):
            if self._collision_checker(point.position):
                return True, i * sample_rate

        return False, -1


class TrajectoryExecutor:
    """
    轨迹执行器

    执行轨迹并跟踪进度。
    """

    def __init__(self, dt: float = 0.01):
        """
        初始化轨迹执行器

        Args:
            dt: 时间步长 (s)
        """
        self.dt = dt

        # 当前轨迹
        self._trajectory: Optional[JointTrajectory] = None
        self._current_time = 0.0
        self._status = TrajectoryStatus.PENDING

        # 回调
        self._command_callback: Optional[Callable[[np.ndarray, np.ndarray], None]] = None

    def set_command_callback(self, callback: Callable[[np.ndarray, np.ndarray], None]):
        """
        设置命令回调

        Args:
            callback: 回调函数 (position, velocity) -> None
        """
        self._command_callback = callback

    def start(self, trajectory: JointTrajectory):
        """
        开始执行轨迹

        Args:
            trajectory: 关节轨迹
        """
        self._trajectory = trajectory
        self._current_time = 0.0
        self._status = TrajectoryStatus.RUNNING

    def update(self) -> Optional[TrajectoryPoint]:
        """
        更新执行器

        Returns:
            当前轨迹点，如果完成返回 None
        """
        if self._status != TrajectoryStatus.RUNNING or self._trajectory is None:
            return None

        # 获取当前轨迹点
        point = self._trajectory.get_point_at_time(self._current_time)

        if point is None:
            self._status = TrajectoryStatus.COMPLETED
            return None

        # 发送命令
        if self._command_callback:
            self._command_callback(point.position, point.velocity)

        # 更新时间
        self._current_time += self.dt

        # 检查是否完成
        if self._current_time >= self._trajectory.duration:
            self._status = TrajectoryStatus.COMPLETED

        return point

    def pause(self):
        """暂停执行"""
        if self._status == TrajectoryStatus.RUNNING:
            self._status = TrajectoryStatus.PAUSED

    def resume(self):
        """恢复执行"""
        if self._status == TrajectoryStatus.PAUSED:
            self._status = TrajectoryStatus.RUNNING

    def stop(self):
        """停止执行"""
        self._status = TrajectoryStatus.PENDING
        self._trajectory = None
        self._current_time = 0.0

    @property
    def status(self) -> TrajectoryStatus:
        """获取状态"""
        return self._status

    @property
    def progress(self) -> float:
        """获取进度 (0.0 - 1.0)"""
        if self._trajectory is None or self._trajectory.duration <= 0:
            return 0.0
        return min(1.0, self._current_time / self._trajectory.duration)

    @property
    def current_time(self) -> float:
        """获取当前时间"""
        return self._current_time


__all__ = [
    "TrajectoryStatus",
    "TrajectoryPoint",
    "JointTrajectory",
    "CartesianTrajectory",
    "TrajectoryConstraints",
    "QuinticPolynomial",
    "TrajectoryPlanner",
    "TrajectoryExecutor",
]
