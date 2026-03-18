"""
GENESIS Perception System

感知系统模块，包括：
- 物体检测与分割
- 位姿估计
- 场景理解
- 语义地图构建
"""

from .segmentation import (
    DetectedObject,
    ObjectDetector,
    SemanticClass,
    CameraIntrinsics,
    add_realistic_noise,
    get_detected_objects,
)

from .pose_estimation import (
    PoseEstimator,
    ObjectPose,
    estimate_pose_pca,
    estimate_pose_icp,
    compute_pose_error,
)

from .dock_detection import (
    DockDetector,
    DockPose,
    ArUcoDetector,
    DockType,
)

from .semantic_map import (
    SemanticMap,
    MapCell,
    OccupancyStatus,
    ZoneType,
)

from .resource_tracker import (
    ResourceTracker,
    ResourceState,
    ZoneState,
)

__all__ = [
    # Segmentation
    "DetectedObject",
    "ObjectDetector",
    "SemanticClass",
    "CameraIntrinsics",
    "add_realistic_noise",
    "get_detected_objects",
    # Pose Estimation
    "PoseEstimator",
    "ObjectPose",
    "estimate_pose_pca",
    "estimate_pose_icp",
    "compute_pose_error",
    # Dock Detection
    "DockDetector",
    "DockPose",
    "ArUcoDetector",
    "DockType",
    # Semantic Map
    "SemanticMap",
    "MapCell",
    "OccupancyStatus",
    "ZoneType",
    # Resource Tracker
    "ResourceTracker",
    "ResourceState",
    "ZoneState",
]
