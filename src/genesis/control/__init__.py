"""
GENESIS Control Module - 运动与操作控制模块

提供机器人的运动控制和操作技能。

模块结构:
- base_controller.py: 底盘基础运动控制
- path_follower.py: 路径跟踪 (Pure Pursuit)
- navigator.py: 全局导航接口
- ik_solver.py: 逆运动学求解器
- trajectory_planner.py: 轨迹规划
- impedance_controller.py: 阻抗控制
- skills/: 操作技能目录
"""

from genesis.control.base_controller import (
    MotionState,
    PIDGains,
    MotionConstraints,
    VelocityCommand,
    WheelVelocities,
    PIDController,
    DifferentialDriveController,
    OdometryEstimator,
)
from genesis.control.path_follower import (
    PathFollower,
    PathFollowerConfig,
    PathPoint,
    FollowerState,
    PurePursuitController,
)
from genesis.control.navigator import Navigator, NavigationStatus
from genesis.control.ik_solver import IKSolver, IKResult
from genesis.control.trajectory_planner import (
    TrajectoryPlanner,
    JointTrajectory,
    CartesianTrajectory,
)
from genesis.control.impedance_controller import ImpedanceController

__all__ = [
    # base_controller
    "MotionState",
    "PIDGains",
    "MotionConstraints",
    "VelocityCommand",
    "WheelVelocities",
    "PIDController",
    "DifferentialDriveController",
    "OdometryEstimator",
    # path_follower
    "PathFollower",
    "PathFollowerConfig",
    "PathPoint",
    "FollowerState",
    "PurePursuitController",
    # navigator
    "Navigator",
    "NavigationStatus",
    # ik_solver
    "IKSolver",
    "IKResult",
    # trajectory_planner
    "TrajectoryPlanner",
    "JointTrajectory",
    "CartesianTrajectory",
    # impedance_controller
    "ImpedanceController",
]
