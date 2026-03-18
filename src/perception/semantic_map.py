"""
GENESIS Perception - Semantic Map Module

语义地图构建模块，包括：
- 2D 栅格地图
- 占据状态管理
- 语义标签存储
- 实时更新
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class OccupancyStatus(Enum):
    """占据状态"""
    UNKNOWN = 0
    FREE = 1
    OCCUPIED = 2
    OBSTACLE = 3


class ZoneType(Enum):
    """区域类型"""
    UNKNOWN = 0
    MINE_IRON = 1
    MINE_SILICON = 2
    PROCESSING = 3
    FABRICATION = 4
    ASSEMBLY = 5
    CHARGING = 6
    WAREHOUSE = 7
    PATH = 8
    SOLAR = 9


@dataclass
class MapCell:
    """地图栅格单元"""
    x: int  # 栅格 X 坐标
    y: int  # 栅格 Y 坐标
    occupancy: OccupancyStatus = OccupancyStatus.UNKNOWN
    semantic_label: Optional[ZoneType] = None
    last_updated: float = 0.0
    item_type: Optional[str] = None  # 如果有物品
    item_position: Optional[np.ndarray] = None  # 物品精确位置

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "x": self.x,
            "y": self.y,
            "occupancy": self.occupancy.name,
            "semantic_label": self.semantic_label.name if self.semantic_label else None,
            "last_updated": self.last_updated,
            "item_type": self.item_type,
            "item_position": self.item_position.tolist() if self.item_position is not None else None,
        }


@dataclass
class SemanticMap:
    """
    语义地图

    维护一个 2D 栅格地图，存储占据状态和语义信息。
    """

    resolution: float = 0.1  # 分辨率 (米/格)
    width: float = 50.0  # 地图宽度 (米)
    height: float = 50.0  # 地图高度 (米)
    origin: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0]))  # 原点坐标

    def __post_init__(self):
        """初始化后处理"""
        self.origin = np.asarray(self.origin, dtype=np.float32)
        # 计算栅格尺寸
        self.grid_width = int(self.width / self.resolution)
        self.grid_height = int(self.height / self.resolution)
        # 初始化栅格数据
        self._occupancy_grid = np.zeros(
            (self.grid_height, self.grid_width), dtype=np.uint8
        )
        self._semantic_grid = np.zeros(
            (self.grid_height, self.grid_width), dtype=np.uint8
        )
        self._update_time_grid = np.zeros(
            (self.grid_height, self.grid_width), dtype=np.float64
        )
        # 物品位置记录
        self._items: Dict[str, List[np.ndarray]] = {}  # item_type -> positions

    def world_to_grid(self, x: float, y: float) -> Tuple[int, int]:
        """
        世界坐标转栅格坐标

        Args:
            x: 世界 X 坐标
            y: 世界 Y 坐标

        Returns:
            (grid_x, grid_y) 栅格坐标
        """
        gx = int((x - self.origin[0]) / self.resolution)
        gy = int((y - self.origin[1]) / self.resolution)
        return gx, gy

    def grid_to_world(self, gx: int, gy: int) -> Tuple[float, float]:
        """
        栅格坐标转世界坐标

        Args:
            gx: 栅格 X 坐标
            gy: 栅格 Y 坐标

        Returns:
            (x, y) 世界坐标 (栅格中心)
        """
        x = self.origin[0] + (gx + 0.5) * self.resolution
        y = self.origin[1] + (gy + 0.5) * self.resolution
        return x, y

    def is_valid(self, gx: int, gy: int) -> bool:
        """检查栅格坐标是否有效"""
        return 0 <= gx < self.grid_width and 0 <= gy < self.grid_height

    def get_cell(self, x: float, y: float) -> Optional[MapCell]:
        """
        获取指定位置的栅格单元

        Args:
            x: 世界 X 坐标
            y: 世界 Y 坐标

        Returns:
            栅格单元，如果坐标无效返回 None
        """
        gx, gy = self.world_to_grid(x, y)
        if not self.is_valid(gx, gy):
            return None

        return MapCell(
            x=gx,
            y=gy,
            occupancy=OccupancyStatus(self._occupancy_grid[gy, gx]),
            semantic_label=ZoneType(self._semantic_grid[gy, gx]) if self._semantic_grid[gy, gx] > 0 else None,
            last_updated=self._update_time_grid[gy, gx],
        )

    def set_occupancy(
        self,
        x: float,
        y: float,
        status: OccupancyStatus,
        timestamp: float,
    ):
        """
        设置占据状态

        Args:
            x: 世界 X 坐标
            y: 世界 Y 坐标
            status: 占据状态
            timestamp: 时间戳
        """
        gx, gy = self.world_to_grid(x, y)
        if not self.is_valid(gx, gy):
            return

        self._occupancy_grid[gy, gx] = status.value
        self._update_time_grid[gy, gx] = timestamp

    def set_semantic(
        self,
        x: float,
        y: float,
        zone_type: ZoneType,
        timestamp: float,
    ):
        """
        设置语义标签

        Args:
            x: 世界 X 坐标
            y: 世界 Y 坐标
            zone_type: 区域类型
            timestamp: 时间戳
        """
        gx, gy = self.world_to_grid(x, y)
        if not self.is_valid(gx, gy):
            return

        self._semantic_grid[gy, gx] = zone_type.value
        self._update_time_grid[gy, gx] = timestamp

    def update_from_depth(
        self,
        depth_image: np.ndarray,
        intrinsics: "CameraIntrinsics",
        camera_pose: np.ndarray,
        timestamp: float,
        max_depth: float = 5.0,
    ):
        """
        从深度图更新地图

        Args:
            depth_image: 深度图 (H, W)
            intrinsics: 相机内参
            camera_pose: 相机位姿 (4x4)
            timestamp: 时间戳
            max_depth: 最大深度 (米)
        """
        h, w = depth_image.shape

        # 采样深度图
        step = max(1, int(self.resolution * 10))  # 采样步长
        for v in range(0, h, step):
            for u in range(0, w, step):
                z = depth_image[v, u]
                if z <= 0 or z > max_depth:
                    continue

                # 反投影到相机坐标系
                x = (u - intrinsics.cx) * z / intrinsics.fx
                y = (v - intrinsics.cy) * z / intrinsics.fy

                # 转换到世界坐标系
                point_camera = np.array([x, y, z, 1])
                point_world = camera_pose @ point_camera

                # 更新占据状态
                self.set_occupancy(
                    point_world[0], point_world[1],
                    OccupancyStatus.OCCUPIED, timestamp
                )

    def add_item(
        self,
        item_type: str,
        position: np.ndarray,
        timestamp: float,
    ):
        """
        添加物品记录

        Args:
            item_type: 物品类型
            position: 物品位置 [x, y, z]
            timestamp: 时间戳
        """
        if item_type not in self._items:
            self._items[item_type] = []

        # 检查是否已存在相近位置的物品
        for existing_pos in self._items[item_type]:
            if np.linalg.norm(existing_pos[:2] - position[:2]) < self.resolution:
                return  # 已存在

        self._items[item_type].append(position.copy())

        # 更新栅格
        self.set_occupancy(position[0], position[1], OccupancyStatus.OCCUPIED, timestamp)

    def remove_item(self, item_type: str, position: np.ndarray):
        """
        移除物品记录

        Args:
            item_type: 物品类型
            position: 物品位置
        """
        if item_type not in self._items:
            return

        # 查找并移除最近的物品
        positions = self._items[item_type]
        for i, pos in enumerate(positions):
            if np.linalg.norm(pos[:2] - position[:2]) < self.resolution:
                positions.pop(i)
                break

    def get_items(self, item_type: Optional[str] = None) -> Dict[str, List[np.ndarray]]:
        """
        获取物品位置

        Args:
            item_type: 物品类型，如果为 None 则返回所有物品

        Returns:
            物品位置字典
        """
        if item_type is not None:
            return {item_type: self._items.get(item_type, [])}
        return self._items.copy()

    def get_nearest_item(
        self,
        position: np.ndarray,
        item_type: str,
    ) -> Optional[np.ndarray]:
        """
        获取最近的物品位置

        Args:
            position: 当前位置 [x, y]
            item_type: 物品类型

        Returns:
            最近物品位置，如果没有则返回 None
        """
        if item_type not in self._items or len(self._items[item_type]) == 0:
            return None

        positions = self._items[item_type]
        distances = [np.linalg.norm(pos[:2] - position[:2]) for pos in positions]
        nearest_idx = np.argmin(distances)
        return positions[nearest_idx]

    def get_occupancy_grid(self) -> np.ndarray:
        """获取占据栅格"""
        return self._occupancy_grid.copy()

    def get_semantic_grid(self) -> np.ndarray:
        """获取语义栅格"""
        return self._semantic_grid.copy()

    def is_path_clear(
        self,
        start: np.ndarray,
        end: np.ndarray,
    ) -> bool:
        """
        检查路径是否畅通

        Args:
            start: 起点 [x, y]
            end: 终点 [x, y]

        Returns:
            路径是否畅通
        """
        # 使用 Bresenham 算法检查路径
        gx1, gy1 = self.world_to_grid(start[0], start[1])
        gx2, gy2 = self.world_to_grid(end[0], end[1])

        dx = abs(gx2 - gx1)
        dy = abs(gy2 - gy1)
        sx = 1 if gx1 < gx2 else -1
        sy = 1 if gy1 < gy2 else -1
        err = dx - dy

        while True:
            if not self.is_valid(gx1, gy1):
                return False

            if self._occupancy_grid[gy1, gx1] == OccupancyStatus.OCCUPIED.value:
                return False

            if self._occupancy_grid[gy1, gx1] == OccupancyStatus.OBSTACLE.value:
                return False

            if gx1 == gx2 and gy1 == gy2:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                gx1 += sx
            if e2 < dx:
                err += dx
                gy1 += sy

        return True

    def get_free_neighbors(self, gx: int, gy: int) -> List[Tuple[int, int]]:
        """
        获取空闲的相邻栅格

        Args:
            gx: 栅格 X 坐标
            gy: 栅格 Y 坐标

        Returns:
            相邻空闲栅格列表
        """
        neighbors = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                nx, ny = gx + dx, gy + dy
                if self.is_valid(nx, ny):
                    if self._occupancy_grid[ny, nx] == OccupancyStatus.FREE.value:
                        neighbors.append((nx, ny))
        return neighbors

    def visualize(self) -> np.ndarray:
        """
        生成可视化图像

        Returns:
            RGB 图像 (H, W, 3)
        """
        # 创建颜色映射
        color_map = {
            OccupancyStatus.UNKNOWN.value: [128, 128, 128],  # 灰色
            OccupancyStatus.FREE.value: [255, 255, 255],  # 白色
            OccupancyStatus.OCCUPIED.value: [0, 0, 0],  # 黑色
            OccupancyStatus.OBSTACLE.value: [255, 0, 0],  # 红色
        }

        # 创建 RGB 图像
        image = np.zeros((self.grid_height, self.grid_width, 3), dtype=np.uint8)

        for status_val, color in color_map.items():
            mask = self._occupancy_grid == status_val
            image[mask] = color

        return image

    def save(self, filepath: str):
        """保存地图到文件"""
        np.savez(
            filepath,
            occupancy=self._occupancy_grid,
            semantic=self._semantic_grid,
            update_time=self._update_time_grid,
            resolution=self.resolution,
            width=self.width,
            height=self.height,
            origin=self.origin,
        )

    @classmethod
    def load(cls, filepath: str) -> "SemanticMap":
        """从文件加载地图"""
        data = np.load(filepath)
        semantic_map = cls(
            resolution=float(data["resolution"]),
            width=float(data["width"]),
            height=float(data["height"]),
            origin=data["origin"],
        )
        semantic_map._occupancy_grid = data["occupancy"]
        semantic_map._semantic_grid = data["semantic"]
        semantic_map._update_time_grid = data["update_time"]
        return semantic_map
