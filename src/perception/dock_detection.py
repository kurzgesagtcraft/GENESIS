"""
GENESIS Perception - Dock Detection Module

工站对接检测模块，包括：
- ArUco marker 检测
- 工站位姿估计
- 对接点定位
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class DockType(Enum):
    """对接点类型"""
    INPUT_PORT = auto()  # 入料口
    OUTPUT_PORT = auto()  # 出料口
    CHARGING = auto()  # 充电口
    STORAGE = auto()  # 存储槽


@dataclass
class DockPose:
    """对接点位姿"""
    dock_type: DockType
    station_name: str
    pose: "ObjectPose"  # 对接点位姿
    approach_pose: "ObjectPose"  # 接近位姿 (用于导航)
    marker_id: Optional[int] = None  # ArUco marker ID
    confidence: float = 1.0
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "dock_type": self.dock_type.name,
            "station_name": self.station_name,
            "pose": self.pose.to_dict(),
            "approach_pose": self.approach_pose.to_dict(),
            "marker_id": self.marker_id,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class ArUcoMarker:
    """ArUco marker 信息"""
    marker_id: int
    corners: np.ndarray  # (4, 2) 角点像素坐标
    center: np.ndarray  # (2,) 中心像素坐标
    pose_3d: Optional["ObjectPose"] = None  # 3D 位姿

    @property
    def size_pixels(self) -> float:
        """获取 marker 在图像中的大小 (像素)"""
        # 计算边长平均值
        edges = [
            np.linalg.norm(self.corners[0] - self.corners[1]),
            np.linalg.norm(self.corners[1] - self.corners[2]),
            np.linalg.norm(self.corners[2] - self.corners[3]),
            np.linalg.norm(self.corners[3] - self.corners[0]),
        ]
        return np.mean(edges)


class ArUcoDetector:
    """
    ArUco marker 检测器

    检测图像中的 ArUco marker 并估计其位姿。
    """

    # ArUco 字典预定义
    ARUCO_DICTS = {
        "DICT_4X4_50": 0,
        "DICT_4X4_100": 1,
        "DICT_4X4_250": 2,
        "DICT_4X4_1000": 3,
        "DICT_5X5_50": 4,
        "DICT_5X5_100": 5,
        "DICT_5X5_250": 6,
        "DICT_5X5_1000": 7,
        "DICT_6X6_50": 8,
        "DICT_6X6_100": 9,
        "DICT_6X6_250": 10,
        "DICT_6X6_1000": 11,
        "DICT_7X7_50": 12,
        "DICT_7X7_100": 13,
        "DICT_7X7_250": 14,
        "DICT_7X7_1000": 15,
    }

    def __init__(
        self,
        dictionary_name: str = "DICT_4X4_50",
        marker_size: float = 0.05,  # marker 边长 (米)
    ):
        """
        初始化 ArUco 检测器

        Args:
            dictionary_name: ArUco 字典名称
            marker_size: marker 实际边长 (米)
        """
        self.dictionary_name = dictionary_name
        self.marker_size = marker_size
        self._cv2_available = self._check_cv2()

    def _check_cv2(self) -> bool:
        """检查 OpenCV 是否可用"""
        try:
            import cv2
            return True
        except ImportError:
            return False

    def detect(
        self,
        rgb_image: np.ndarray,
        depth_image: Optional[np.ndarray] = None,
        intrinsics: Optional["CameraIntrinsics"] = None,
        camera_pose: Optional[np.ndarray] = None,
    ) -> List[ArUcoMarker]:
        """
        检测图像中的 ArUco marker

        Args:
            rgb_image: RGB 图像 (H, W, 3)
            depth_image: 深度图 (H, W)，可选
            intrinsics: 相机内参，可选
            camera_pose: 相机位姿 (4x4)，可选

        Returns:
            检测到的 marker 列表
        """
        if not self._cv2_available:
            # 如果 OpenCV 不可用，返回模拟数据
            return self._detect_simulated(rgb_image)

        import cv2

        # 转换为灰度图
        if len(rgb_image.shape) == 3:
            gray = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2GRAY)
        else:
            gray = rgb_image

        # 获取 ArUco 字典
        aruco_dict = cv2.aruco.getPredefinedDictionary(
            self.ARUCO_DICTS.get(self.dictionary_name, 0)
        )
        parameters = cv2.aruco.DetectorParameters()

        # 创建检测器 (OpenCV 4.7+ 新 API)
        try:
            detector = cv2.aruco.ArucoDetector(aruco_dict, parameters)
            corners, ids, rejected = detector.detectMarkers(gray)
        except AttributeError:
            # 兼容旧版 OpenCV
            corners, ids, rejected = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)

        if ids is None:
            return []

        markers = []
        for i, marker_id in enumerate(ids.flatten()):
            # 获取角点
            corner = corners[i].reshape(4, 2)

            # 计算中心
            center = np.mean(corner, axis=0)

            marker = ArUcoMarker(
                marker_id=int(marker_id),
                corners=corner,
                center=center,
            )

            # 如果提供了内参和深度，估计 3D 位姿
            if intrinsics is not None and depth_image is not None:
                pose_3d = self._estimate_marker_pose(
                    marker, depth_image, intrinsics, camera_pose
                )
                marker.pose_3d = pose_3d

            markers.append(marker)

        return markers

    def _detect_simulated(self, rgb_image: np.ndarray) -> List[ArUcoMarker]:
        """模拟检测 (用于测试)"""
        # 返回空列表，实际应用中应该使用真实检测
        return []

    def _estimate_marker_pose(
        self,
        marker: ArUcoMarker,
        depth_image: np.ndarray,
        intrinsics: "CameraIntrinsics",
        camera_pose: Optional[np.ndarray],
    ) -> Optional["ObjectPose"]:
        """估计 marker 的 3D 位姿"""
        # 使用深度图估计 marker 中心深度
        cx, cy = int(marker.center[0]), int(marker.center[1])
        h, w = depth_image.shape

        if cx < 0 or cx >= w or cy < 0 or cy >= h:
            return None

        # 获取 marker 区域的平均深度
        x1, y1 = int(marker.corners[:, 0].min()), int(marker.corners[:, 1].min())
        x2, y2 = int(marker.corners[:, 0].max()), int(marker.corners[:, 1].max())
        x1, x2 = max(0, x1), min(w, x2)
        y1, y2 = max(0, y1), min(h, y2)

        depth_region = depth_image[y1:y2, x1:x2]
        valid_depths = depth_region[depth_region > 0]

        if len(valid_depths) == 0:
            return None

        z = np.median(valid_depths)

        # 反投影到相机坐标系
        x = (marker.center[0] - intrinsics.cx) * z / intrinsics.fx
        y = (marker.center[1] - intrinsics.cy) * z / intrinsics.fy

        position_camera = np.array([x, y, z])

        # 估计朝向 (简化：假设 marker 面向相机)
        # 实际应用中应该使用 cv2.aruco.estimatePoseSingleMarkers
        orientation_camera = np.array([0, 0, 0, 1])  # 单位四元数

        # 转换到世界坐标系
        if camera_pose is not None:
            position_homo = np.append(position_camera, 1)
            position_world = (camera_pose @ position_homo)[:3]

            # 旋转部分
            R_camera = Rotation.from_quat(orientation_camera).as_matrix()
            R_world = camera_pose[:3, :3] @ R_camera
            orientation_world = Rotation.from_matrix(R_world).as_quat()
        else:
            position_world = position_camera
            orientation_world = orientation_camera

        # 导入延迟
        from .pose_estimation import ObjectPose
        return ObjectPose(position=position_world, orientation=orientation_world)


class DockDetector:
    """
    工站对接检测器

    检测工站的入料口、出料口等对接点。
    """

    # 工站 marker ID 映射 (示例)
    STATION_MARKER_MAP = {
        # 冶炼站
        0: {"name": "smelter", "type": DockType.INPUT_PORT},
        1: {"name": "smelter", "type": DockType.OUTPUT_PORT},
        # 加工站
        10: {"name": "fabricator", "type": DockType.INPUT_PORT},
        11: {"name": "fabricator", "type": DockType.OUTPUT_PORT},
        # 装配站
        20: {"name": "assembler", "type": DockType.INPUT_PORT},
        21: {"name": "assembler", "type": DockType.OUTPUT_PORT},
        # 充电站
        100: {"name": "charging_dock", "type": DockType.CHARGING},
        # 仓库
        200: {"name": "warehouse", "type": DockType.STORAGE},
    }

    def __init__(
        self,
        aruco_detector: Optional[ArUcoDetector] = None,
        approach_distance: float = 0.3,  # 接近距离 (米)
    ):
        """
        初始化对接检测器

        Args:
            aruco_detector: ArUco 检测器
            approach_distance: 接近距离
        """
        self.aruco_detector = aruco_detector or ArUcoDetector()
        self.approach_distance = approach_distance

    def detect_docks(
        self,
        rgb_image: np.ndarray,
        depth_image: np.ndarray,
        intrinsics: "CameraIntrinsics",
        camera_pose: np.ndarray,
    ) -> List[DockPose]:
        """
        检测图像中的对接点

        Args:
            rgb_image: RGB 图像
            depth_image: 深度图
            intrinsics: 相机内参
            camera_pose: 相机位姿

        Returns:
            检测到的对接点列表
        """
        # 检测 ArUco marker
        markers = self.aruco_detector.detect(
            rgb_image, depth_image, intrinsics, camera_pose
        )

        docks = []
        for marker in markers:
            if marker.pose_3d is None:
                continue

            # 查找对应的工站信息
            station_info = self.STATION_MARKER_MAP.get(marker.marker_id)
            if station_info is None:
                continue

            # 创建对接位姿
            dock_pose = self._create_dock_pose(
                marker, station_info, camera_pose
            )
            if dock_pose is not None:
                docks.append(dock_pose)

        return docks

    def _create_dock_pose(
        self,
        marker: ArUcoMarker,
        station_info: Dict[str, Any],
        camera_pose: np.ndarray,
    ) -> Optional[DockPose]:
        """创建对接位姿"""
        from .pose_estimation import ObjectPose

        # 对接点位姿 (marker 位姿)
        dock_pose = marker.pose_3d

        # 计算接近位姿 (在 marker 前方一定距离)
        # 假设 marker 的 Z 轴指向外侧
        approach_position = dock_pose.position + \
            dock_pose.rotation_matrix[:, 2] * self.approach_distance

        # 接近位姿的朝向与对接点相反
        approach_orientation = dock_pose.orientation.copy()
        # 绕 Y 轴旋转 180 度
        R_approach = dock_pose.rotation_matrix @ np.array([
            [-1, 0, 0],
            [0, 1, 0],
            [0, 0, -1]
        ])
        from scipy.spatial.transform import Rotation
        approach_orientation = Rotation.from_matrix(R_approach).as_quat()

        approach_pose = ObjectPose(
            position=approach_position,
            orientation=approach_orientation,
        )

        return DockPose(
            dock_type=station_info["type"],
            station_name=station_info["name"],
            pose=dock_pose,
            approach_pose=approach_pose,
            marker_id=marker.marker_id,
            confidence=1.0,
            timestamp=dock_pose.timestamp,
        )

    def get_station_dock(
        self,
        station_name: str,
        dock_type: DockType,
        detected_docks: List[DockPose],
    ) -> Optional[DockPose]:
        """
        获取指定工站的对接点

        Args:
            station_name: 工站名称
            dock_type: 对接点类型
            detected_docks: 检测到的对接点列表

        Returns:
            匹配的对接点，如果没有则返回 None
        """
        for dock in detected_docks:
            if dock.station_name == station_name and dock.dock_type == dock_type:
                return dock
        return None


# 延迟导入处理
from scipy.spatial.transform import Rotation
