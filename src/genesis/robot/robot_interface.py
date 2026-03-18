"""
GENESIS Robot Interface Module

机器人统一控制接口，所有上层模块通过此类与机器人交互。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from genesis.robot.sensors import SensorSuite, RGBDCamera, IMUSensor, FTSensor
from genesis.robot.battery import Battery, PowerMode
from genesis.utils.geometry import SE3
from genesis.utils.types import Pose2D


class ArmSide(Enum):
    """手臂侧别"""
    LEFT = "left"
    RIGHT = "right"


class GripperState(Enum):
    """夹爪状态"""
    OPEN = "open"
    CLOSED = "closed"
    MOVING = "moving"


@dataclass
class JointState:
    """关节状态"""
    positions: np.ndarray  # 关节位置 (rad)
    velocities: np.ndarray  # 关节速度 (rad/s)
    efforts: np.ndarray  # 关节力矩 (Nm)
    
    def __post_init__(self):
        self.positions = np.asarray(self.positions, dtype=np.float64)
        self.velocities = np.asarray(self.velocities, dtype=np.float64)
        self.efforts = np.asarray(self.efforts, dtype=np.float64)


@dataclass
class ArmState:
    """手臂状态"""
    joint_state: JointState
    end_effector_pose: SE3
    is_moving: bool = False
    gripper_state: GripperState = GripperState.OPEN
    gripper_width: float = 0.1  # 当前开合宽度 (m)


@dataclass
class BaseState:
    """底盘状态"""
    pose: Pose2D  # (x, y, yaw)
    velocity: Tuple[float, float]  # (linear, angular)
    is_moving: bool = False


@dataclass
class RobotState:
    """机器人完整状态"""
    base: BaseState
    left_arm: ArmState
    right_arm: ArmState
    battery_soc: float
    sensors: Dict[str, Any]
    timestamp: float = 0.0


class BaseController:
    """
    底盘控制器
    
    管理移动底盘的运动控制。
    """
    
    def __init__(
        self,
        max_linear_speed: float = 1.5,
        max_angular_speed: float = 1.0,
        wheel_base: float = 0.5,
    ):
        """
        初始化底盘控制器
        
        Args:
            max_linear_speed: 最大线速度 (m/s)
            max_angular_speed: 最大角速度 (rad/s)
            wheel_base: 轮距 (m)
        """
        self.max_linear_speed = max_linear_speed
        self.max_angular_speed = max_angular_speed
        self.wheel_base = wheel_base
        
        self._current_pose = Pose2D(0.0, 0.0, 0.0)
        self._target_pose: Optional[Pose2D] = None
        self._velocity = (0.0, 0.0)  # (linear, angular)
        self._is_moving = False
        
    def set_velocity(self, linear: float, angular: float):
        """
        设置底盘速度
        
        Args:
            linear: 线速度 (m/s)
            angular: 角速度 (rad/s)
        """
        # 限制速度
        linear = np.clip(linear, -self.max_linear_speed, self.max_linear_speed)
        angular = np.clip(angular, -self.max_angular_speed, self.max_angular_speed)
        self._velocity = (linear, angular)
        self._is_moving = abs(linear) > 0.001 or abs(angular) > 0.001
    
    def move_to(self, target_x: float, target_y: float, target_yaw: float = 0.0):
        """
        导航到目标位置
        
        Args:
            target_x: 目标 x 坐标 (m)
            target_y: 目标 y 坐标 (m)
            target_yaw: 目标朝向 (rad)
        """
        self._target_pose = Pose2D(target_x, target_y, target_yaw)
        self._is_moving = True
    
    def stop(self):
        """停止底盘运动"""
        self._velocity = (0.0, 0.0)
        self._is_moving = False
        self._target_pose = None
    
    def update(self, dt: float, sim_context: Any = None):
        """
        更新底盘状态
        
        Args:
            dt: 时间步长 (s)
            sim_context: 仿真上下文
        """
        if sim_context is not None:
            # 从仿真获取真实状态
            if hasattr(sim_context, 'get_base_pose'):
                pose = sim_context.get_base_pose()
                self._current_pose = Pose2D(pose[0], pose[1], pose[2])
        else:
            # 简单运动学模拟
            linear, angular = self._velocity
            x, y, yaw = self._current_pose.x, self._current_pose.y, self._current_pose.yaw
            
            # 更新位置
            x += linear * np.cos(yaw) * dt
            y += linear * np.sin(yaw) * dt
            yaw += angular * dt
            
            self._current_pose = Pose2D(x, y, yaw)
    
    @property
    def pose(self) -> Pose2D:
        """获取当前位姿"""
        return self._current_pose
    
    @property
    def velocity(self) -> Tuple[float, float]:
        """获取当前速度"""
        return self._velocity
    
    @property
    def is_moving(self) -> bool:
        """是否正在移动"""
        return self._is_moving
    
    def get_wheel_velocities(self) -> Tuple[float, float, float, float]:
        """
        计算四轮速度
        
        Returns:
            (fl, fr, rl, rr) 四轮速度 (rad/s)
        """
        linear, angular = self._velocity
        
        # 差速驱动运动学
        v_left = linear - angular * self.wheel_base / 2
        v_right = linear + angular * self.wheel_base / 2
        
        # 假设四轮配置，前后轮同速
        return (v_left, v_right, v_left, v_right)


class ArmController:
    """
    手臂控制器
    
    管理 6-DOF 机械臂的运动控制。
    """
    
    def __init__(
        self,
        side: ArmSide,
        joint_limits: Optional[np.ndarray] = None,
        max_velocities: Optional[np.ndarray] = None,
        max_efforts: Optional[np.ndarray] = None,
    ):
        """
        初始化手臂控制器
        
        Args:
            side: 手臂侧别 (LEFT / RIGHT)
            joint_limits: 关节限位 (6, 2) - [lower, upper]
            max_velocities: 最大关节速度 (6,)
            max_efforts: 最大关节力矩 (6,)
        """
        self.side = side
        
        # 默认关节参数
        if joint_limits is None:
            joint_limits = np.array([
                [-np.pi, np.pi],
                [-np.pi/2, np.pi/2],
                [-2.5, 2.5],
                [-np.pi, np.pi],
                [-2.0, 2.0],
                [-np.pi, np.pi],
            ])
        if max_velocities is None:
            max_velocities = np.array([2.0, 2.0, 2.0, 3.0, 3.0, 4.0])
        if max_efforts is None:
            max_efforts = np.array([50.0, 50.0, 40.0, 20.0, 20.0, 10.0])
        
        self.joint_limits = joint_limits
        self.max_velocities = max_velocities
        self.max_efforts = max_efforts
        
        # 状态
        self._joint_positions = np.zeros(6)
        self._joint_velocities = np.zeros(6)
        self._joint_efforts = np.zeros(6)
        self._end_effector_pose = SE3.identity()
        self._is_moving = False
        self._target_joints: Optional[np.ndarray] = None
        self._target_pose: Optional[SE3] = None
        
    def move_to_joints(self, joint_positions: np.ndarray):
        """
        移动到目标关节位置
        
        Args:
            joint_positions: 目标关节位置 (6,)
        """
        self._target_joints = np.clip(
            joint_positions,
            self.joint_limits[:, 0],
            self.joint_limits[:, 1],
        )
        self._is_moving = True
    
    def move_to_pose(self, target_pose: SE3, duration: float = 2.0):
        """
        移动到目标笛卡尔位姿
        
        Args:
            target_pose: 目标位姿 (SE3)
            duration: 运动时长 (s)
        """
        self._target_pose = target_pose
        self._is_moving = True
    
    def stop(self):
        """停止手臂运动"""
        self._target_joints = None
        self._target_pose = None
        self._is_moving = False
        self._joint_velocities = np.zeros(6)
    
    def update(self, dt: float, sim_context: Any = None):
        """
        更新手臂状态
        
        Args:
            dt: 时间步长 (s)
            sim_context: 仿真上下文
        """
        if sim_context is not None:
            # 从仿真获取真实状态
            prefix = f"{self.side.value}_arm"
            if hasattr(sim_context, 'get_joint_positions'):
                self._joint_positions = sim_context.get_joint_positions(prefix)
            if hasattr(sim_context, 'get_joint_velocities'):
                self._joint_velocities = sim_context.get_joint_velocities(prefix)
            if hasattr(sim_context, 'get_end_effector_pose'):
                self._end_effector_pose = sim_context.get_end_effector_pose(prefix)
        else:
            # 简单模拟
            if self._target_joints is not None:
                # 线性插值
                diff = self._target_joints - self._joint_positions
                step = self.max_velocities * dt
                movement = np.minimum(np.abs(diff), step) * np.sign(diff)
                self._joint_positions += movement
                self._joint_velocities = movement / dt if dt > 0 else np.zeros(6)
                
                # 检查是否到达目标
                if np.allclose(self._joint_positions, self._target_joints, atol=0.001):
                    self._joint_positions = self._target_joints.copy()
                    self._joint_velocities = np.zeros(6)
                    self._target_joints = None
                    self._is_moving = False
    
    @property
    def joint_positions(self) -> np.ndarray:
        """获取关节位置"""
        return self._joint_positions
    
    @property
    def joint_velocities(self) -> np.ndarray:
        """获取关节速度"""
        return self._joint_velocities
    
    @property
    def end_effector_pose(self) -> SE3:
        """获取末端位姿"""
        return self._end_effector_pose
    
    @property
    def is_moving(self) -> bool:
        """是否正在移动"""
        return self._is_moving
    
    def get_state(self) -> ArmState:
        """获取手臂状态"""
        return ArmState(
            joint_state=JointState(
                positions=self._joint_positions.copy(),
                velocities=self._joint_velocities.copy(),
                efforts=self._joint_efforts.copy(),
            ),
            end_effector_pose=self._end_effector_pose,
            is_moving=self._is_moving,
        )


class GripperController:
    """
    夹爪控制器
    
    管理平行两指夹爪的控制。
    """
    
    def __init__(
        self,
        side: ArmSide,
        max_width: float = 0.1,
        max_force: float = 50.0,
        max_velocity: float = 0.1,
    ):
        """
        初始化夹爪控制器
        
        Args:
            side: 手臂侧别
            max_width: 最大开合宽度 (m)
            max_force: 最大夹持力 (N)
            max_velocity: 最大开合速度 (m/s)
        """
        self.side = side
        self.max_width = max_width
        self.max_force = max_force
        self.max_velocity = max_velocity
        
        self._width = max_width  # 当前宽度
        self._force = 0.0  # 当前夹持力
        self._state = GripperState.OPEN
        self._target_width: Optional[float] = None
        
    def open(self):
        """打开夹爪"""
        self._target_width = self.max_width
        self._state = GripperState.MOVING
    
    def close(self, force: float = 30.0):
        """
        闭合夹爪
        
        Args:
            force: 夹持力 (N)
        """
        self._target_width = 0.0
        self._force = min(force, self.max_force)
        self._state = GripperState.MOVING
    
    def set_width(self, width: float, force: float = 30.0):
        """
        设置夹爪宽度
        
        Args:
            width: 目标宽度 (m)
            force: 夹持力 (N)
        """
        self._target_width = np.clip(width, 0.0, self.max_width)
        self._force = min(force, self.max_force)
        self._state = GripperState.MOVING
    
    def update(self, dt: float, sim_context: Any = None):
        """
        更新夹爪状态
        
        Args:
            dt: 时间步长 (s)
            sim_context: 仿真上下文
        """
        if sim_context is not None:
            # 从仿真获取真实状态
            prefix = f"{self.side.value}_gripper"
            if hasattr(sim_context, 'get_gripper_width'):
                self._width = sim_context.get_gripper_width(prefix)
        else:
            # 简单模拟
            if self._target_width is not None:
                diff = self._target_width - self._width
                step = self.max_velocity * dt
                
                if abs(diff) < step:
                    self._width = self._target_width
                    self._target_width = None
                    self._state = GripperState.CLOSED if self._width < 0.01 else GripperState.OPEN
                else:
                    self._width += step * np.sign(diff)
    
    @property
    def width(self) -> float:
        """获取当前宽度"""
        return self._width
    
    @property
    def state(self) -> GripperState:
        """获取夹爪状态"""
        return self._state
    
    @property
    def is_grasping(self) -> bool:
        """是否正在抓取"""
        return self._state == GripperState.CLOSED and self._width < 0.01


class GenesisBot:
    """
    GENESIS 机器人统一控制接口
    
    所有上层模块通过此类与机器人交互。
    
    使用示例:
        >>> robot = GenesisBot.from_config(config)
        >>> robot.start()
        >>> robot.move_to(5.0, 10.0, 0.0)  # 导航到目标位置
        >>> robot.move_arm_to_pose(ArmSide.LEFT, target_pose)
        >>> robot.grasp(ArmSide.LEFT, width=0.05)
        >>> robot.get_full_state()
    """
    
    def __init__(
        self,
        name: str = "genesis_bot_v1",
        urdf_path: Optional[str] = None,
        sim_context: Any = None,
    ):
        """
        初始化机器人
        
        Args:
            name: 机器人名称
            urdf_path: URDF 文件路径
            sim_context: 仿真上下文
        """
        self.name = name
        self.urdf_path = urdf_path
        self._sim_context = sim_context
        
        # 初始化组件
        self.base = BaseController()
        self.left_arm = ArmController(ArmSide.LEFT)
        self.right_arm = ArmController(ArmSide.RIGHT)
        self.left_gripper = GripperController(ArmSide.LEFT)
        self.right_gripper = GripperController(ArmSide.RIGHT)
        
        # 传感器套件
        self.sensors = SensorSuite()
        
        # 电池
        self.battery = Battery()
        
        # 状态
        self._is_initialized = False
        self._current_time = 0.0
        
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "GenesisBot":
        """
        从配置创建机器人实例
        
        Args:
            config: 配置字典
            
        Returns:
            机器人实例
        """
        robot_config = config.get('robot', {})
        
        robot = cls(
            name=robot_config.get('name', 'genesis_bot_v1'),
            urdf_path=robot_config.get('urdf_path'),
        )
        
        # 配置底盘
        base_config = robot_config.get('base', {})
        robot.base = BaseController(
            max_linear_speed=base_config.get('dynamics', {}).get('max_linear_speed', 1.5),
            max_angular_speed=base_config.get('dynamics', {}).get('max_angular_speed', 1.0),
            wheel_base=base_config.get('wheel_base', 0.5),
        )
        
        # 配置传感器
        sensors_config = robot_config.get('sensors', {})
        robot.sensors = SensorSuite.from_config(sensors_config)
        
        # 配置电池
        battery_config = robot_config.get('battery', {})
        robot.battery = Battery.from_config(battery_config)
        
        return robot
    
    def initialize(self):
        """初始化机器人"""
        self._is_initialized = True
        self._current_time = 0.0
        self.sensors.reset_all()
        self.battery.reset()
    
    def update(self, dt: float):
        """
        更新机器人状态
        
        Args:
            dt: 时间步长 (s)
        """
        self._current_time += dt
        
        # 更新各组件
        self.base.update(dt, self._sim_context)
        self.left_arm.update(dt, self._sim_context)
        self.right_arm.update(dt, self._sim_context)
        self.left_gripper.update(dt, self._sim_context)
        self.right_gripper.update(dt, self._sim_context)
        
        # 更新传感器
        self.sensors.update_all(self._sim_context, self._current_time)
        
        # 更新电池
        self._update_battery(dt)
    
    def _update_battery(self, dt: float):
        """更新电池状态"""
        # 计算当前功耗
        power = 0.0
        
        # 基础功耗
        power += self.battery._config.idle_power
        
        # 移动功耗
        if self.base.is_moving:
            power += self.battery._config.mobile_power - self.battery._config.idle_power
        
        # 操作功耗
        if self.left_arm.is_moving or self.right_arm.is_moving:
            power += self.battery._config.manipulation_power - self.battery._config.idle_power
        
        # 感知功耗 (假设始终开启)
        power += self.battery._config.perception_power
        
        self.battery.consume(power, dt)
    
    # ==================== 底盘控制 ====================
    
    def move_to(self, target_x: float, target_y: float, target_yaw: float = 0.0):
        """
        导航到目标位置
        
        Args:
            target_x: 目标 x 坐标 (m)
            target_y: 目标 y 坐标 (m)
            target_yaw: 目标朝向 (rad)
        """
        self.base.move_to(target_x, target_y, target_yaw)
    
    def set_velocity(self, linear: float, angular: float):
        """
        设置底盘速度
        
        Args:
            linear: 线速度 (m/s)
            angular: 角速度 (rad/s)
        """
        self.base.set_velocity(linear, angular)
    
    def stop_base(self):
        """停止底盘"""
        self.base.stop()
    
    def get_base_pose(self) -> Tuple[float, float, float]:
        """
        获取底盘位姿
        
        Returns:
            (x, y, yaw) 元组
        """
        pose = self.base.pose
        return (pose.x, pose.y, pose.yaw)
    
    # ==================== 手臂控制 ====================
    
    def move_arm_to_joints(self, arm: ArmSide, joint_positions: np.ndarray):
        """
        移动手臂到目标关节位置
        
        Args:
            arm: 手臂侧别
            joint_positions: 目标关节位置 (6,)
        """
        controller = self.left_arm if arm == ArmSide.LEFT else self.right_arm
        controller.move_to_joints(joint_positions)
    
    def move_arm_to_pose(self, arm: ArmSide, target_pose: SE3, duration: float = 2.0):
        """
        移动手臂到目标笛卡尔位姿
        
        Args:
            arm: 手臂侧别
            target_pose: 目标位姿 (SE3)
            duration: 运动时长 (s)
        """
        controller = self.left_arm if arm == ArmSide.LEFT else self.right_arm
        controller.move_to_pose(target_pose, duration)
    
    def stop_arm(self, arm: ArmSide):
        """停止手臂"""
        controller = self.left_arm if arm == ArmSide.LEFT else self.right_arm
        controller.stop()
    
    def get_arm_state(self, arm: ArmSide) -> ArmState:
        """获取手臂状态"""
        controller = self.left_arm if arm == ArmSide.LEFT else self.right_arm
        return controller.get_state()
    
    # ==================== 夹爪控制 ====================
    
    def grasp(self, arm: ArmSide, width: float = 0.0, force: float = 30.0):
        """
        抓取
        
        Args:
            arm: 手臂侧别
            width: 抓取宽度 (m)，0 表示完全闭合
            force: 夹持力 (N)
        """
        gripper = self.left_gripper if arm == ArmSide.LEFT else self.right_gripper
        gripper.set_width(width, force)
    
    def release(self, arm: ArmSide):
        """释放"""
        gripper = self.left_gripper if arm == ArmSide.LEFT else self.right_gripper
        gripper.open()
    
    def get_gripper_state(self, arm: ArmSide) -> GripperState:
        """获取夹爪状态"""
        gripper = self.left_gripper if arm == ArmSide.LEFT else self.right_gripper
        return gripper.state
    
    # ==================== 感知 ====================
    
    def get_head_image(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取头部相机图像
        
        Returns:
            (rgb, depth) 元组
        """
        camera = self.sensors.get_camera('head_camera')
        if camera is None:
            return None, None
        return camera.rgb, camera.depth
    
    def get_wrist_image(self, arm: ArmSide) -> Tuple[np.ndarray, np.ndarray]:
        """
        获取腕部相机图像
        
        Args:
            arm: 手臂侧别
            
        Returns:
            (rgb, depth) 元组
        """
        name = f"{arm.value}_wrist_camera"
        camera = self.sensors.get_camera(name)
        if camera is None:
            return None, None
        return camera.rgb, camera.depth
    
    def get_wrist_force(self, arm: ArmSide) -> np.ndarray:
        """
        获取腕部力/力矩传感器数据
        
        Args:
            arm: 手臂侧别
            
        Returns:
            力/力矩向量 [Fx, Fy, Fz, Tx, Ty, Tz]
        """
        name = f"{arm.value}_ft_sensor"
        ft = self.sensors.get_ft_sensor(name)
        if ft is None:
            return np.zeros(6)
        return ft.wrench
    
    # ==================== 状态 ====================
    
    def get_battery_soc(self) -> float:
        """获取电池电量状态"""
        return self.battery.soc
    
    def is_battery_critical(self) -> bool:
        """检查电池是否处于临界状态"""
        return self.battery.is_critical
    
    def get_full_state(self) -> Dict[str, Any]:
        """
        获取机器人完整状态
        
        Returns:
            包含所有状态的字典
        """
        return {
            'name': self.name,
            'base': {
                'pose': self.get_base_pose(),
                'velocity': self.base.velocity,
                'is_moving': self.base.is_moving,
            },
            'left_arm': {
                'joint_positions': self.left_arm.joint_positions.tolist(),
                'is_moving': self.left_arm.is_moving,
                'gripper_state': self.left_gripper.state.value,
                'gripper_width': self.left_gripper.width,
            },
            'right_arm': {
                'joint_positions': self.right_arm.joint_positions.tolist(),
                'is_moving': self.right_arm.is_moving,
                'gripper_state': self.right_gripper.state.value,
                'gripper_width': self.right_gripper.width,
            },
            'battery': self.battery.get_status(),
            'sensors': self.sensors.get_all_data(),
            'timestamp': self._current_time,
        }
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"GenesisBot(name='{self.name}', "
            f"battery={self.battery.soc * 100:.1f}%, "
            f"base={'moving' if self.base.is_moving else 'idle'})"
        )
