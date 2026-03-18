"""
GENESIS Perception - Segmentation Module

物体检测与分割模块，包括：
- 语义分割处理
- 物体检测
- 3D 定位
- 噪声模拟 (sim-to-real)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class SemanticClass(Enum):
    """语义类别枚举"""
    BACKGROUND = 0
    # 矿石类
    IRON_ORE = 1
    SILICON_ORE = 2
    # 加工品
    IRON_BAR = 3
    CIRCUIT_BOARD = 4
    MOTOR = 5
    JOINT_MODULE = 6
    FRAME_SEGMENT = 7
    CONTROLLER_BOARD = 8
    GRIPPER_FINGER = 9
    # 设施
    WORKSTATION = 10
    CHARGING_DOCK = 11
    ROBOT = 12
    # 装配件
    ASSEMBLED_ARM = 13
    ASSEMBLED_ROBOT = 14
    # 区域标记
    MINE_ZONE = 20
    WAREHOUSE = 21
    PATH = 22

    @classmethod
    def from_id(cls, class_id: int) -> "SemanticClass":
        """从 ID 获取枚举值"""
        for member in cls:
            if member.value == class_id:
                return member
        return cls.BACKGROUND

    @property
    def item_type(self) -> Optional[str]:
        """获取对应的物品类型字符串"""
        type_map = {
            cls.IRON_ORE: "iron_ore",
            cls.SILICON_ORE: "silicon_ore",
            cls.IRON_BAR: "iron_bar",
            cls.CIRCUIT_BOARD: "circuit_board",
            cls.MOTOR: "motor",
            cls.JOINT_MODULE: "joint_module",
            cls.FRAME_SEGMENT: "frame_segment",
            cls.CONTROLLER_BOARD: "controller_board",
            cls.GRIPPER_FINGER: "gripper_finger",
            cls.ASSEMBLED_ARM: "assembled_arm",
            cls.ASSEMBLED_ROBOT: "assembled_robot",
        }
        return type_map.get(self)


@dataclass
class DetectedObject:
    """检测到的物体"""
    class_name: str
    class_id: int
    confidence: float
    bbox_2d: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    center_3d: np.ndarray  # [x, y, z] in world frame
    estimated_size: np.ndarray  # [width, height, depth] in meters
    mask: Optional[np.ndarray] = None  # 分割掩码
    point_cloud: Optional[np.ndarray] = None  # 物体点云 (N, 3)
    timestamp: float = 0.0

    def __post_init__(self):
        """初始化后处理"""
        self.center_3d = np.asarray(self.center_3d, dtype=np.float32)
        self.estimated_size = np.asarray(self.estimated_size, dtype=np.float32)

    @property
    def position(self) -> np.ndarray:
        """获取 3D 位置"""
        return self.center_3d

    @property
    def bbox_area(self) -> int:
        """获取 2D 边界框面积"""
        return (self.bbox_2d[2] - self.bbox_2d[0]) * (self.bbox_2d[3] - self.bbox_2d[1])

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "class_name": self.class_name,
            "class_id": self.class_id,
            "confidence": self.confidence,
            "bbox_2d": self.bbox_2d,
            "center_3d": self.center_3d.tolist(),
            "estimated_size": self.estimated_size.tolist(),
            "timestamp": self.timestamp,
        }


@dataclass
class CameraIntrinsics:
    """相机内参"""
    fx: float  # 焦距 x
    fy: float  # 焦距 y
    cx: float  # 光心 x
    cy: float  # 光心 y
    width: int  # 图像宽度
    height: int  # 图像高度

    @classmethod
    def from_fov(cls, width: int, height: int, fov_degrees: float) -> "CameraIntrinsics":
        """从视场角创建内参"""
        fov_rad = np.radians(fov_degrees)
        fx = width / (2 * np.tan(fov_rad / 2))
        fy = fx
        cx = width / 2
        cy = height / 2
        return cls(fx=fx, fy=fy, cx=cx, cy=cy, width=width, height=height)

    @property
    def matrix(self) -> np.ndarray:
        """获取内参矩阵"""
        return np.array([
            [self.fx, 0, self.cx],
            [0, self.fy, self.cy],
            [0, 0, 1]
        ])


class ObjectDetector:
    """
    物体检测器

    从 RGB-D 图像和语义分割图中检测物体并计算其 3D 位置。
    """

    def __init__(
        self,
        min_confidence: float = 0.5,
        min_pixels: int = 100,
        depth_truncation: float = 10.0,
    ):
        """
        初始化检测器

        Args:
            min_confidence: 最小置信度阈值
            min_pixels: 最小像素数量阈值
            depth_truncation: 深度截断距离 (米)
        """
        self.min_confidence = min_confidence
        self.min_pixels = min_pixels
        self.depth_truncation = depth_truncation

    def detect(
        self,
        rgb_image: np.ndarray,
        depth_image: np.ndarray,
        seg_mask: np.ndarray,
        intrinsics: CameraIntrinsics,
        camera_pose: Optional[np.ndarray] = None,
    ) -> List[DetectedObject]:
        """
        检测图像中的物体

        Args:
            rgb_image: RGB 图像 (H, W, 3)
            depth_image: 深度图 (H, W)
            seg_mask: 语义分割图 (H, W)
            intrinsics: 相机内参
            camera_pose: 相机位姿 (4x4 变换矩阵)，如果为 None 则使用单位矩阵

        Returns:
            检测到的物体列表
        """
        if camera_pose is None:
            camera_pose = np.eye(4)

        detected_objects = []

        # 获取所有非背景类别
        unique_classes = np.unique(seg_mask)
        unique_classes = unique_classes[unique_classes != 0]  # 排除背景

        for class_id in unique_classes:
            # 创建当前类别的掩码
            class_mask = (seg_mask == class_id).astype(np.uint8)

            # 计算像素数量
            pixel_count = np.sum(class_mask)
            if pixel_count < self.min_pixels:
                continue

            # 获取类别信息
            semantic_class = SemanticClass.from_id(class_id)
            class_name = semantic_class.name.lower()

            # 计算 2D 边界框
            rows, cols = np.where(class_mask)
            x1, x2 = cols.min(), cols.max()
            y1, y2 = rows.min(), rows.max()
            bbox_2d = (int(x1), int(y1), int(x2), int(y2))

            # 提取物体区域的深度值
            object_depths = depth_image[class_mask == 1]
            valid_depth_mask = (object_depths > 0) & (object_depths < self.depth_truncation)

            if not np.any(valid_depth_mask):
                continue

            valid_depths = object_depths[valid_depth_mask]

            # 计算平均深度
            mean_depth = np.mean(valid_depths)

            # 获取物体区域的像素坐标
            obj_rows, obj_cols = np.where(class_mask == 1)

            # 过滤有效深度的像素
            valid_mask = (depth_image[obj_rows, obj_cols] > 0) & \
                         (depth_image[obj_rows, obj_cols] < self.depth_truncation)
            valid_rows = obj_rows[valid_mask]
            valid_cols = obj_cols[valid_mask]
            valid_depths = depth_image[valid_rows, valid_cols]

            if len(valid_depths) == 0:
                continue

            # 反投影到相机坐标系
            x_camera = (valid_cols - intrinsics.cx) * valid_depths / intrinsics.fx
            y_camera = (valid_rows - intrinsics.cy) * valid_depths / intrinsics.fy
            z_camera = valid_depths

            # 组合点云 (N, 3)
            points_camera = np.stack([x_camera, y_camera, z_camera], axis=-1)

            # 转换到世界坐标系
            # 扩展点云为齐次坐标
            points_homo = np.hstack([points_camera, np.ones((len(points_camera), 1))])
            points_world = (camera_pose @ points_homo.T).T[:, :3]

            # 计算 3D 中心
            center_3d = np.mean(points_world, axis=0)

            # 估计尺寸
            if len(points_world) > 10:
                # 使用点云的主成分分析估计尺寸
                centered = points_world - center_3d
                cov = np.cov(centered.T)
                eigenvalues, _ = np.linalg.eigh(cov)
                eigenvalues = np.sort(eigenvalues)[::-1]
                # 尺寸估计为 2 倍标准差
                estimated_size = 4 * np.sqrt(eigenvalues)
                estimated_size = np.maximum(estimated_size, 0.01)  # 最小 1cm
            else:
                # 使用默认尺寸
                estimated_size = np.array([0.1, 0.1, 0.1])

            # 计算置信度 (基于像素数量和深度一致性)
            depth_std = np.std(valid_depths)
            confidence = min(1.0, pixel_count / 1000) * np.exp(-depth_std / 0.1)
            confidence = max(self.min_confidence, min(1.0, confidence))

            # 创建检测对象
            detected_obj = DetectedObject(
                class_name=class_name,
                class_id=int(class_id),
                confidence=float(confidence),
                bbox_2d=bbox_2d,
                center_3d=center_3d,
                estimated_size=estimated_size,
                mask=class_mask,
                point_cloud=points_world,
            )

            detected_objects.append(detected_obj)

        return detected_objects


def add_realistic_noise(
    rgb_image: np.ndarray,
    depth_image: np.ndarray,
    seg_mask: np.ndarray,
    rgb_noise_std: float = 5.0,
    depth_noise_std: float = 0.005,
    dropout_rate: float = 0.05,
    brightness_range: Tuple[float, float] = (0.9, 1.1),
    contrast_range: Tuple[float, float] = (0.9, 1.1),
    occlusion_prob: float = 0.1,
    occlusion_size_range: Tuple[int, int] = (10, 50),
    seed: Optional[int] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    添加真实感噪声以提高 sim-to-real 泛化能力

    Args:
        rgb_image: RGB 图像 (H, W, 3)
        depth_image: 深度图 (H, W)
        seg_mask: 语义分割图 (H, W)
        rgb_noise_std: RGB 高斯噪声标准差
        depth_noise_std: 深度高斯噪声标准差 (米)
        dropout_rate: 深度图像素丢失率
        brightness_range: 亮度变化范围
        contrast_range: 对比度变化范围
        occlusion_prob: 遮挡概率
        occlusion_size_range: 遮挡尺寸范围 (像素)
        seed: 随机种子

    Returns:
        带噪声的 (rgb, depth, seg_mask)
    """
    if seed is not None:
        np.random.seed(seed)

    # 复制输入图像
    rgb_noisy = rgb_image.copy().astype(np.float32)
    depth_noisy = depth_image.copy().astype(np.float32)
    seg_noisy = seg_mask.copy()

    # 1. RGB 高斯噪声
    if rgb_noise_std > 0:
        rgb_noise = np.random.normal(0, rgb_noise_std, rgb_noisy.shape)
        rgb_noisy = rgb_noisy + rgb_noise

    # 2. 亮度变化
    brightness_factor = np.random.uniform(*brightness_range)
    rgb_noisy = rgb_noisy * brightness_factor

    # 3. 对比度变化
    contrast_factor = np.random.uniform(*contrast_range)
    mean_val = np.mean(rgb_noisy)
    rgb_noisy = (rgb_noisy - mean_val) * contrast_factor + mean_val

    # 4. 深度高斯噪声
    if depth_noise_std > 0:
        depth_noise = np.random.normal(0, depth_noise_std, depth_noisy.shape)
        depth_noisy = depth_noisy + depth_noise

    # 5. 深度图像素丢失 (模拟反射/遮挡)
    if dropout_rate > 0:
        dropout_mask = np.random.random(depth_noisy.shape) < dropout_rate
        depth_noisy[dropout_mask] = 0

    # 6. 随机遮挡 (模拟物体遮挡)
    if occlusion_prob > 0 and np.random.random() < occlusion_prob:
        h, w = rgb_noisy.shape[:2]
        num_occlusions = np.random.randint(1, 4)
        for _ in range(num_occlusions):
            occ_h = np.random.randint(*occlusion_size_range)
            occ_w = np.random.randint(*occlusion_size_range)
            y = np.random.randint(0, h - occ_h)
            x = np.random.randint(0, w - occ_w)
            # 用随机颜色填充
            rgb_noisy[y:y+occ_h, x:x+occ_w] = np.random.randint(0, 256, (3,))
            depth_noisy[y:y+occ_h, x:x+occ_w] = 0
            seg_noisy[y:y+occ_h, x:x+occ_w] = 0

    # 裁剪到有效范围
    rgb_noisy = np.clip(rgb_noisy, 0, 255).astype(np.uint8)
    depth_noisy = np.clip(depth_noisy, 0, np.inf).astype(np.float32)

    return rgb_noisy, depth_noisy, seg_noisy


def get_detected_objects(
    rgb_image: np.ndarray,
    depth_image: np.ndarray,
    seg_mask: np.ndarray,
    intrinsics: CameraIntrinsics,
    camera_pose: Optional[np.ndarray] = None,
    add_noise: bool = False,
    noise_seed: Optional[int] = None,
) -> List[DetectedObject]:
    """
    便捷函数：从图像获取检测到的物体

    Args:
        rgb_image: RGB 图像 (H, W, 3)
        depth_image: 深度图 (H, W)
        seg_mask: 语义分割图 (H, W)
        intrinsics: 相机内参
        camera_pose: 相机位姿 (4x4 变换矩阵)
        add_noise: 是否添加噪声
        noise_seed: 噪声随机种子

    Returns:
        检测到的物体列表
    """
    # 添加噪声 (可选)
    if add_noise:
        rgb_image, depth_image, seg_mask = add_realistic_noise(
            rgb_image, depth_image, seg_mask, seed=noise_seed
        )

    # 创建检测器
    detector = ObjectDetector()

    # 执行检测
    objects = detector.detect(rgb_image, depth_image, seg_mask, intrinsics, camera_pose)

    return objects
