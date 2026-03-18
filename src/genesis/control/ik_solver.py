"""
GENESIS IK Solver - 逆运动学求解器

实现机械臂的逆运动学求解，包括:
- 阻尼最小二乘法 (DLS)
- 雅可比转置法
- 奇异点处理
- 关节限位约束

支持 6-DOF 机械臂。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import numpy as np
from numpy.typing import NDArray

from genesis.utils.geometry import SE3, SO3


class IKStatus(Enum):
    """IK 求解状态"""
    SUCCESS = "success"
    FAILED = "failed"
    MAX_ITERATIONS = "max_iterations"
    SINGULARITY = "singularity"
    LIMIT_VIOLATION = "limit_violation"


@dataclass
class IKResult:
    """IK 求解结果"""
    status: IKStatus
    joint_positions: np.ndarray  # 关节位置 (rad)
    position_error: float  # 位置误差 (m)
    orientation_error: float  # 姿态误差 (rad)
    iterations: int = 0  # 迭代次数
    success: bool = False  # 是否成功


@dataclass
class IKConfig:
    """IK 求解器配置"""
    max_iterations: int = 100  # 最大迭代次数
    position_tolerance: float = 0.001  # 位置容差 (m)
    orientation_tolerance: float = 0.01  # 姿态容差 (rad)
    damping: float = 0.01  # 阻尼系数
    step_size: float = 1.0  # 步长
    max_step: float = 0.1  # 最大步长 (rad)


class RobotKinematics:
    """
    机器人运动学

    提供正运动学和雅可比矩阵计算。
    """

    def __init__(
        self,
        joint_limits: np.ndarray,
        link_lengths: List[float] = None,
        dh_parameters: List[Dict] = None,
    ):
        """
        初始化机器人运动学

        Args:
            joint_limits: 关节限位 (n_joints, 2) - [lower, upper]
            link_lengths: 连杆长度列表
            dh_parameters: DH 参数列表
        """
        self.joint_limits = joint_limits
        self.n_joints = len(joint_limits)

        # 默认连杆长度 (类似 Panda 臂)
        if link_lengths is None:
            link_lengths = [0.333, 0.0, 0.316, 0.0, 0.384, 0.0, 0.107]
        self.link_lengths = link_lengths

        # DH 参数 (标准 DH)
        if dh_parameters is None:
            # 默认 DH 参数 (6-DOF 臂)
            dh_parameters = [
                {"a": 0.0, "alpha": 0.0, "d": 0.333, "theta": 0.0},
                {"a": 0.0, "alpha": -np.pi/2, "d": 0.0, "theta": 0.0},
                {"a": 0.0, "alpha": np.pi/2, "d": 0.316, "theta": 0.0},
                {"a": 0.0825, "alpha": np.pi/2, "d": 0.0, "theta": 0.0},
                {"a": -0.0825, "alpha": -np.pi/2, "d": 0.384, "theta": 0.0},
                {"a": 0.0, "alpha": np.pi/2, "d": 0.0, "theta": 0.0},
                {"a": 0.088, "alpha": 0.0, "d": 0.0, "theta": 0.0},
            ]
        self.dh_parameters = dh_parameters

    def forward_kinematics(self, joint_positions: np.ndarray) -> SE3:
        """
        正运动学

        Args:
            joint_positions: 关节位置 (n_joints,)

        Returns:
            末端位姿 (SE3)
        """
        T = np.eye(4)

        for i, (q, dh) in enumerate(zip(joint_positions, self.dh_parameters[:self.n_joints])):
            theta = dh["theta"] + q
            d = dh["d"]
            a = dh["a"]
            alpha = dh["alpha"]

            # DH 变换矩阵
            ct, st = np.cos(theta), np.sin(theta)
            ca, sa = np.cos(alpha), np.sin(alpha)

            Ti = np.array([
                [ct, -st * ca, st * sa, a * ct],
                [st, ct * ca, -ct * sa, a * st],
                [0, sa, ca, d],
                [0, 0, 0, 1]
            ])

            T = T @ Ti

        return SE3.from_matrix(T)

    def compute_jacobian(
        self,
        joint_positions: np.ndarray,
        delta: float = 1e-6
    ) -> np.ndarray:
        """
        计算雅可比矩阵 (数值方法)

        Args:
            joint_positions: 关节位置
            delta: 数值微分步长

        Returns:
            雅可比矩阵 (6, n_joints)
        """
        n = len(joint_positions)
        J = np.zeros((6, n))

        # 当前末端位姿
        T0 = self.forward_kinematics(joint_positions)
        p0 = T0.position
        R0 = T0.rotation.to_rotation_matrix()

        for i in range(n):
            # 扰动
            q_plus = joint_positions.copy()
            q_plus[i] += delta

            T_plus = self.forward_kinematics(q_plus)
            p_plus = T_plus.position
            R_plus = T_plus.rotation.to_rotation_matrix()

            # 位置导数
            J[:3, i] = (np.array(p_plus) - np.array(p0)) / delta

            # 姿态导数 (使用旋转矩阵差分)
            dR = R_plus @ R0.T
            # 提取角速度
            J[3:, i] = self._rotation_matrix_to_axis_angle(dR) / delta

        return J

    def _rotation_matrix_to_axis_angle(self, R: np.ndarray) -> np.ndarray:
        """
        从旋转矩阵提取轴角

        Args:
            R: 旋转矩阵

        Returns:
            角速度向量
        """
        angle = np.arccos(np.clip((np.trace(R) - 1) / 2, -1, 1))

        if angle < 1e-6:
            return np.zeros(3)

        axis = np.array([
            R[2, 1] - R[1, 2],
            R[0, 2] - R[2, 0],
            R[1, 0] - R[0, 1]
        ]) / (2 * np.sin(angle))

        return axis * angle

    def is_within_limits(self, joint_positions: np.ndarray) -> bool:
        """
        检查关节位置是否在限位内

        Args:
            joint_positions: 关节位置

        Returns:
            是否在限位内
        """
        return np.all(joint_positions >= self.joint_limits[:, 0]) and \
               np.all(joint_positions <= self.joint_limits[:, 1])

    def clamp_to_limits(self, joint_positions: np.ndarray) -> np.ndarray:
        """
        将关节位置限制在限位内

        Args:
            joint_positions: 关节位置

        Returns:
            限制后的关节位置
        """
        return np.clip(
            joint_positions,
            self.joint_limits[:, 0],
            self.joint_limits[:, 1]
        )


class IKSolver:
    """
    逆运动学求解器

    实现多种 IK 求解方法。
    """

    def __init__(
        self,
        kinematics: RobotKinematics,
        config: Optional[IKConfig] = None,
    ):
        """
        初始化 IK 求解器

        Args:
            kinematics: 机器人运动学
            config: 求解器配置
        """
        self.kinematics = kinematics
        self.config = config or IKConfig()

    def solve(
        self,
        target_pose: SE3,
        initial_guess: np.ndarray,
        weights: np.ndarray = None,
    ) -> IKResult:
        """
        求解逆运动学

        Args:
            target_pose: 目标位姿
            initial_guess: 初始关节位置
            weights: 位置/姿态权重 (默认 [1, 1, 1, 0.5, 0.5, 0.5])

        Returns:
            IK 求解结果
        """
        # 使用阻尼最小二乘法
        return self._solve_dls(target_pose, initial_guess, weights)

    def _solve_dls(
        self,
        target_pose: SE3,
        q: np.ndarray,
        weights: np.ndarray = None,
    ) -> IKResult:
        """
        阻尼最小二乘法求解

        Args:
            target_pose: 目标位姿
            q: 当前关节位置
            weights: 权重

        Returns:
            IK 结果
        """
        if weights is None:
            weights = np.array([1.0, 1.0, 1.0, 0.5, 0.5, 0.5])

        q = q.copy()
        best_q = q.copy()
        best_error = float('inf')

        for iteration in range(self.config.max_iterations):
            # 当前末端位姿
            current_pose = self.kinematics.forward_kinematics(q)

            # 计算误差
            pos_error = self._compute_position_error(current_pose, target_pose)
            ori_error = self._compute_orientation_error(current_pose, target_pose)

            total_error = np.sqrt(pos_error**2 + ori_error**2)

            # 记录最佳解
            if total_error < best_error:
                best_error = total_error
                best_q = q.copy()

            # 检查收敛
            if (pos_error < self.config.position_tolerance and
                ori_error < self.config.orientation_tolerance):
                return IKResult(
                    status=IKStatus.SUCCESS,
                    joint_positions=q,
                    position_error=pos_error,
                    orientation_error=ori_error,
                    iterations=iteration + 1,
                    success=True
                )

            # 计算雅可比矩阵
            J = self.kinematics.compute_jacobian(q)

            # 计算误差向量
            error = self._compute_error_vector(current_pose, target_pose)
            error = weights * error

            # 阻尼最小二乘法
            # dq = J^T * (J * J^T + lambda * I)^-1 * e
            # 或使用伪逆: dq = (J^T * J + lambda * I)^-1 * J^T * e
            JJT = J @ J.T
            damping_matrix = self.config.damping**2 * np.eye(6)

            try:
                # 使用 J^T * (J * J^T + lambda * I)^-1 * e
                dq = J.T @ np.linalg.solve(JJT + damping_matrix, error)
            except np.linalg.LinAlgError:
                # 奇异矩阵，使用伪逆
                dq = np.linalg.lstsq(J, error, rcond=None)[0]

            # 限制步长
            step_norm = np.linalg.norm(dq)
            if step_norm > self.config.max_step:
                dq = dq * self.config.max_step / step_norm

            # 更新关节位置
            q = q + self.config.step_size * dq

            # 应用关节限位
            q = self.kinematics.clamp_to_limits(q)

        # 达到最大迭代次数
        pos_error = self._compute_position_error(
            self.kinematics.forward_kinematics(best_q),
            target_pose
        )
        ori_error = self._compute_orientation_error(
            self.kinematics.forward_kinematics(best_q),
            target_pose
        )

        return IKResult(
            status=IKStatus.MAX_ITERATIONS,
            joint_positions=best_q,
            position_error=pos_error,
            orientation_error=ori_error,
            iterations=self.config.max_iterations,
            success=(pos_error < self.config.position_tolerance * 10 and
                    ori_error < self.config.orientation_tolerance * 10)
        )

    def _compute_error_vector(
        self,
        current_pose: SE3,
        target_pose: SE3
    ) -> np.ndarray:
        """
        计算误差向量

        Args:
            current_pose: 当前位姿
            target_pose: 目标位姿

        Returns:
            6维误差向量 [位置误差, 姿态误差]
        """
        # 位置误差
        pos_error = np.array(target_pose.position) - np.array(current_pose.position)

        # 姿态误差 (使用旋转矩阵差分)
        R_current = current_pose.rotation.to_rotation_matrix()
        R_target = target_pose.rotation.to_rotation_matrix()
        R_error = R_target @ R_current.T

        ori_error = self.kinematics._rotation_matrix_to_axis_angle(R_error)

        return np.concatenate([pos_error, ori_error])

    def _compute_position_error(
        self,
        current_pose: SE3,
        target_pose: SE3
    ) -> float:
        """计算位置误差"""
        return np.linalg.norm(
            np.array(target_pose.position) - np.array(current_pose.position)
        )

    def _compute_orientation_error(
        self,
        current_pose: SE3,
        target_pose: SE3
    ) -> float:
        """计算姿态误差 (弧度)"""
        R_current = current_pose.rotation.to_rotation_matrix()
        R_target = target_pose.rotation.to_rotation_matrix()
        R_error = R_target @ R_current.T

        angle = np.arccos(np.clip((np.trace(R_error) - 1) / 2, -1, 1))
        return abs(angle)

    def solve_with_seed(
        self,
        target_pose: SE3,
        seed_positions: List[np.ndarray],
    ) -> IKResult:
        """
        使用多个种子位置求解

        Args:
            target_pose: 目标位姿
            seed_positions: 种子位置列表

        Returns:
            最佳 IK 结果
        """
        best_result = None
        best_error = float('inf')

        for seed in seed_positions:
            result = self.solve(target_pose, seed)

            total_error = result.position_error + result.orientation_error
            if total_error < best_error:
                best_error = total_error
                best_result = result

            if result.success:
                return result

        return best_result or IKResult(
            status=IKStatus.FAILED,
            joint_positions=np.zeros(self.kinematics.n_joints),
            position_error=float('inf'),
            orientation_error=float('inf'),
            success=False
        )

    def solve_position_only(
        self,
        target_position: Tuple[float, float, float],
        initial_guess: np.ndarray,
    ) -> IKResult:
        """
        仅求解位置 (忽略姿态)

        Args:
            target_position: 目标位置 (x, y, z)
            initial_guess: 初始关节位置

        Returns:
            IK 结果
        """
        # 使用仅位置的权重
        weights = np.array([1.0, 1.0, 1.0, 0.0, 0.0, 0.0])

        # 创建目标位姿 (姿态任意)
        target_pose = SE3(target_position)

        return self._solve_dls(target_pose, initial_guess, weights)


class IKValidator:
    """
    IK 结果验证器

    验证 IK 结果的有效性。
    """

    def __init__(self, kinematics: RobotKinematics):
        """
        初始化验证器

        Args:
            kinematics: 机器人运动学
        """
        self.kinematics = kinematics

    def validate(
        self,
        joint_positions: np.ndarray,
        target_pose: SE3,
        position_tolerance: float = 0.01,
        orientation_tolerance: float = 0.1,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        验证 IK 结果

        Args:
            joint_positions: 关节位置
            target_pose: 目标位姿
            position_tolerance: 位置容差
            orientation_tolerance: 姿态容差

        Returns:
            (是否有效, 详细信息)
        """
        # 检查关节限位
        within_limits = self.kinematics.is_within_limits(joint_positions)

        # 计算实际位姿
        actual_pose = self.kinematics.forward_kinematics(joint_positions)

        # 计算误差
        pos_error = np.linalg.norm(
            np.array(target_pose.position) - np.array(actual_pose.position)
        )

        R_target = target_pose.rotation.to_rotation_matrix()
        R_actual = actual_pose.rotation.to_rotation_matrix()
        R_error = R_target @ R_actual.T
        ori_error = abs(np.arccos(np.clip((np.trace(R_error) - 1) / 2, -1, 1)))

        # 检查误差
        position_ok = pos_error < position_tolerance
        orientation_ok = ori_error < orientation_tolerance

        valid = within_limits and position_ok and orientation_ok

        details = {
            "within_limits": within_limits,
            "position_error": pos_error,
            "orientation_error": ori_error,
            "position_ok": position_ok,
            "orientation_ok": orientation_ok,
            "actual_pose": actual_pose,
        }

        return valid, details


__all__ = [
    "IKStatus",
    "IKResult",
    "IKConfig",
    "RobotKinematics",
    "IKSolver",
    "IKValidator",
]
