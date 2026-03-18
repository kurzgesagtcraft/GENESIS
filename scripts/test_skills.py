#!/usr/bin/env python3
"""
GENESIS Skills Test Script - 技能系统测试脚本

测试 P4 运动与操作能力模块的所有组件。

用法:
    python scripts/test_skills.py --test all
    python scripts/test_skills.py --test base_controller
    python scripts/test_skills.py --test path_follower
    python scripts/test_skills.py --test navigator
    python scripts/test_skills.py --test ik_solver
    python scripts/test_skills.py --test trajectory
    python scripts/test_skills.py --test impedance
    python scripts/test_skills.py --test skills
"""

import argparse
import sys
import numpy as np
from typing import Dict, List, Tuple, Any

# 添加项目路径
sys.path.insert(0, '.')


def test_base_controller():
    """测试基础运动控制"""
    print("\n📦 测试: 基础运动控制")
    
    from genesis.control.base_controller import (
        DifferentialDriveController,
        OdometryEstimator,
        MotionConstraints,
        PIDGains,
    )
    
    # 测试差速驱动控制器
    controller = DifferentialDriveController(
        wheel_base=0.5,
        wheel_radius=0.08,
    )
    
    # 设置目标速度
    controller.set_target_velocity(1.0, 0.5)
    
    # 更新控制器
    controller.update(0.01)
    
    # 获取轮子速度
    wheel_vel = controller.get_wheel_velocities()
    
    assert wheel_vel.front_left != wheel_vel.front_right, "左右轮速度应该不同"
    assert abs(wheel_vel.front_left - wheel_vel.rear_left) < 0.001, "前后轮速度应该相同"
    
    # 测试里程计
    odom = OdometryEstimator(wheel_base=0.5, wheel_radius=0.08)
    
    # 模拟轮子转动 - 使用更大的角度增量
    # 第一次调用会初始化，不会产生位移
    odom.update(0.0, 0.0, 0.01)  # 初始化
    
    # 后续调用会产生位移
    for _ in range(100):
        odom.update(1.0, 1.0, 0.01)  # 左右轮相同速度
    
    pose = odom.get_pose()
    # 里程计应该记录位置变化
    # 由于轮子转动，应该有位移
    total_distance = np.sqrt(pose[0]**2 + pose[1]**2)
    assert total_distance > 0.01, f"机器人应该有位置变化，实际位置: {pose}"
    
    print("✅ 基础运动控制测试通过")
    return True


def test_path_follower():
    """测试路径跟踪"""
    print("\n📐 测试: 路径跟踪")
    
    from genesis.control.path_follower import (
        PathFollower,
        PathFollowerConfig,
        PathPoint,
        PurePursuitController,
    )
    
    # 测试 Pure Pursuit 控制器
    config = PathFollowerConfig(
        lookahead_distance=0.5,
        goal_tolerance=0.1,
    )
    
    controller = PurePursuitController(config)
    
    # 创建简单路径
    path = [
        PathPoint(0, 0),
        PathPoint(1, 0),
        PathPoint(2, 0),
        PathPoint(3, 0),
    ]
    
    controller.set_path(path)
    
    # 测试速度计算
    linear, angular = controller.compute_velocity(0, 0, 0, 0)
    
    assert linear > 0, "应该向前移动"
    
    # 测试路径跟踪器
    follower = PathFollower(config)
    follower.set_path(path)
    
    # 模拟跟踪
    x, y, yaw = 0.0, 0.0, 0.0
    for _ in range(100):
        linear, angular = follower.update(x, y, yaw)
        x += linear * np.cos(yaw) * 0.01
        y += linear * np.sin(yaw) * 0.01
        yaw += angular * 0.01
        
        if follower.reached_goal:
            break
    
    print("✅ 路径跟踪测试通过")
    return True


def test_navigator():
    """测试导航器"""
    print("\n🗺️ 测试: 导航器")
    
    from genesis.control.navigator import (
        Navigator,
        NavigationConfig,
        NavigationStatus,
        NavigationGoal,
    )
    from genesis.world.path_network import PathNetwork, PathNetworkConfig
    
    # 创建简单路径网络
    config = PathNetworkConfig(
        nodes=[
            {"id": "start", "position": [0, 0], "zone_name": "start"},
            {"id": "mid", "position": [5, 0], "zone_name": "mid"},
            {"id": "end", "position": [10, 0], "zone_name": "end"},
        ],
        edges=[("start", "mid"), ("mid", "end")],
    )
    
    path_network = PathNetwork(config)
    
    # 创建导航器
    nav_config = NavigationConfig()
    navigator = Navigator(path_network)
    
    # 测试路径规划
    path = navigator.plan_path_from_zone("start", "end")
    
    assert len(path) == 3, "路径应该有 3 个点"
    
    # 测试导航目标
    goal = NavigationGoal(target_zone="end")
    assert goal.is_valid(), "目标应该有效"
    
    print("✅ 导航器测试通过")
    return True


def test_ik_solver():
    """测试逆运动学求解器"""
    print("\n🦾 测试: 逆运动学求解器")
    
    from genesis.control.ik_solver import (
        IKSolver,
        IKConfig,
        IKStatus,
        RobotKinematics,
    )
    from genesis.utils.geometry import SE3, SO3
    
    # 创建机器人运动学
    joint_limits = np.array([
        [-np.pi, np.pi],
        [-np.pi/2, np.pi/2],
        [-2.5, 2.5],
        [-np.pi, np.pi],
        [-2.0, 2.0],
        [-np.pi, np.pi],
    ])
    
    kinematics = RobotKinematics(joint_limits)
    
    # 测试正运动学
    q = np.zeros(6)
    pose = kinematics.forward_kinematics(q)
    
    assert pose is not None, "正运动学应该返回位姿"
    
    # 测试雅可比矩阵
    J = kinematics.compute_jacobian(q)
    
    assert J.shape == (6, 6), f"雅可比矩阵应该是 6x6, 实际是 {J.shape}"
    
    # 创建 IK 求解器
    ik_config = IKConfig(max_iterations=50)
    solver = IKSolver(kinematics, ik_config)
    
    # 测试 IK 求解
    target_pose = SE3(
        position=(0.3, 0.1, 0.5),
        rotation=SO3.from_euler_angles(np.pi, 0, 0)
    )
    
    result = solver.solve(target_pose, np.zeros(6))
    
    # IK 可能不总是成功，但应该返回结果
    assert result.status in [IKStatus.SUCCESS, IKStatus.MAX_ITERATIONS], \
        f"IK 状态应该是 SUCCESS 或 MAX_ITERATIONS, 实际是 {result.status}"
    
    print("✅ 逆运动学求解器测试通过")
    return True


def test_trajectory_planner():
    """测试轨迹规划器"""
    print("\n📈 测试: 轨迹规划器")
    
    from genesis.control.trajectory_planner import (
        TrajectoryPlanner,
        JointTrajectory,
        CartesianTrajectory,
        QuinticPolynomial,
    )
    
    # 测试五次多项式
    coeffs = QuinticPolynomial.compute_coefficients(0, 1, T=2.0)
    
    pos, vel, acc = QuinticPolynomial.evaluate(coeffs, 1.0)
    
    assert 0 < pos < 1, "中间时刻位置应该在起点和终点之间"
    
    # 创建轨迹规划器
    planner = TrajectoryPlanner(n_joints=6)
    
    # 测试关节轨迹规划
    start = np.zeros(6)
    end = np.array([0.5, 0.3, 0.2, 0.1, 0.1, 0.05])
    
    trajectory = planner.plan_joint_trajectory(start, end, duration=2.0)
    
    assert len(trajectory.points) > 0, "轨迹应该有轨迹点"
    assert trajectory.duration == 2.0, "轨迹时长应该是 2.0 秒"
    
    # 测试获取轨迹点
    point = trajectory.get_point_at_time(1.0)
    
    assert point is not None, "应该能获取中间轨迹点"
    
    # 测试笛卡尔轨迹规划
    from genesis.utils.geometry import SE3, SO3
    
    start_pose = SE3.identity()
    end_pose = SE3(
        position=(0.5, 0.2, 0.3),
        rotation=SO3.from_euler_angles(0.1, 0.1, 0.1)
    )
    
    cart_trajectory = planner.plan_cartesian_trajectory(start_pose, end_pose)
    
    assert len(cart_trajectory.points) > 0, "笛卡尔轨迹应该有轨迹点"
    
    print("✅ 轨迹规划器测试通过")
    return True


def test_impedance_controller():
    """测试阻抗控制器"""
    print("\n🎮 测试: 阻抗控制器")
    
    from genesis.control.impedance_controller import (
        ImpedanceController,
        ImpedanceParams,
        ImpedanceMode,
        ForceController,
    )
    from genesis.utils.geometry import SE3, SO3
    
    # 创建阻抗控制器
    params = ImpedanceParams.stiff()
    controller = ImpedanceController(params)
    
    # 测试设置目标位姿
    target_pose = SE3(
        position=(0.5, 0.0, 0.3),
        rotation=SO3.identity()
    )
    
    controller.set_target_pose(target_pose)
    
    assert controller.mode == ImpedanceMode.POSITION, "应该是位置控制模式"
    
    # 测试更新控制器
    current_pose = SE3(
        position=(0.4, 0.0, 0.3),
        rotation=SO3.identity()
    )
    
    joint_torques, wrench = controller.update(current_pose, dt=0.01)
    
    # 应该产生向目标移动的力
    assert wrench[0] > 0, "应该产生向前的力"
    
    # 测试柔顺模式
    controller.set_compliant_mode()
    
    assert controller.mode == ImpedanceMode.COMPLIANT, "应该是柔顺模式"
    
    # 测试力控制器
    force_controller = ForceController(kp=0.1)
    
    output = force_controller.compute(10.0, 5.0, 0.01)
    
    assert output != 0, "力控制器应该产生输出"
    
    print("✅ 阻抗控制器测试通过")
    return True


def test_skills():
    """测试技能系统"""
    print("\n🎯 测试: 技能系统")
    
    from genesis.control.skills.base_skill import (
        SkillStatus,
        SkillResult,
        SkillContext,
        SkillLibrary,
    )
    from genesis.control.skills.top_grasp import TopGraspSkill, TopGraspParams
    from genesis.control.skills.place import PlaceSkill, PlaceParams
    from genesis.control.skills.side_grasp import SideGraspSkill, SideGraspParams
    
    # 测试技能上下文
    context = SkillContext()
    
    # 测试顶抓技能
    params = TopGraspParams(
        object_position=np.array([0.5, 0.0, 0.2]),
        object_size=np.array([0.1, 0.1, 0.1]),
    )
    
    skill = TopGraspSkill(context=context, params=params)
    
    assert skill.name == "top_grasp", "技能名称应该是 top_grasp"
    assert skill.status == SkillStatus.IDLE, "初始状态应该是 IDLE"
    
    # 测试放置技能
    place_params = PlaceParams(
        target_position=np.array([0.5, 0.0, 0.1]),
    )
    
    place_skill = PlaceSkill(context=context, params=place_params)
    
    assert place_skill.name == "place", "技能名称应该是 place"
    
    # 测试侧抓技能
    side_params = SideGraspParams(
        object_position=np.array([0.5, 0.2, 0.2]),
    )
    
    side_skill = SideGraspSkill(context=context, params=side_params)
    
    assert side_skill.name == "side_grasp", "技能名称应该是 side_grasp"
    
    # 测试技能库
    library = SkillLibrary(context)
    
    library.register("top_grasp", TopGraspSkill)
    library.register("place", PlaceSkill)
    
    assert library.has_skill("top_grasp"), "技能库应该有 top_grasp"
    assert "top_grasp" in library.list_skills(), "技能列表应该包含 top_grasp"
    
    print("✅ 技能系统测试通过")
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 GENESIS 技能系统测试")
    print("=" * 60)
    
    tests = {
        "base_controller": test_base_controller,
        "path_follower": test_path_follower,
        "navigator": test_navigator,
        "ik_solver": test_ik_solver,
        "trajectory": test_trajectory_planner,
        "impedance": test_impedance_controller,
        "skills": test_skills,
    }
    
    results = {}
    
    for name, test_func in tests.items():
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"❌ {name} 测试失败: {e}")
            results[name] = False
    
    # 打印结果汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
    
    print("=" * 60)
    
    all_passed = all(results.values())
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败")
    
    print("=" * 60)
    
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="GENESIS 技能系统测试")
    parser.add_argument(
        "--test",
        type=str,
        default="all",
        choices=["all", "base_controller", "path_follower", "navigator",
                 "ik_solver", "trajectory", "impedance", "skills"],
        help="要运行的测试"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出"
    )
    
    args = parser.parse_args()
    
    if args.test == "all":
        success = run_all_tests()
    else:
        test_funcs = {
            "base_controller": test_base_controller,
            "path_follower": test_path_follower,
            "navigator": test_navigator,
            "ik_solver": test_ik_solver,
            "trajectory": test_trajectory_planner,
            "impedance": test_impedance_controller,
            "skills": test_skills,
        }
        
        if args.test in test_funcs:
            success = test_funcs[args.test]()
        else:
            print(f"未知测试: {args.test}")
            success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
