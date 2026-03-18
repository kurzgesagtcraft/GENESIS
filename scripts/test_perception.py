#!/usr/bin/env python3
"""
GENESIS Perception System Test Script

测试感知系统的各个模块：
- 物体检测与分割
- 位姿估计
- 工站对接检测
- 语义地图
- 资源追踪
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from perception import (
    # Segmentation
    DetectedObject,
    ObjectDetector,
    SemanticClass,
    CameraIntrinsics,
    add_realistic_noise,
    get_detected_objects,
    # Pose Estimation
    PoseEstimator,
    ObjectPose,
    estimate_pose_pca,
    estimate_pose_icp,
    compute_pose_error,
    # Dock Detection
    DockDetector,
    DockPose,
    ArUcoDetector,
    DockType,
    # Semantic Map
    SemanticMap,
    MapCell,
    OccupancyStatus,
    ZoneType,
    # Resource Tracker
    ResourceTracker,
    ResourceState,
    ZoneState,
)


def create_test_image(
    width: int = 640,
    height: int = 480,
    num_objects: int = 5,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    创建测试图像

    Returns:
        (rgb_image, depth_image, seg_mask)
    """
    # 创建 RGB 图像
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    rgb[:, :] = [100, 100, 100]  # 灰色背景

    # 创建深度图
    depth = np.ones((height, width), dtype=np.float32) * 5.0  # 5米远

    # 创建分割图
    seg = np.zeros((height, width), dtype=np.uint8)

    # 添加一些物体
    np.random.seed(42)
    for i in range(num_objects):
        # 随机位置和大小
        cx = np.random.randint(50, width - 50)
        cy = np.random.randint(50, height - 50)
        w = np.random.randint(30, 80)
        h = np.random.randint(30, 80)

        # 随机类别
        class_id = np.random.choice([
            SemanticClass.IRON_ORE.value,
            SemanticClass.SILICON_ORE.value,
            SemanticClass.IRON_BAR.value,
            SemanticClass.CIRCUIT_BOARD.value,
            SemanticClass.MOTOR.value,
        ])

        # 绘制矩形
        x1, y1 = max(0, cx - w // 2), max(0, cy - h // 2)
        x2, y2 = min(width, cx + w // 2), min(height, cy + h // 2)

        # 设置颜色
        colors = {
            SemanticClass.IRON_ORE.value: [139, 69, 19],  # 棕色
            SemanticClass.SILICON_ORE.value: [128, 128, 128],  # 灰色
            SemanticClass.IRON_BAR.value: [192, 192, 192],  # 银色
            SemanticClass.CIRCUIT_BOARD.value: [0, 128, 0],  # 绿色
            SemanticClass.MOTOR.value: [255, 165, 0],  # 橙色
        }
        rgb[y1:y2, x1:x2] = colors.get(class_id, [255, 255, 255])

        # 设置深度
        depth[y1:y2, x1:x2] = np.random.uniform(1.0, 3.0)

        # 设置分割
        seg[y1:y2, x1:x2] = class_id

    return rgb, depth, seg


def test_segmentation(verbose: bool = False) -> bool:
    """测试物体检测与分割"""
    print("\n" + "=" * 60)
    print("📦 测试: 物体检测与分割")
    print("=" * 60)

    try:
        # 创建测试图像
        rgb, depth, seg = create_test_image(num_objects=5)

        # 创建相机内参
        intrinsics = CameraIntrinsics.from_fov(640, 480, 70.0)

        if verbose:
            print(f"  图像尺寸: {rgb.shape}")
            print(f"  深度范围: {depth.min():.2f} - {depth.max():.2f} m")
            print(f"  分割类别: {np.unique(seg)}")

        # 测试检测器
        detector = ObjectDetector(min_confidence=0.3, min_pixels=50)
        objects = detector.detect(rgb, depth, seg, intrinsics)

        if verbose:
            print(f"\n  检测到 {len(objects)} 个物体:")
            for obj in objects:
                print(f"    - {obj.class_name}: 置信度 {obj.confidence:.2f}, "
                      f"位置 {obj.center_3d}")

        # 测试噪声添加
        rgb_noisy, depth_noisy, seg_noisy = add_realistic_noise(
            rgb, depth, seg,
            rgb_noise_std=10.0,
            depth_noise_std=0.01,
            seed=42,
        )

        if verbose:
            print(f"\n  噪声添加后:")
            print(f"    RGB 均值变化: {np.abs(rgb_noisy.astype(float) - rgb.astype(float)).mean():.2f}")
            print(f"    深度有效像素: {np.sum(depth_noisy > 0)}")

        # 测试便捷函数
        objects2 = get_detected_objects(rgb, depth, seg, intrinsics, add_noise=False)

        print(f"\n  ✅ 检测测试通过: 检测到 {len(objects)} 个物体")
        return True

    except Exception as e:
        print(f"\n  ❌ 检测测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pose_estimation(verbose: bool = False) -> bool:
    """测试位姿估计"""
    print("\n" + "=" * 60)
    print("📐 测试: 位姿估计")
    print("=" * 60)

    try:
        # 创建测试点云 (立方体)
        np.random.seed(42)
        points = np.random.uniform(-0.1, 0.1, (100, 3))
        points[:, 2] += 0.5  # 偏移到 z=0.5

        # 测试 PCA 位姿估计
        pose_pca = estimate_pose_pca(points)

        if verbose:
            print(f"  PCA 位姿估计:")
            print(f"    位置: {pose_pca.position}")
            print(f"    四元数: {pose_pca.orientation}")
            print(f"    欧拉角: {np.degrees(pose_pca.euler_angles)}")

        # 测试 ICP 位姿估计
        # 创建目标点云 (旋转后的)
        from scipy.spatial.transform import Rotation
        R = Rotation.from_euler("z", 30, degrees=True).as_matrix()
        target_points = (R @ points.T).T + np.array([0.1, 0.1, 0])

        pose_icp, error = estimate_pose_icp(points, target_points)

        if verbose:
            print(f"\n  ICP 位姿估计:")
            print(f"    位置: {pose_icp.position}")
            print(f"    误差: {error:.6f}")

        # 测试 ObjectPose 功能
        pose = ObjectPose(
            position=np.array([1.0, 2.0, 0.5]),
            orientation=np.array([0, 0, 0, 1]),
        )

        if verbose:
            print(f"\n  ObjectPose 测试:")
            print(f"    变换矩阵:\n{pose.transformation_matrix}")
            print(f"    Yaw 角: {np.degrees(pose.yaw):.2f}°")

        # 测试位姿误差计算
        gt_pose = ObjectPose(
            position=np.array([1.05, 2.0, 0.5]),
            orientation=np.array([0, 0, 0.0872, 0.9962]),  # ~10度旋转
        )
        pos_err, ang_err = compute_pose_error(pose, gt_pose)

        if verbose:
            print(f"\n  位姿误差:")
            print(f"    位置误差: {pos_err * 100:.2f} cm")
            print(f"    角度误差: {ang_err:.2f}°")

        print(f"\n  ✅ 位姿估计测试通过")
        return True

    except Exception as e:
        print(f"\n  ❌ 位姿估计测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dock_detection(verbose: bool = False) -> bool:
    """测试工站对接检测"""
    print("\n" + "=" * 60)
    print("🏭 测试: 工站对接检测")
    print("=" * 60)

    try:
        # 创建 ArUco 检测器
        aruco_detector = ArUcoDetector(marker_size=0.05)

        if verbose:
            print(f"  ArUco 字典: {aruco_detector.dictionary_name}")
            print(f"  Marker 尺寸: {aruco_detector.marker_size} m")

        # 创建对接检测器
        dock_detector = DockDetector(approach_distance=0.3)

        if verbose:
            print(f"  接近距离: {dock_detector.approach_distance} m")

        # 测试 marker ID 映射
        if verbose:
            print(f"\n  工站 Marker 映射:")
            for marker_id, info in DockDetector.STATION_MARKER_MAP.items():
                print(f"    ID {marker_id}: {info['name']} - {info['type'].name}")

        # 创建测试图像 (无 marker)
        rgb = np.zeros((480, 640, 3), dtype=np.uint8)
        depth = np.ones((480, 640), dtype=np.float32) * 2.0
        intrinsics = CameraIntrinsics.from_fov(640, 480, 70.0)
        camera_pose = np.eye(4)

        # 检测 (应该返回空列表)
        markers = aruco_detector.detect(rgb, depth, intrinsics, camera_pose)

        if verbose:
            print(f"\n  检测到 {len(markers)} 个 marker (预期 0)")

        print(f"\n  ✅ 工站对接检测测试通过")
        return True

    except Exception as e:
        print(f"\n  ❌ 工站对接检测测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_semantic_map(verbose: bool = False) -> bool:
    """测试语义地图"""
    print("\n" + "=" * 60)
    print("🗺️ 测试: 语义地图")
    print("=" * 60)

    try:
        # 创建语义地图
        semantic_map = SemanticMap(
            resolution=0.1,
            width=50.0,
            height=50.0,
        )

        if verbose:
            print(f"  地图尺寸: {semantic_map.grid_width} x {semantic_map.grid_height}")
            print(f"  分辨率: {semantic_map.resolution} m")

        # 测试坐标转换
        x, y = 25.0, 25.0
        gx, gy = semantic_map.world_to_grid(x, y)
        wx, wy = semantic_map.grid_to_world(gx, gy)

        if verbose:
            print(f"\n  坐标转换测试:")
            print(f"    世界坐标: ({x}, {y})")
            print(f"    栅格坐标: ({gx}, {gy})")
            print(f"    转换回来: ({wx:.2f}, {wy:.2f})")

        # 设置占据状态
        semantic_map.set_occupancy(10.0, 10.0, OccupancyStatus.OCCUPIED, 0.0)
        semantic_map.set_occupancy(10.5, 10.0, OccupancyStatus.FREE, 0.0)

        # 设置语义标签
        semantic_map.set_semantic(5.0, 35.0, ZoneType.MINE_IRON, 0.0)
        semantic_map.set_semantic(20.0, 35.0, ZoneType.MINE_SILICON, 0.0)

        # 添加物品
        semantic_map.add_item("iron_ore", np.array([10.0, 10.0, 0.0]), 0.0)
        semantic_map.add_item("iron_ore", np.array([10.5, 10.5, 0.0]), 0.0)

        if verbose:
            items = semantic_map.get_items("iron_ore")
            print(f"\n  物品记录:")
            print(f"    iron_ore 数量: {len(items['iron_ore'])}")

        # 测试路径检查
        start = np.array([5.0, 5.0])
        end = np.array([15.0, 15.0])
        is_clear = semantic_map.is_path_clear(start, end)

        if verbose:
            print(f"\n  路径检查: ({start}) -> ({end})")
            print(f"    是否畅通: {is_clear}")

        # 测试可视化
        vis_image = semantic_map.visualize()
        if verbose:
            print(f"\n  可视化图像尺寸: {vis_image.shape}")

        print(f"\n  ✅ 语义地图测试通过")
        return True

    except Exception as e:
        print(f"\n  ❌ 语义地图测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_resource_tracker(verbose: bool = False) -> bool:
    """测试资源追踪"""
    print("\n" + "=" * 60)
    print("📊 测试: 资源追踪")
    print("=" * 60)

    try:
        # 创建资源追踪器
        tracker = ResourceTracker(decay_rate=0.1, min_confidence=0.3)

        if verbose:
            print(f"  衰减率: {tracker.decay_rate}")
            print(f"  最小置信度: {tracker.min_confidence}")

        # 更新矿区观察
        tracker.update_mine_observation("mine_iron", "iron_ore", 100, 0.0)
        tracker.update_mine_observation("mine_silicon", "silicon_ore", 50, 0.0)

        if verbose:
            print(f"\n  矿区状态:")
            for name, state in tracker.get_all_mines().items():
                print(f"    {name}: {state.estimated_quantity} {state.resource_type} "
                      f"(置信度: {state.confidence:.2f})")

        # 更新仓库库存
        tracker.update_warehouse_item("iron_ore", 10, 0.0)
        tracker.update_warehouse_item("iron_bar", 5, 0.0)
        tracker.update_warehouse_item("iron_ore", -2, 1.0)  # 消耗 2 个

        if verbose:
            inventory = tracker.get_warehouse_inventory()
            print(f"\n  仓库库存:")
            for item_type, quantity in inventory.items():
                print(f"    {item_type}: {quantity}")

        # 更新工站状态
        tracker.update_station_state(
            "smelter", "smelter",
            ZoneState.PROCESSING,
            input_buffer={"iron_ore": 3},
            current_recipe="smelt_iron",
            process_remaining=25.0,
            timestamp=0.0,
        )

        if verbose:
            stations = tracker.get_all_stations()
            print(f"\n  工站状态:")
            for name, state in stations.items():
                print(f"    {name}: {state.state.name}")

        # 更新能量状态
        tracker.update_energy_state(
            battery_soc=0.85,
            solar_output=100.0,
            consumption_rate=50.0,
            net_energy=50.0,
            timestamp=0.0,
        )

        if verbose:
            energy = tracker.get_energy_state()
            print(f"\n  能量状态:")
            print(f"    电池电量: {energy.battery_soc * 100:.1f}%")
            print(f"    太阳能输出: {energy.solar_output:.1f} W")

        # 获取总资源
        totals = tracker.get_total_resources()
        if verbose:
            print(f"\n  总资源估计:")
            for resource_type, quantity in totals.items():
                print(f"    {resource_type}: {quantity}")

        # 获取摘要
        summary = tracker.get_summary()
        if verbose:
            print(f"\n  状态摘要键: {list(summary.keys())}")

        print(f"\n  ✅ 资源追踪测试通过")
        return True

    except Exception as e:
        print(f"\n  ❌ 资源追踪测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests(verbose: bool = False) -> Dict[str, bool]:
    """运行所有测试"""
    results = {}

    results["segmentation"] = test_segmentation(verbose)
    results["pose_estimation"] = test_pose_estimation(verbose)
    results["dock_detection"] = test_dock_detection(verbose)
    results["semantic_map"] = test_semantic_map(verbose)
    results["resource_tracker"] = test_resource_tracker(verbose)

    return results


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="GENESIS 感知系统测试")
    parser.add_argument(
        "--test", "-t",
        choices=["all", "segmentation", "pose", "dock", "map", "tracker"],
        default="all",
        help="要运行的测试",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="详细输出",
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🧪 GENESIS 感知系统测试")
    print("=" * 60)

    if args.test == "all":
        results = run_all_tests(args.verbose)
    elif args.test == "segmentation":
        results = {"segmentation": test_segmentation(args.verbose)}
    elif args.test == "pose":
        results = {"pose_estimation": test_pose_estimation(args.verbose)}
    elif args.test == "dock":
        results = {"dock_detection": test_dock_detection(args.verbose)}
    elif args.test == "map":
        results = {"semantic_map": test_semantic_map(args.verbose)}
    elif args.test == "tracker":
        results = {"resource_tracker": test_resource_tracker(args.verbose)}

    # 打印结果汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("🎉 所有测试通过！")
    else:
        print("⚠️ 部分测试失败")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
