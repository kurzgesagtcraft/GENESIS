"""
GENESIS Geometry Module - 几何变换模块

提供 SE3 和 SO3 变换类，用于 3D 空间中的位姿表示和变换。
"""

from __future__ import annotations

from typing import Tuple, Union
import numpy as np
from numpy.typing import NDArray


class SO3:
    """
    SO(3) 旋转群表示。
    
    使用四元数表示旋转，支持各种旋转表示之间的转换。
    """
    
    def __init__(self, quaternion: Tuple[float, float, float, float] = (1, 0, 0, 0)) -> None:
        """
        初始化 SO3 旋转。
        
        Args:
            quaternion: 四元数 (w, x, y, z)，默认为单位四元数
        """
        self._quat = np.array(quaternion, dtype=np.float64)
        self._normalize()
    
    def _normalize(self) -> None:
        """归一化四元数。"""
        norm = np.linalg.norm(self._quat)
        if norm < 1e-10:
            self._quat = np.array([1, 0, 0, 0])
        else:
            self._quat /= norm
    
    @property
    def quaternion(self) -> Tuple[float, float, float, float]:
        """返回四元数 (w, x, y, z)。"""
        return tuple(self._quat)
    
    @property
    def w(self) -> float:
        """四元数 w 分量。"""
        return self._quat[0]
    
    @property
    def xyz(self) -> Tuple[float, float, float]:
        """四元数 (x, y, z) 分量。"""
        return tuple(self._quat[1:4])
    
    def to_rotation_matrix(self) -> NDArray[np.float64]:
        """转换为 3x3 旋转矩阵。"""
        w, x, y, z = self._quat
        
        # 避免重复计算
        xx, yy, zz = x * x, y * y, z * z
        xy, xz, yz = x * y, x * z, y * z
        wx, wy, wz = w * x, w * y, w * z
        
        return np.array([
            [1 - 2*(yy + zz), 2*(xy - wz), 2*(xz + wy)],
            [2*(xy + wz), 1 - 2*(xx + zz), 2*(yz - wx)],
            [2*(xz - wy), 2*(yz + wx), 1 - 2*(xx + yy)],
        ])
    
    def to_euler_angles(self, order: str = "xyz") -> Tuple[float, float, float]:
        """
        转换为欧拉角。
        
        Args:
            order: 欧拉角顺序，默认 "xyz"
            
        Returns:
            欧拉角 (roll, pitch, yaw)，单位为弧度
        """
        R = self.to_rotation_matrix()
        
        if order == "xyz":
            # 检查万向节锁
            sy = np.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
            
            if sy > 1e-6:
                x = np.arctan2(R[2, 1], R[2, 2])
                y = np.arctan2(-R[2, 0], sy)
                z = np.arctan2(R[1, 0], R[0, 0])
            else:
                x = np.arctan2(-R[1, 2], R[1, 1])
                y = np.arctan2(-R[2, 0], sy)
                z = 0
            
            return (x, y, z)
        else:
            raise NotImplementedError(f"Euler order '{order}' not implemented")
    
    def to_axis_angle(self) -> Tuple[NDArray[np.float64], float]:
        """
        转换为轴角表示。
        
        Returns:
            (axis, angle): 旋转轴和旋转角度（弧度）
        """
        w = self._quat[0]
        xyz = self._quat[1:4]
        
        angle = 2 * np.arccos(np.clip(w, -1, 1))
        
        if angle < 1e-10:
            return np.array([0, 0, 1]), 0.0
        
        axis = xyz / np.sin(angle / 2)
        return axis, angle
    
    def inverse(self) -> SO3:
        """返回逆旋转。"""
        return SO3((self._quat[0], -self._quat[1], -self._quat[2], -self._quat[3]))
    
    def __mul__(self, other: SO3) -> SO3:
        """旋转组合。"""
        w1, x1, y1, z1 = self._quat
        w2, x2, y2, z2 = other._quat
        
        w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
        x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
        y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
        z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
        
        return SO3((w, x, y, z))
    
    def __repr__(self) -> str:
        return f"SO3(quaternion={self.quaternion})"
    
    @classmethod
    def from_rotation_matrix(cls, R: NDArray[np.float64]) -> SO3:
        """从 3x3 旋转矩阵创建。"""
        trace = R[0, 0] + R[1, 1] + R[2, 2]
        
        if trace > 0:
            s = 0.5 / np.sqrt(trace + 1.0)
            w = 0.25 / s
            x = (R[2, 1] - R[1, 2]) * s
            y = (R[0, 2] - R[2, 0]) * s
            z = (R[1, 0] - R[0, 1]) * s
        elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2])
            w = (R[2, 1] - R[1, 2]) / s
            x = 0.25 * s
            y = (R[0, 1] + R[1, 0]) / s
            z = (R[0, 2] + R[2, 0]) / s
        elif R[1, 1] > R[2, 2]:
            s = 2.0 * np.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2])
            w = (R[0, 2] - R[2, 0]) / s
            x = (R[0, 1] + R[1, 0]) / s
            y = 0.25 * s
            z = (R[1, 2] + R[2, 1]) / s
        else:
            s = 2.0 * np.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1])
            w = (R[1, 0] - R[0, 1]) / s
            x = (R[0, 2] + R[2, 0]) / s
            y = (R[1, 2] + R[2, 1]) / s
            z = 0.25 * s
        
        return cls((w, x, y, z))
    
    @classmethod
    def from_euler_angles(cls, roll: float, pitch: float, yaw: float, order: str = "xyz") -> SO3:
        """从欧拉角创建。"""
        if order == "xyz":
            cr, sr = np.cos(roll / 2), np.sin(roll / 2)
            cp, sp = np.cos(pitch / 2), np.sin(pitch / 2)
            cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
            
            w = cr * cp * cy + sr * sp * sy
            x = sr * cp * cy - cr * sp * sy
            y = cr * sp * cy + sr * cp * sy
            z = cr * cp * sy - sr * sp * cy
            
            return cls((w, x, y, z))
        else:
            raise NotImplementedError(f"Euler order '{order}' not implemented")
    
    @classmethod
    def from_axis_angle(cls, axis: NDArray[np.float64], angle: float) -> SO3:
        """从轴角创建。"""
        axis = axis / np.linalg.norm(axis)
        half_angle = angle / 2
        w = np.cos(half_angle)
        xyz = np.sin(half_angle) * axis
        return cls((w, xyz[0], xyz[1], xyz[2]))
    
    @classmethod
    def identity(cls) -> SO3:
        """返回单位旋转。"""
        return cls((1, 0, 0, 0))
    
    @classmethod
    def random(cls) -> SO3:
        """返回随机旋转。"""
        # 均匀分布在 SO(3) 上
        u1, u2, u3 = np.random.random(3)
        w = np.sqrt(1 - u1) * np.sin(2 * np.pi * u2)
        x = np.sqrt(1 - u1) * np.cos(2 * np.pi * u2)
        y = np.sqrt(u1) * np.sin(2 * np.pi * u3)
        z = np.sqrt(u1) * np.cos(2 * np.pi * u3)
        return cls((w, x, y, z))


class SE3:
    """
    SE(3) 变换群表示。
    
    表示 3D 空间中的刚体变换，包含位置和旋转。
    """
    
    def __init__(
        self,
        position: Tuple[float, float, float] = (0, 0, 0),
        rotation: Union[SO3, Tuple[float, float, float, float]] = None,
    ) -> None:
        """
        初始化 SE3 变换。
        
        Args:
            position: 位置 (x, y, z)
            rotation: SO3 旋转或四元数 (w, x, y, z)
        """
        self._position = np.array(position, dtype=np.float64)
        
        if rotation is None:
            self._rotation = SO3.identity()
        elif isinstance(rotation, SO3):
            self._rotation = rotation
        else:
            self._rotation = SO3(rotation)
    
    @property
    def position(self) -> Tuple[float, float, float]:
        """返回位置。"""
        return tuple(self._position)
    
    @property
    def rotation(self) -> SO3:
        """返回旋转。"""
        return self._rotation
    
    @property
    def x(self) -> float:
        """x 坐标。"""
        return self._position[0]
    
    @property
    def y(self) -> float:
        """y 坐标。"""
        return self._position[1]
    
    @property
    def z(self) -> float:
        """z 坐标。"""
        return self._position[2]
    
    def to_matrix(self) -> NDArray[np.float64]:
        """转换为 4x4 齐次变换矩阵。"""
        T = np.eye(4)
        T[:3, :3] = self._rotation.to_rotation_matrix()
        T[:3, 3] = self._position
        return T
    
    def inverse(self) -> SE3:
        """返回逆变换。"""
        R_inv = self._rotation.inverse()
        p_inv = -R_inv.to_rotation_matrix() @ self._position
        return SE3(tuple(p_inv), R_inv)
    
    def transform_point(self, point: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """变换一个点。"""
        p = np.array(point)
        R = self._rotation.to_rotation_matrix()
        result = R @ p + self._position
        return tuple(result)
    
    def transform_direction(self, direction: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """变换一个方向（不考虑平移）。"""
        d = np.array(direction)
        R = self._rotation.to_rotation_matrix()
        result = R @ d
        return tuple(result)
    
    def __mul__(self, other: SE3) -> SE3:
        """变换组合。"""
        R1 = self._rotation.to_rotation_matrix()
        R2 = other._rotation.to_rotation_matrix()
        
        new_R = R1 @ R2
        new_p = R1 @ other._position + self._position
        
        return SE3(tuple(new_p), SO3.from_rotation_matrix(new_R))
    
    def __repr__(self) -> str:
        return f"SE3(position={self.position}, rotation={self.rotation})"
    
    @classmethod
    def from_matrix(cls, T: NDArray[np.float64]) -> SE3:
        """从 4x4 齐次变换矩阵创建。"""
        position = tuple(T[:3, 3])
        rotation = SO3.from_rotation_matrix(T[:3, :3])
        return cls(position, rotation)
    
    @classmethod
    def identity(cls) -> SE3:
        """返回单位变换。"""
        return cls((0, 0, 0), SO3.identity())
    
    @classmethod
    def from_translation(cls, x: float, y: float, z: float) -> SE3:
        """从平移创建。"""
        return cls((x, y, z), SO3.identity())
    
    @classmethod
    def from_rotation(cls, rotation: SO3) -> SE3:
        """从旋转创建。"""
        return cls((0, 0, 0), rotation)
    
    @classmethod
    def from_pose(cls, x: float, y: float, z: float, roll: float, pitch: float, yaw: float) -> SE3:
        """从位姿创建（位置 + 欧拉角）。"""
        position = (x, y, z)
        rotation = SO3.from_euler_angles(roll, pitch, yaw)
        return cls(position, rotation)
