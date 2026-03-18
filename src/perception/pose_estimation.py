"""
GENESIS Perception - Pose Estimation Module

位姿估计模块，包括：
- PCA 位姿估计
- ICP 位姿估计
- 6D 位姿表示
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from scipy.spatial.transform import Rotation


@dataclass
class ObjectPose:
    """物体 6D 位姿"""
    position: np.ndarray  # [x, y, z] in world frame
    orientation: np.ndarray  # [qx, qy, qz, qw] quaternion
    covariance: Optional[np.ndarray] = None  # 6x6 位姿协方差矩阵
    timestamp: float = 0.0

    def __post_init__(self):
        """初始化后处理"""
        self.position = np.asarray(self.position, dtype=np.float64)
        self.orientation = np.asarray(self.orientation, dtype=np.float64)
        # 归一化四元数
        self.orientation = self.orientation / np.linalg.norm(self.orientation)

    @property
    def rotation_matrix(self) -> np.ndarray:
        """获取旋转矩阵 (3x3)"""
        return Rotation.from_quat(self.orientation).as_matrix()

    @property
    def transformation_matrix(self) -> np.ndarray:
        """获取变换矩阵 (4x4)"""
        T = np.eye(4)
        T[:3, :3] = self.rotation_matrix
        T[:3, 3] = self.position
        return T

    @property
    def euler_angles(self) -> np.ndarray:
        """获取欧拉角 [roll, pitch, yaw] (弧度)"""
        return Rotation.from_quat(self.orientation).as_euler("xyz")

    @property
    def yaw(self) -> float:
        """获取偏航角 (弧度)"""
        return self.euler_angles[2]

    @classmethod
    def from_matrix(cls, T: np.ndarray, timestamp: float = 0.0) -> "ObjectPose":
        """从变换矩阵创建"""
        position = T[:3, 3]
        orientation = Rotation.from_matrix(T[:3, :3]).as_quat()
        return cls(position=position, orientation=orientation, timestamp=timestamp)

    @classmethod
    def from_position_euler(
        cls,
        position: np.ndarray,
        euler: np.ndarray,
        timestamp: float = 0.0,
    ) -> "ObjectPose":
        """从位置和欧拉角创建"""
        orientation = Rotation.from_euler("xyz", euler).as_quat()
        return cls(position=position, orientation=orientation, timestamp=timestamp)

    def inverse(self) -> "ObjectPose":
        """获取逆位姿"""
        T_inv = np.linalg.inv(self.transformation_matrix)
        return ObjectPose.from_matrix(T_inv, self.timestamp)

    def transform_point(self, point: np.ndarray) -> np.ndarray:
        """变换点云"""
        point = np.asarray(point)
        if point.ndim == 1:
            point = point.reshape(1, 3)
        # 转换为齐次坐标
        points_homo = np.hstack([point, np.ones((len(point), 1))])
        # 变换
        transformed = (self.transformation_matrix @ points_homo.T).T
        return transformed[:, :3]

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "position": self.position.tolist(),
            "orientation": self.orientation.tolist(),
            "timestamp": self.timestamp,
        }


def estimate_pose_pca(
    point_cloud: np.ndarray,
    center: Optional[np.ndarray] = None,
) -> ObjectPose:
    """
    使用 PCA 估计物体位姿

    通过主成分分析确定物体的主轴方向。

    Args:
        point_cloud: 物体点云 (N, 3)
        center: 可选的中心位置，如果为 None 则使用点云质心

    Returns:
        估计的物体位姿
    """
    point_cloud = np.asarray(point_cloud)
    if len(point_cloud) < 3:
        raise ValueError("点云至少需要 3 个点")

    # 计算质心
    if center is None:
        center = np.mean(point_cloud, axis=0)

    # 中心化
    centered = point_cloud - center

    # 计算协方差矩阵
    cov = np.cov(centered.T)

    # 特征值分解
    eigenvalues, eigenvectors = np.linalg.eigh(cov)

    # 按特征值降序排列
    idx = np.argsort(eigenvalues)[::-1]
    eigenvectors = eigenvectors[:, idx]

    # 确保右手坐标系
    if np.linalg.det(eigenvectors) < 0:
        eigenvectors[:, 2] = -eigenvectors[:, 2]

    # 创建旋转矩阵
    rotation_matrix = eigenvectors

    # 转换为四元数
    orientation = Rotation.from_matrix(rotation_matrix).as_quat()

    return ObjectPose(position=center, orientation=orientation)


def estimate_pose_icp(
    source_points: np.ndarray,
    target_points: np.ndarray,
    initial_pose: Optional[ObjectPose] = None,
    max_iterations: int = 50,
    tolerance: float = 1e-6,
    inlier_threshold: float = 0.05,
) -> Tuple[ObjectPose, float]:
    """
    使用 ICP (Iterative Closest Point) 估计位姿

    Args:
        source_points: 源点云 (N, 3)
        target_points: 目标点云 (M, 3)
        initial_pose: 初始位姿估计
        max_iterations: 最大迭代次数
        tolerance: 收敛容差
        inlier_threshold: 内点距离阈值

    Returns:
        (估计位姿, 最终误差)
    """
    source_points = np.asarray(source_points, dtype=np.float64)
    target_points = np.asarray(target_points, dtype=np.float64)

    # 初始化变换
    if initial_pose is None:
        T = np.eye(4)
    else:
        T = initial_pose.transformation_matrix

    # 构建目标点云的 KD 树 (简化版，使用暴力搜索)
    prev_error = np.inf

    for iteration in range(max_iterations):
        # 变换源点云
        source_homo = np.hstack([source_points, np.ones((len(source_points), 1))])
        transformed = (T @ source_homo.T).T[:, :3]

        # 找最近点
        distances = []
        correspondences = []
        for i, sp in enumerate(transformed):
            dists = np.linalg.norm(target_points - sp, axis=1)
            j = np.argmin(dists)
            d = dists[j]
            if d < inlier_threshold:
                distances.append(d)
                correspondences.append((i, j))

        if len(correspondences) < 3:
            break

        # 计算当前误差
        current_error = np.mean(distances) if distances else np.inf

        # 检查收敛
        if abs(prev_error - current_error) < tolerance:
            break

        prev_error = current_error

        # 提取对应点
        src_matched = transformed[[c[0] for c in correspondences]]
        tgt_matched = target_points[[c[1] for c in correspondences]]

        # 计算最佳变换 (使用 SVD)
        src_center = np.mean(src_matched, axis=0)
        tgt_center = np.mean(tgt_matched, axis=0)

        src_centered = src_matched - src_center
        tgt_centered = tgt_matched - tgt_center

        H = src_centered.T @ tgt_centered
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T

        # 确保右手坐标系
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T

        t = tgt_center - R @ src_center

        # 更新变换
        delta_T = np.eye(4)
        delta_T[:3, :3] = R
        delta_T[:3, 3] = t
        T = delta_T @ T

    pose = ObjectPose.from_matrix(T)
    return pose, prev_error


class PoseEstimator:
    """
    位姿估计器

    结合 PCA 和 ICP 进行精确位姿估计。
    """

    def __init__(
        self,
        use_icp: bool = True,
        icp_iterations: int = 50,
        icp_tolerance: float = 1e-6,
        inlier_threshold: float = 0.05,
    ):
        """
        初始化位姿估计器

        Args:
            use_icp: 是否使用 ICP 精化
            icp_iterations: ICP 最大迭代次数
            icp_tolerance: ICP 收敛容差
            inlier_threshold: 内点距离阈值
        """
        self.use_icp = use_icp
        self.icp_iterations = icp_iterations
        self.icp_tolerance = icp_tolerance
        self.inlier_threshold = inlier_threshold

    def estimate(
        self,
        point_cloud: np.ndarray,
        reference_model: Optional[np.ndarray] = None,
        initial_pose: Optional[ObjectPose] = None,
    ) -> ObjectPose:
        """
        估计点云的位姿

        Args:
            point_cloud: 输入点云 (N, 3)
            reference_model: 参考模型点云 (用于 ICP)，如果为 None 则只使用 PCA
            initial_pose: 初始位姿估计

        Returns:
            估计的位姿
        """
        # 使用 PCA 获取初始估计
        if initial_pose is None:
            initial_pose = estimate_pose_pca(point_cloud)

        # 如果没有参考模型或不需要 ICP，直接返回
        if reference_model is None or not self.use_icp:
            return initial_pose

        # 使用 ICP 精化
        refined_pose, error = estimate_pose_icp(
            source_points=point_cloud,
            target_points=reference_model,
            initial_pose=initial_pose,
            max_iterations=self.icp_iterations,
            tolerance=self.icp_tolerance,
            inlier_threshold=self.inlier_threshold,
        )

        return refined_pose

    def estimate_from_depth(
        self,
        depth_image: np.ndarray,
        seg_mask: np.ndarray,
        intrinsics: "CameraIntrinsics",
        camera_pose: np.ndarray,
        class_id: int,
        reference_model: Optional[np.ndarray] = None,
    ) -> Optional[ObjectPose]:
        """
        从深度图估计特定位姿

        Args:
            depth_image: 深度图 (H, W)
            seg_mask: 语义分割图 (H, W)
            intrinsics: 相机内参
            camera_pose: 相机位姿 (4x4)
            class_id: 目标类别 ID
            reference_model: 参考模型点云

        Returns:
            估计的位姿，如果检测不到则返回 None
        """
        # 提取目标类别的掩码
        object_mask = (seg_mask == class_id)
        if not np.any(object_mask):
            return None

        # 获取像素坐标
        rows, cols = np.where(object_mask)
        depths = depth_image[rows, cols]

        # 过滤无效深度
        valid = depths > 0
        if not np.any(valid):
            return None

        rows = rows[valid]
        cols = cols[valid]
        depths = depths[valid]

        # 反投影到相机坐标系
        x = (cols - intrinsics.cx) * depths / intrinsics.fx
        y = (rows - intrinsics.cy) * depths / intrinsics.fy
        z = depths

        # 组合点云
        points_camera = np.stack([x, y, z], axis=-1)

        # 转换到世界坐标系
        points_homo = np.hstack([points_camera, np.ones((len(points_camera), 1))])
        points_world = (camera_pose @ points_homo.T).T[:, :3]

        # 估计位姿
        return self.estimate(points_world, reference_model)


def compute_pose_error(
    estimated: ObjectPose,
    ground_truth: ObjectPose,
) -> Tuple[float, float]:
    """
    计算位姿误差

    Args:
        estimated: 估计位姿
        ground_truth: 真实位姿

    Returns:
        (位置误差 (米), 角度误差 (度))
    """
    # 位置误差
    position_error = np.linalg.norm(estimated.position - ground_truth.position)

    # 角度误差 (使用四元数的点积)
    q1 = estimated.orientation
    q2 = ground_truth.orientation

    # 处理四元数的双覆盖性质
    dot = np.abs(np.dot(q1, q2))
    dot = np.clip(dot, -1.0, 1.0)
    angle_error = 2 * np.arccos(dot)
    angle_error_deg = np.degrees(angle_error)

    return position_error, angle_error_deg
