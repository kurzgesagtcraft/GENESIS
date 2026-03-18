"""
GENESIS Types Module - 类型定义模块

定义项目中使用的核心数据类型。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Union
import numpy as np
from numpy.typing import NDArray


# 数值类型
Float = Union[float, np.floating]
Int = Union[int, np.integer]

# 数组类型
Array = NDArray[np.floating]

# 基础几何类型
Point2D = Tuple[Float, Float]
Point3D = Tuple[Float, Float, Float]
Quaternion = Tuple[Float, Float, Float, Float] # (w, x, y, z)


@dataclass
class Pose2D:
    """
    2D 位姿数据类。
    
    Attributes:
        x: x 坐标 (m)
        y: y 坐标 (m)
        yaw: 朝向角 (rad)
    """
    x: float = 0.0
    y: float = 0.0
    yaw: float = 0.0

    def to_tuple(self) -> Tuple[float, float, float]:
        """返回 (x, y, yaw) 元组。"""
        return (self.x, self.y, self.yaw)

    def to_array(self) -> np.ndarray:
        """返回 numpy 数组。"""
        return np.array([self.x, self.y, self.yaw])

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float]) -> "Pose2D":
        """从元组创建。"""
        return cls(x=t[0], y=t[1], yaw=t[2] if len(t) > 2 else 0.0)

    def distance_to(self, other: "Pose2D") -> float:
        """计算到另一个位姿的平面距离。"""
        return np.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)

    def angle_to(self, other: "Pose2D") -> float:
        """计算到另一个位姿的角度差。"""
        return np.arctan2(other.y - self.y, other.x - self.x)


@dataclass
class Position3D:
    """3D位置数据类"""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    @classmethod
    def from_tuple(cls, t: Tuple[float, float, float]) -> "Position3D":
        return cls(x=t[0], y=t[1], z=t[2])


@dataclass
class Color:
  """RGBA颜色数据类"""
  r: float = 0.0
  g: float = 0.0
  b: float = 0.0
  a: float = 1.0
  
  def to_tuple(self) -> Tuple[float, float, float, float]:
    return (self.r, self.g, self.b, self.a)
  
  def to_array(self) -> np.ndarray:
    return np.array([self.r, self.g, self.b, self.a])
  
  @classmethod
  def from_tuple(cls, t: Tuple[float, float, float, float]) -> "Color":
    return cls(r=t[0], g=t[1], b=t[2], a=t[3] if len(t) > 3 else 1.0)


@dataclass
class BoundingBox:
    """
    3D 边界框。
    
    Attributes:
        min: 最小点坐标 (x, y, z)
        max: 最大点坐标 (x, y, z)
    """
    min: Point3D
    max: Point3D
    
    @property
    def size(self) -> Tuple[Float, Float, Float]:
        """返回边界框尺寸 (width, height, depth)。"""
        return (
            self.max[0] - self.min[0],
            self.max[1] - self.min[1],
            self.max[2] - self.min[2],
        )
    
    @property
    def center(self) -> Point3D:
        """返回边界框中心点。"""
        return (
            (self.min[0] + self.max[0]) / 2,
            (self.min[1] + self.max[1]) / 2,
            (self.min[2] + self.max[2]) / 2,
        )
    
    @property
    def volume(self) -> Float:
        """返回边界框体积。"""
        s = self.size
        return s[0] * s[1] * s[2]
    
    def contains(self, point: Point3D) -> bool:
        """检查点是否在边界框内。"""
        return (
            self.min[0] <= point[0] <= self.max[0]
            and self.min[1] <= point[1] <= self.max[1]
            and self.min[2] <= point[2] <= self.max[2]
        )
    
    def intersects(self, other: BoundingBox) -> bool:
        """检查是否与另一个边界框相交。"""
        return (
            self.min[0] <= other.max[0] and self.max[0] >= other.min[0]
            and self.min[1] <= other.max[1] and self.max[1] >= other.min[1]
            and self.min[2] <= other.max[2] and self.max[2] >= other.min[2]
        )
    
    @classmethod
    def from_center_size(
        cls, center: Point3D, size: Tuple[Float, Float, Float]
    ) -> BoundingBox:
        """从中心点和尺寸创建边界框。"""
        half_size = (size[0] / 2, size[1] / 2, size[2] / 2)
        return cls(
            min=(center[0] - half_size[0], center[1] - half_size[1], center[2] - half_size[2]),
            max=(center[0] + half_size[0], center[1] + half_size[1], center[2] + half_size[2]),
        )


@dataclass
class Transform:
    """
    3D 变换，包含位置和旋转。
    
    Attributes:
        position: 位置 (x, y, z)
        rotation: 旋转四元数 (w, x, y, z)
    """
    position: Point3D = (0.0, 0.0, 0.0)
    rotation: Quaternion = (1.0, 0.0, 0.0, 0.0)
    
    def to_matrix(self) -> Array:
        """转换为 4x4 齐次变换矩阵。"""
        # 四元数转旋转矩阵
        w, x, y, z = self.rotation
        
        # 避免重复计算
        xx, yy, zz = x * x, y * y, z * z
        xy, xz, yz = x * y, x * z, y * z
        wx, wy, wz = w * x, w * y, w * z
        
        matrix = np.array([
            [1 - 2*(yy + zz), 2*(xy - wz), 2*(xz + wy), self.position[0]],
            [2*(xy + wz), 1 - 2*(xx + zz), 2*(yz - wx), self.position[1]],
            [2*(xz - wy), 2*(yz + wx), 1 - 2*(xx + yy), self.position[2]],
            [0, 0, 0, 1],
        ], dtype=np.float64)
        
        return matrix
    
    @classmethod
    def from_matrix(cls, matrix: Array) -> Transform:
        """从 4x4 齐次变换矩阵创建变换。"""
        # 提取位置
        position = (matrix[0, 3], matrix[1, 3], matrix[2, 3])
        
        # 提取旋转矩阵并转换为四元数
        rot_matrix = matrix[:3, :3]
        trace = rot_matrix[0, 0] + rot_matrix[1, 1] + rot_matrix[2, 2]
        
        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (rot_matrix[2, 1] - rot_matrix[1, 2]) * s
            y = (rot_matrix[0, 2] - rot_matrix[2, 0]) * s
            z = (rot_matrix[1, 0] - rot_matrix[0, 1]) * s
        elif rot_matrix[0, 0] > rot_matrix[1, 1] and rot_matrix[0, 0] > rot_matrix[2, 2]:
            s = 2.0 * np.sqrt(1.0 + rot_matrix[0, 0] - rot_matrix[1, 1] - rot_matrix[2, 2])
            w = (rot_matrix[2, 1] - rot_matrix[1, 2]) / s
            x = 0.25 * s
            y = (rot_matrix[0, 1] + rot_matrix[1, 0]) / s
            z = (rot_matrix[0, 2] + rot_matrix[2, 0]) / s
        elif rot_matrix[1, 1] > rot_matrix[2, 2]:
            s = 2.0 * np.sqrt(1.0 + rot_matrix[1, 1] - rot_matrix[0, 0] - rot_matrix[2, 2])
            w = (rot_matrix[0, 2] - rot_matrix[2, 0]) / s
            x = (rot_matrix[0, 1] + rot_matrix[1, 0]) / s
            y = 0.25 * s
            z = (rot_matrix[1, 2] + rot_matrix[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + rot_matrix[2, 2] - rot_matrix[0, 0] - rot_matrix[1, 1])
            w = (rot_matrix[1, 0] - rot_matrix[0, 1]) / s
            x = (rot_matrix[0, 2] + rot_matrix[2, 0]) / s
            y = (rot_matrix[1, 2] + rot_matrix[2, 1]) / s
            z = 0.25 * s
        
        return cls(position=position, rotation=(w, x, y, z))
    
    def inverse(self) -> Transform:
        """返回逆变换。"""
        matrix = self.to_matrix()
        inv_matrix = np.linalg.inv(matrix)
        return Transform.from_matrix(inv_matrix)
    
    def __mul__(self, other: Transform) -> Transform:
        """变换组合。"""
        matrix = self.to_matrix() @ other.to_matrix()
        return Transform.from_matrix(matrix)


@dataclass
class Velocity:
    """
    速度，包含线速度和角速度。
    
    Attributes:
        linear: 线速度 (vx, vy, vz)
        angular: 角速度 (wx, wy, wz)
    """
    linear: Point3D = (0.0, 0.0, 0.0)
    angular: Point3D = (0.0, 0.0, 0.0)


@dataclass
class Wrench:
    """
    力/力矩，包含力和力矩。
    
    Attributes:
        force: 力 (fx, fy, fz)
        torque: 力矩 (tx, ty, tz)
    """
    force: Point3D = (0.0, 0.0, 0.0)
    torque: Point3D = (0.0, 0.0, 0.0)


@dataclass
class JointState:
    """
    关节状态。
    
    Attributes:
        position: 关节位置 (弧度或米)
        velocity: 关节速度 (rad/s 或 m/s)
        effort: 关节力/力矩 (N 或 Nm)
    """
    position: float = 0.0
    velocity: float = 0.0
    effort: float = 0.0


@dataclass  
class RobotState:
    """
    机器人完整状态。
    
    Attributes:
        base_pose: 底盘位姿
        base_velocity: 底盘速度
        joint_states: 关节状态字典 {joint_name: JointState}
        battery_soc: 电池电量 (0-1)
        gripper_states: 夹爪状态字典 {gripper_name: float (开合度)}
    """
    base_pose: Transform
    base_velocity: Velocity
    joint_states: dict[str, JointState]
    battery_soc: float = 1.0
    gripper_states: dict[str, float] = None
    
    def __post_init__(self):
        if self.gripper_states is None:
            self.gripper_states = {}
