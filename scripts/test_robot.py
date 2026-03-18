#!/usr/bin/env python3
"""
GENESIS Robot Test Script

测试机器人模块的功能，包括：
- 传感器系统
- 电池系统
- 机器人控制接口
"""

import sys
import time
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import numpy as np

from genesis.robot.sensors import (
    RGBDCamera,
    CameraConfig,
    IMUSensor,
    IMUConfig,
    FTSensor,
    FTConfig,
    SensorSuite,
)
from genesis.robot.battery import Battery, PowerMode
from genesis.robot.robot_interface import (
    GenesisBot,
    ArmSide,
    GripperState,
)
from genesis.utils.geometry import SE3


def test_battery():
    """测试电池系统"""
    print("\n" + "=" * 60)
    print("🔋 测试电池系统")
    print("=" * 60)
    
    # 创建电池
    battery = Battery(capacity_wh=500, initial_soc=1.0)
    print(f"初始状态: {battery}")
    
    # 测试电量消耗
    print("\n--- 测试电量消耗 ---")
    for mode in [PowerMode.IDLE, PowerMode.MOBILE, PowerMode.MANIPULATION]:
        battery.set_mode(mode)
        battery.consume_mode(mode, 60)  # 消耗 60 秒
        print(f"  {mode.value}: 消耗 60s, 剩余电量 {battery.soc * 100:.1f}%")
    
    # 测试充电
    print("\n--- 测试充电 ---")
    battery.charge(50, 120)  # 50W 充电 120 秒
    print(f"  充电后: {battery}")
    
    # 测试状态
    print("\n--- 电池状态 ---")
    status = battery.get_status()
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    print("\n✅ 电池系统测试通过")
    return True


def test_sensors():
    """测试传感器系统"""
    print("\n" + "=" * 60)
    print("📷 测试传感器系统")
    print("=" * 60)
    
    # 创建相机
    print("\n--- 测试 RGB-D 相机 ---")
    camera_config = CameraConfig(
        name="test_camera",
        resolution=(640, 480),
        fov=70.0,
        depth_range=(0.1, 10.0),
    )
    camera = RGBDCamera(camera_config)
    
    # 更新相机
    camera.update(None, time.time())
    
    print(f"  相机名称: {camera.name}")
    print(f"  分辨率: {camera_config.resolution}")
    print(f"  RGB 图像形状: {camera.rgb.shape if camera.rgb is not None else 'None'}")
    print(f"  深度图形状: {camera.depth.shape if camera.depth is not None else 'None'}")
    print(f"  点云形状: {camera.point_cloud.shape if camera.point_cloud is not None else 'None'}")
    
    # 创建 IMU
    print("\n--- 测试 IMU ---")
    imu_config = IMUConfig(name="test_imu", update_rate=200.0)
    imu = IMUSensor(imu_config)
    
    imu.update(None, time.time())
    
    print(f"  IMU 名称: {imu.name}")
    print(f"  角速度: {imu.angular_velocity}")
    print(f"  线加速度: {imu.linear_acceleration}")
    print(f"  姿态四元数: {imu.orientation}")
    
    # 创建力/力矩传感器
    print("\n--- 测试力/力矩传感器 ---")
    ft_config = FTConfig(name="test_ft", update_rate=1000.0)
    ft = FTSensor(ft_config)
    
    ft.update(None, time.time())
    
    print(f"  传感器名称: {ft.name}")
    print(f"  力: {ft.force}")
    print(f"  力矩: {ft.torque}")
    print(f"  力大小: {ft.force_magnitude:.4f} N")
    print(f"  力矩大小: {ft.torque_magnitude:.4f} Nm")
    
    # 测试传感器套件
    print("\n--- 测试传感器套件 ---")
    suite = SensorSuite()
    suite.add_sensor(camera)
    suite.add_sensor(imu)
    suite.add_sensor(ft)
    
    print(f"  传感器数量: {len(suite._sensors)}")
    print(f"  相机数量: {len(suite.cameras)}")
    print(f"  IMU 数量: {len(suite.imus)}")
    print(f"  FT 传感器数量: {len(suite.ft_sensors)}")
    
    # 更新所有传感器
    all_data = suite.update_all(None, time.time())
    print(f"  更新后数据键: {list(all_data.keys())}")
    
    print("\n✅ 传感器系统测试通过")
    return True


def test_robot_interface():
    """测试机器人控制接口"""
    print("\n" + "=" * 60)
    print("🤖 测试机器人控制接口")
    print("=" * 60)
    
    # 创建机器人
    print("\n--- 创建机器人 ---")
    robot = GenesisBot(name="genesis_bot_v1")
    robot.initialize()
    
    print(f"  机器人名称: {robot.name}")
    print(f"  电池状态: {robot.battery}")
    
    # 测试底盘控制
    print("\n--- 测试底盘控制 ---")
    robot.set_velocity(0.5, 0.1)  # 0.5 m/s, 0.1 rad/s
    print(f"  设置速度: (0.5 m/s, 0.1 rad/s)")
    print(f"  当前速度: {robot.base.velocity}")
    print(f"  轮速: FL={robot.base.get_wheel_velocities()[0]:.3f}, "
          f"FR={robot.base.get_wheel_velocities()[1]:.3f}")
    
    # 模拟移动
    print("\n--- 模拟移动 (5秒) ---")
    for i in range(5):
        robot.update(1.0)
        pose = robot.get_base_pose()
        print(f"  t={i+1}s: 位置=({pose[0]:.3f}, {pose[1]:.3f}), 朝向={np.degrees(pose[2]):.1f}°")
    
    robot.stop_base()
    print(f"  停止后: is_moving={robot.base.is_moving}")
    
    # 测试手臂控制
    print("\n--- 测试手臂控制 ---")
    target_joints = np.array([0.5, -0.3, 0.2, 0.0, 0.1, 0.0])
    robot.move_arm_to_joints(ArmSide.LEFT, target_joints)
    print(f"  目标关节位置: {target_joints}")
    
    # 模拟手臂运动
    for i in range(10):
        robot.update(0.1)
    
    left_state = robot.get_arm_state(ArmSide.LEFT)
    print(f"  当前关节位置: {left_state.joint_state.positions}")
    print(f"  是否正在移动: {left_state.is_moving}")
    
    # 测试夹爪控制
    print("\n--- 测试夹爪控制 ---")
    robot.grasp(ArmSide.LEFT, width=0.05, force=30.0)
    print(f"  抓取指令: width=0.05m, force=30N")
    
    for i in range(5):
        robot.update(0.1)
    
    print(f"  夹爪状态: {robot.get_gripper_state(ArmSide.LEFT).value}")
    print(f"  夹爪宽度: {robot.left_gripper.width:.4f} m")
    
    robot.release(ArmSide.LEFT)
    print(f"  释放指令已发送")
    
    # 测试电池消耗
    print("\n--- 测试电池消耗 ---")
    initial_soc = robot.get_battery_soc()
    print(f"  初始电量: {initial_soc * 100:.1f}%")
    
    # 模拟运行
    robot.set_velocity(1.0, 0.0)
    for i in range(10):
        robot.update(1.0)
    
    final_soc = robot.get_battery_soc()
    print(f"  运行 10s 后电量: {final_soc * 100:.1f}%")
    print(f"  消耗: {(initial_soc - final_soc) * 100:.2f}%")
    
    # 获取完整状态
    print("\n--- 机器人完整状态 ---")
    state = robot.get_full_state()
    print(f"  名称: {state['name']}")
    print(f"  底盘位姿: {state['base']['pose']}")
    print(f"  左臂关节: {state['left_arm']['joint_positions']}")
    print(f"  电池 SOC: {state['battery']['soc_percent']:.1f}%")
    
    print("\n✅ 机器人控制接口测试通过")
    return True


def test_urdf_files():
    """测试 URDF 文件是否存在"""
    print("\n" + "=" * 60)
    print("📁 测试 URDF 文件")
    print("=" * 60)
    
    urdf_files = [
        "assets/robot/chassis.urdf",
        "assets/robot/arm.urdf",
        "assets/robot/gripper.urdf",
        "assets/robot/genesis_bot.urdf",
    ]
    
    all_exist = True
    for urdf_file in urdf_files:
        path = project_root / urdf_file
        exists = path.exists()
        all_exist = all_exist and exists
        status = "✅" if exists else "❌"
        print(f"  {status} {urdf_file}: {'存在' if exists else '不存在'}")
        
        if exists:
            # 检查文件大小
            size = path.stat().st_size
            print(f"      文件大小: {size / 1024:.1f} KB")
    
    if all_exist:
        print("\n✅ 所有 URDF 文件存在")
    else:
        print("\n❌ 部分 URDF 文件缺失")
    
    return all_exist


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GENESIS 机器人模块测试")
    parser.add_argument(
        "--test",
        choices=["all", "battery", "sensors", "robot", "urdf"],
        default="all",
        help="选择测试项目",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 GENESIS 机器人模块测试")
    print("=" * 60)
    
    results = {}
    
    # 运行测试
    if args.test in ["all", "battery"]:
        results["battery"] = test_battery()
    
    if args.test in ["all", "sensors"]:
        results["sensors"] = test_sensors()
    
    if args.test in ["all", "robot"]:
        results["robot"] = test_robot_interface()
    
    if args.test in ["all", "urdf"]:
        results["urdf"] = test_urdf_files()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        all_passed = all_passed and passed
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
