"""
GENESIS Robot Module

机器人本体相关模块，包括：
- sensors: 传感器系统 (RGB-D 相机、IMU、力/力矩传感器)
- battery: 电池与能源管理
- robot_interface: 机器人统一控制接口
"""

from genesis.robot.sensors import (
    SensorBase,
    SensorType,
    SensorConfig,
    CameraConfig,
    IMUConfig,
    FTConfig,
    RGBDCamera,
    IMUSensor,
    FTSensor,
    SensorSuite,
)
from genesis.robot.battery import (
    Battery,
    BatteryConfig,
    PowerMode,
)
from genesis.robot.robot_interface import (
    ArmSide,
    GripperState,
    JointState,
    ArmState,
    BaseState,
    RobotState,
    BaseController,
    ArmController,
    GripperController,
    GenesisBot,
)

__all__ = [
    # Sensors
    "SensorBase",
    "SensorType",
    "SensorConfig",
    "CameraConfig",
    "IMUConfig",
    "FTConfig",
    "RGBDCamera",
    "IMUSensor",
    "FTSensor",
    "SensorSuite",
    # Battery
    "Battery",
    "BatteryConfig",
    "PowerMode",
    # Robot Interface
    "ArmSide",
    "GripperState",
    "JointState",
    "ArmState",
    "BaseState",
    "RobotState",
    "BaseController",
    "ArmController",
    "GripperController",
    "GenesisBot",
]
