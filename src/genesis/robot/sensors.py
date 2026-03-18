"""
GENESIS Robot Sensors Module

传感器系统实现，包括：
- RGBDCamera: RGB-D 深度相机
- IMUSensor: 惯性测量单元
- FTSensor: 六维力/力矩传感器
- SensorSuite: 传感器套件管理器
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class SensorType(Enum):
    """传感器类型枚举"""
    RGBD_CAMERA = "rgbd_camera"
    IMU = "imu"
    FT_SENSOR = "ft_sensor"
    CONTACT = "contact"


@dataclass
class SensorConfig:
    """传感器配置基类"""
    name: str
    sensor_type: SensorType
    update_rate: float = 30.0  # Hz
    enabled: bool = True


@dataclass
class CameraConfig(SensorConfig):
    """RGB-D 相机配置"""
    sensor_type: SensorType = field(default=SensorType.RGBD_CAMERA, init=False)
    resolution: Tuple[int, int] = (640, 480)  # (width, height)
    fov: float = 70.0  # degrees
    depth_range: Tuple[float, float] = (0.1, 10.0)  # meters
    mount_frame: str = "camera_link"
    mount_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    mount_orientation: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # roll, pitch, yaw


@dataclass
class IMUConfig(SensorConfig):
    """IMU 配置"""
    sensor_type: SensorType = field(default=SensorType.IMU, init=False)
    gyro_noise_std: float = 0.01  # rad/s
    accel_noise_std: float = 0.1  # m/s^2
    mount_frame: str = "imu_link"


@dataclass
class FTConfig(SensorConfig):
    """力/力矩传感器配置"""
    sensor_type: SensorType = field(default=SensorType.FT_SENSOR, init=False)
    max_force: float = 100.0  # N
    max_torque: float = 10.0  # Nm
    force_noise_std: float = 0.1  # N
    torque_noise_std: float = 0.01  # Nm
    mount_frame: str = "ft_sensor_link"


class SensorBase(ABC):
    """
    传感器基类
    
    所有传感器都继承此类，实现统一的接口。
    """
    
    def __init__(self, config: SensorConfig):
        """
        初始化传感器
        
        Args:
            config: 传感器配置
        """
        self.config = config
        self._enabled = config.enabled
        self._last_update_time = 0.0
        self._data: Dict[str, Any] = {}
        
    @property
    def name(self) -> str:
        """传感器名称"""
        return self.config.name
    
    @property
    def enabled(self) -> bool:
        """是否启用"""
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        """设置启用状态"""
        self._enabled = value
        
    @property
    def update_interval(self) -> float:
        """更新间隔 (秒)"""
        return 1.0 / self.config.update_rate
    
    def should_update(self, current_time: float) -> bool:
        """
        检查是否应该更新
        
        Args:
            current_time: 当前时间 (秒)
            
        Returns:
            是否应该更新
        """
        if not self._enabled:
            return False
        return (current_time - self._last_update_time) >= self.update_interval
    
    @abstractmethod
    def update(self, sim_context: Any, current_time: float) -> Dict[str, Any]:
        """
        更新传感器数据
        
        Args:
            sim_context: 仿真上下文
            current_time: 当前时间 (秒)
            
        Returns:
            传感器数据字典
        """
        pass
    
    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """
        获取当前传感器数据
        
        Returns:
            传感器数据字典
        """
        return self._data.copy()
    
    def reset(self):
        """重置传感器状态"""
        self._last_update_time = 0.0
        self._data = {}


class RGBDCamera(SensorBase):
    """
    RGB-D 深度相机
    
    提供 RGB 图像、深度图和语义分割图。
    """
    
    def __init__(self, config: CameraConfig):
        """
        初始化 RGB-D 相机
        
        Args:
            config: 相机配置
        """
        super().__init__(config)
        self.config: CameraConfig = config
        self._rgb_image: Optional[np.ndarray] = None
        self._depth_image: Optional[np.ndarray] = None
        self._segmentation: Optional[np.ndarray] = None
        self._point_cloud: Optional[np.ndarray] = None
        
    def update(self, sim_context: Any, current_time: float) -> Dict[str, Any]:
        """
        更新相机数据
        
        Args:
            sim_context: 仿真上下文 (Isaac Sim / MuJoCo)
            current_time: 当前时间
            
        Returns:
            包含 RGB、深度和分割图的字典
        """
        if not self.should_update(current_time):
            return self.get_data()
        
        self._last_update_time = current_time
        
        # 如果有真实仿真上下文，从中获取图像
        if sim_context is not None and hasattr(sim_context, 'get_camera_data'):
            data = sim_context.get_camera_data(self.config.name)
            self._rgb_image = data.get('rgb')
            self._depth_image = data.get('depth')
            self._segmentation = data.get('segmentation')
        else:
            # 生成模拟数据 (用于测试)
            self._generate_simulated_data()
        
        # 生成点云
        self._generate_point_cloud()
        
        self._data = {
            'rgb': self._rgb_image,
            'depth': self._depth_image,
            'segmentation': self._segmentation,
            'point_cloud': self._point_cloud,
            'timestamp': current_time,
        }
        
        return self._data
    
    def _generate_simulated_data(self):
        """生成模拟相机数据 (用于测试)"""
        width, height = self.config.resolution
        
        # 模拟 RGB 图像 (渐变色)
        x = np.linspace(0, 255, width, dtype=np.uint8)
        y = np.linspace(0, 255, height, dtype=np.uint8)
        xx, yy = np.meshgrid(x, y)
        self._rgb_image = np.stack([xx, yy, 128 * np.ones_like(xx)], axis=-1)
        
        # 模拟深度图 (随机深度)
        self._depth_image = np.random.uniform(
            self.config.depth_range[0],
            self.config.depth_range[1],
            (height, width)
        ).astype(np.float32)
        
        # 模拟分割图 (全零 = 背景)
        self._segmentation = np.zeros((height, width), dtype=np.uint8)
    
    def _generate_point_cloud(self):
        """从深度图生成点云"""
        if self._depth_image is None:
            self._point_cloud = None
            return
        
        width, height = self.config.resolution
        fov_rad = np.radians(self.config.fov)
        
        # 计算相机内参
        fx = width / (2 * np.tan(fov_rad / 2))
        fy = fx
        cx = width / 2
        cy = height / 2
        
        # 生成像素坐标
        u = np.arange(width)
        v = np.arange(height)
        u, v = np.meshgrid(u, v)
        
        # 反投影到 3D
        z = self._depth_image
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy
        
        # 组合点云 (N, 3)
        self._point_cloud = np.stack([x, y, z], axis=-1).reshape(-1, 3)
    
    def get_data(self) -> Dict[str, Any]:
        """获取当前相机数据"""
        return self._data.copy()
    
    @property
    def rgb(self) -> Optional[np.ndarray]:
        """获取 RGB 图像"""
        return self._rgb_image
    
    @property
    def depth(self) -> Optional[np.ndarray]:
        """获取深度图"""
        return self._depth_image
    
    @property
    def segmentation(self) -> Optional[np.ndarray]:
        """获取语义分割图"""
        return self._segmentation
    
    @property
    def point_cloud(self) -> Optional[np.ndarray]:
        """获取点云"""
        return self._point_cloud


class IMUSensor(SensorBase):
    """
    惯性测量单元 (IMU)
    
    提供角速度和线加速度数据。
    """
    
    def __init__(self, config: IMUConfig):
        """
        初始化 IMU
        
        Args:
            config: IMU 配置
        """
        super().__init__(config)
        self.config: IMUConfig = config
        self._angular_velocity: np.ndarray = np.zeros(3)
        self._linear_acceleration: np.ndarray = np.zeros(3)
        self._orientation: np.ndarray = np.array([0, 0, 0, 1])  # quaternion (x, y, z, w)
        
    def update(self, sim_context: Any, current_time: float) -> Dict[str, Any]:
        """
        更新 IMU 数据
        
        Args:
            sim_context: 仿真上下文
            current_time: 当前时间
            
        Returns:
            包含角速度、线加速度和姿态的字典
        """
        if not self.should_update(current_time):
            return self.get_data()
        
        self._last_update_time = current_time
        
        # 如果有真实仿真上下文，从中获取数据
        if sim_context is not None and hasattr(sim_context, 'get_imu_data'):
            data = sim_context.get_imu_data(self.config.name)
            self._angular_velocity = data.get('angular_velocity', np.zeros(3))
            self._linear_acceleration = data.get('linear_acceleration', np.zeros(3))
            self._orientation = data.get('orientation', np.array([0, 0, 0, 1]))
        else:
            # 生成模拟数据 (用于测试)
            self._generate_simulated_data()
        
        self._data = {
            'angular_velocity': self._angular_velocity.copy(),
            'linear_acceleration': self._linear_acceleration.copy(),
            'orientation': self._orientation.copy(),
            'timestamp': current_time,
        }
        
        return self._data
    
    def _generate_simulated_data(self):
        """生成模拟 IMU 数据 (用于测试)"""
        # 添加高斯噪声
        self._angular_velocity = np.random.normal(
            0, self.config.gyro_noise_std, 3
        )
        self._linear_acceleration = np.random.normal(
            0, self.config.accel_noise_std, 3
        )
        # 保持静止姿态
        self._orientation = np.array([0, 0, 0, 1])
    
    def get_data(self) -> Dict[str, Any]:
        """获取当前 IMU 数据"""
        return self._data.copy()
    
    @property
    def angular_velocity(self) -> np.ndarray:
        """获取角速度 (rad/s)"""
        return self._angular_velocity
    
    @property
    def linear_acceleration(self) -> np.ndarray:
        """获取线加速度 (m/s²)"""
        return self._linear_acceleration
    
    @property
    def orientation(self) -> np.ndarray:
        """获取姿态四元数 (x, y, z, w)"""
        return self._orientation


class FTSensor(SensorBase):
    """
    六维力/力矩传感器
    
    提供末端执行器的力和力矩数据。
    """
    
    def __init__(self, config: FTConfig):
        """
        初始化力/力矩传感器
        
        Args:
            config: 传感器配置
        """
        super().__init__(config)
        self.config: FTConfig = config
        self._force: np.ndarray = np.zeros(3)  # Fx, Fy, Fz
        self._torque: np.ndarray = np.zeros(3)  # Tx, Ty, Tz
        self._wrench: np.ndarray = np.zeros(6)  # [Fx, Fy, Fz, Tx, Ty, Tz]
        
    def update(self, sim_context: Any, current_time: float) -> Dict[str, Any]:
        """
        更新力/力矩传感器数据
        
        Args:
            sim_context: 仿真上下文
            current_time: 当前时间
            
        Returns:
            包含力和力矩的字典
        """
        if not self.should_update(current_time):
            return self.get_data()
        
        self._last_update_time = current_time
        
        # 如果有真实仿真上下文，从中获取数据
        if sim_context is not None and hasattr(sim_context, 'get_ft_data'):
            data = sim_context.get_ft_data(self.config.name)
            self._force = data.get('force', np.zeros(3))
            self._torque = data.get('torque', np.zeros(3))
        else:
            # 生成模拟数据 (用于测试)
            self._generate_simulated_data()
        
        self._wrench = np.concatenate([self._force, self._torque])
        
        self._data = {
            'force': self._force.copy(),
            'torque': self._torque.copy(),
            'wrench': self._wrench.copy(),
            'timestamp': current_time,
        }
        
        return self._data
    
    def _generate_simulated_data(self):
        """生成模拟力/力矩数据 (用于测试)"""
        # 添加高斯噪声
        self._force = np.random.normal(0, self.config.force_noise_std, 3)
        self._torque = np.random.normal(0, self.config.torque_noise_std, 3)
        
        # 限制范围
        force_mag = np.linalg.norm(self._force)
        if force_mag > self.config.max_force:
            self._force = self._force * self.config.max_force / force_mag
        
        torque_mag = np.linalg.norm(self._torque)
        if torque_mag > self.config.max_torque:
            self._torque = self._torque * self.config.max_torque / torque_mag
    
    def get_data(self) -> Dict[str, Any]:
        """获取当前力/力矩数据"""
        return self._data.copy()
    
    @property
    def force(self) -> np.ndarray:
        """获取力向量 (N)"""
        return self._force
    
    @property
    def torque(self) -> np.ndarray:
        """获取力矩向量 (Nm)"""
        return self._torque
    
    @property
    def wrench(self) -> np.ndarray:
        """获取力/力矩组合向量 [Fx, Fy, Fz, Tx, Ty, Tz]"""
        return self._wrench
    
    @property
    def force_magnitude(self) -> float:
        """获取力的大小 (N)"""
        return np.linalg.norm(self._force)
    
    @property
    def torque_magnitude(self) -> float:
        """获取力矩的大小 (Nm)"""
        return np.linalg.norm(self._torque)


class SensorSuite:
    """
    传感器套件管理器
    
    管理机器人上的所有传感器，提供统一的访问接口。
    """
    
    def __init__(self):
        """初始化传感器套件"""
        self._sensors: Dict[str, SensorBase] = {}
        self._cameras: Dict[str, RGBDCamera] = {}
        self._imus: Dict[str, IMUSensor] = {}
        self._ft_sensors: Dict[str, FTSensor] = {}
        
    def add_sensor(self, sensor: SensorBase):
        """
        添加传感器
        
        Args:
            sensor: 传感器实例
        """
        self._sensors[sensor.name] = sensor
        
        # 按类型分类
        if isinstance(sensor, RGBDCamera):
            self._cameras[sensor.name] = sensor
        elif isinstance(sensor, IMUSensor):
            self._imus[sensor.name] = sensor
        elif isinstance(sensor, FTSensor):
            self._ft_sensors[sensor.name] = sensor
    
    def remove_sensor(self, name: str):
        """
        移除传感器
        
        Args:
            name: 传感器名称
        """
        if name in self._sensors:
            sensor = self._sensors.pop(name)
            if isinstance(sensor, RGBDCamera):
                self._cameras.pop(name, None)
            elif isinstance(sensor, IMUSensor):
                self._imus.pop(name, None)
            elif isinstance(sensor, FTSensor):
                self._ft_sensors.pop(name, None)
    
    def get_sensor(self, name: str) -> Optional[SensorBase]:
        """
        获取传感器
        
        Args:
            name: 传感器名称
            
        Returns:
            传感器实例，如果不存在返回 None
        """
        return self._sensors.get(name)
    
    def update_all(self, sim_context: Any, current_time: float) -> Dict[str, Dict[str, Any]]:
        """
        更新所有传感器
        
        Args:
            sim_context: 仿真上下文
            current_time: 当前时间
            
        Returns:
            所有传感器数据的字典
        """
        all_data = {}
        for name, sensor in self._sensors.items():
            if sensor.enabled:
                data = sensor.update(sim_context, current_time)
                all_data[name] = data
        return all_data
    
    def reset_all(self):
        """重置所有传感器"""
        for sensor in self._sensors.values():
            sensor.reset()
    
    def get_all_data(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有传感器的当前数据
        
        Returns:
            所有传感器数据的字典
        """
        return {name: sensor.get_data() for name, sensor in self._sensors.items()}
    
    @property
    def cameras(self) -> Dict[str, RGBDCamera]:
        """获取所有相机"""
        return self._cameras
    
    @property
    def imus(self) -> Dict[str, IMUSensor]:
        """获取所有 IMU"""
        return self._imus
    
    @property
    def ft_sensors(self) -> Dict[str, FTSensor]:
        """获取所有力/力矩传感器"""
        return self._ft_sensors
    
    def get_camera(self, name: str) -> Optional[RGBDCamera]:
        """获取指定相机"""
        return self._cameras.get(name)
    
    def get_imu(self, name: str) -> Optional[IMUSensor]:
        """获取指定 IMU"""
        return self._imus.get(name)
    
    def get_ft_sensor(self, name: str) -> Optional[FTSensor]:
        """获取指定力/力矩传感器"""
        return self._ft_sensors.get(name)
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "SensorSuite":
        """
        从配置创建传感器套件
        
        Args:
            config: 传感器配置字典
            
        Returns:
            传感器套件实例
        """
        suite = cls()
        
        # 创建头部相机
        if 'head_camera' in config:
            head_cam_config = CameraConfig(
                name='head_camera',
                resolution=tuple(config['head_camera'].get('resolution', [640, 480])),
                fov=config['head_camera'].get('fov', 70.0),
                depth_range=tuple(config['head_camera'].get('depth_range', [0.1, 10.0])),
                mount_frame=config['head_camera'].get('mount_frame', 'head_camera_link'),
                update_rate=config['head_camera'].get('fps', 30.0),
            )
            suite.add_sensor(RGBDCamera(head_cam_config))
        
        # 创建左腕相机
        if 'left_wrist_camera' in config:
            left_wrist_config = CameraConfig(
                name='left_wrist_camera',
                resolution=tuple(config['left_wrist_camera'].get('resolution', [320, 240])),
                fov=config['left_wrist_camera'].get('fov', 90.0),
                depth_range=tuple(config['left_wrist_camera'].get('depth_range', [0.05, 2.0])),
                mount_frame=config['left_wrist_camera'].get('mount_frame', 'left_wrist_camera_link'),
                update_rate=config['left_wrist_camera'].get('fps', 30.0),
            )
            suite.add_sensor(RGBDCamera(left_wrist_config))
        
        # 创建右腕相机
        if 'right_wrist_camera' in config:
            right_wrist_config = CameraConfig(
                name='right_wrist_camera',
                resolution=tuple(config['right_wrist_camera'].get('resolution', [320, 240])),
                fov=config['right_wrist_camera'].get('fov', 90.0),
                depth_range=tuple(config['right_wrist_camera'].get('depth_range', [0.05, 2.0])),
                mount_frame=config['right_wrist_camera'].get('mount_frame', 'right_wrist_camera_link'),
                update_rate=config['right_wrist_camera'].get('fps', 30.0),
            )
            suite.add_sensor(RGBDCamera(right_wrist_config))
        
        # 创建 IMU
        if 'imu' in config:
            imu_config = IMUConfig(
                name='imu',
                update_rate=config['imu'].get('update_rate', 200.0),
                gyro_noise_std=config['imu'].get('noise', {}).get('gyro_std', 0.01),
                accel_noise_std=config['imu'].get('noise', {}).get('accel_std', 0.1),
            )
            suite.add_sensor(IMUSensor(imu_config))
        
        # 创建左腕力/力矩传感器
        if 'left_ft_sensor' in config:
            left_ft_config = FTConfig(
                name='left_ft_sensor',
                update_rate=config['left_ft_sensor'].get('update_rate', 1000.0),
                max_force=config['left_ft_sensor'].get('max_force', 100.0),
                max_torque=config['left_ft_sensor'].get('max_torque', 10.0),
            )
            suite.add_sensor(FTSensor(left_ft_config))
        
        # 创建右腕力/力矩传感器
        if 'right_ft_sensor' in config:
            right_ft_config = FTConfig(
                name='right_ft_sensor',
                update_rate=config['right_ft_sensor'].get('update_rate', 1000.0),
                max_force=config['right_ft_sensor'].get('max_force', 100.0),
                max_torque=config['right_ft_sensor'].get('max_torque', 10.0),
            )
            suite.add_sensor(FTSensor(right_ft_config))
        
        return suite
