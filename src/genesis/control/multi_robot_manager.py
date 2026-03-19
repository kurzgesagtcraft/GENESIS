"""
GENESIS Multi-Robot Manager Module

多机器人协作管理器，支持多机器人并行工作、任务分配和冲突避免。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Callable
import numpy as np
from collections import defaultdict
import time

from genesis.robot.robot_interface import GenesisBot, ArmSide
from genesis.utils.types import Pose2D
from genesis.utils.geometry import SE3


class RobotStatus(Enum):
    """机器人状态"""
    IDLE = "idle"                    # 空闲
    WORKING = "working"              # 工作中
    CHARGING = "charging"            # 充电中
    NAVIGATING = "navigating"        # 导航中
    WAITING = "waiting"              # 等待中
    ERROR = "error"                  # 错误
    OFFLINE = "offline"              # 离线


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0    # 关键任务 (如充电)
    HIGH = 1        # 高优先级
    NORMAL = 2      # 正常优先级
    LOW = 3         # 低优先级
    BACKGROUND = 4  # 后台任务


class ConflictType(Enum):
    """冲突类型"""
    POSITION = "position"        # 位置冲突
    RESOURCE = "resource"        # 资源冲突
    STATION = "station"          # 工站冲突
    PATH = "path"                # 路径冲突
    NONE = "none"                # 无冲突


@dataclass
class RobotInfo:
    """机器人信息"""
    robot_id: str
    robot: GenesisBot
    status: RobotStatus = RobotStatus.IDLE
    current_task_id: Optional[str] = None
    position: Pose2D = field(default_factory=lambda: Pose2D(0.0, 0.0, 0.0))
    battery_soc: float = 1.0
    carrying_items: List[str] = field(default_factory=list)
    assigned_zone: Optional[str] = None
    last_update_time: float = 0.0

    def is_available(self) -> bool:
        """检查机器人是否可用"""
        return (
            self.status in [RobotStatus.IDLE, RobotStatus.WAITING] and
            self.battery_soc > 0.15 and
            self.current_task_id is None
        )

    def needs_charging(self) -> bool:
        """检查是否需要充电"""
        return self.battery_soc < 0.20


@dataclass
class TaskAssignment:
    """任务分配"""
    task_id: str
    robot_id: str
    task_type: str
    target: str
    priority: TaskPriority
    start_time: float = 0.0
    estimated_duration: float = 0.0
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"


@dataclass
class Conflict:
    """冲突信息"""
    conflict_type: ConflictType
    robot_ids: List[str]
    location: Optional[Tuple[float, float]] = None
    resource_id: Optional[str] = None
    time_window: Optional[Tuple[float, float]] = None
    resolution: Optional[str] = None


@dataclass
class ZoneReservation:
    """区域预约"""
    zone_id: str
    robot_id: str
    start_time: float
    end_time: float
    priority: TaskPriority


class CommunicationProtocol:
    """
    机器人通信协议

    定义机器人之间的通信消息格式和处理逻辑。
    """

    def __init__(self):
        """初始化通信协议"""
        self._message_handlers: Dict[str, Callable] = {}
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._message_history: List[Dict] = []
        self._max_history = 1000

    def register_handler(self, message_type: str, handler: Callable):
        """
        注册消息处理器

        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        self._message_handlers[message_type] = handler

    async def send_message(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: str,
        content: Dict[str, Any],
    ) -> bool:
        """
        发送消息

        Args:
            sender_id: 发送者 ID
            receiver_id: 接收者 ID (可为 "broadcast")
            message_type: 消息类型
            content: 消息内容

        Returns:
            是否发送成功
        """
        message = {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message_type": message_type,
            "content": content,
            "timestamp": time.time(),
        }

        await self._message_queue.put(message)
        self._message_history.append(message)

        # 限制历史记录长度
        if len(self._message_history) > self._max_history:
            self._message_history = self._message_history[-self._max_history:]

        return True

    async def receive_message(self, robot_id: str) -> Optional[Dict]:
        """
        接收消息

        Args:
            robot_id: 接收者 ID

        Returns:
            消息字典，如果没有消息则返回 None
        """
        # 检查队列中的消息
        messages = []
        while not self._message_queue.empty():
            msg = await self._message_queue.get()
            messages.append(msg)

        # 查找发给该机器人的消息
        for msg in messages:
            if msg["receiver_id"] == robot_id or msg["receiver_id"] == "broadcast":
                # 处理消息
                if msg["message_type"] in self._message_handlers:
                    await self._message_handlers[msg["message_type"]](msg)
                return msg

        # 将其他消息放回队列
        for msg in messages:
            if msg["receiver_id"] != robot_id:
                await self._message_queue.put(msg)

        return None

    def get_broadcast_messages(self, since_time: float = 0.0) -> List[Dict]:
        """
        获取广播消息

        Args:
            since_time: 起始时间

        Returns:
            消息列表
        """
        return [
            msg for msg in self._message_history
            if msg["receiver_id"] == "broadcast" and msg["timestamp"] > since_time
        ]


class TaskAllocator:
    """
    任务分配器

    负责将任务分配给最合适的机器人。
    """

    def __init__(self):
        """初始化任务分配器"""
        self._pending_tasks: List[TaskAssignment] = []
        self._active_tasks: Dict[str, TaskAssignment] = {}
        self._completed_tasks: List[TaskAssignment] = []
        self._task_counter = 0

    def add_task(
        self,
        task_type: str,
        target: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        estimated_duration: float = 60.0,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        """
        添加任务

        Args:
            task_type: 任务类型
            target: 目标
            priority: 优先级
            estimated_duration: 预估时长
            dependencies: 依赖任务 ID 列表

        Returns:
            任务 ID
        """
        self._task_counter += 1
        task_id = f"task_{self._task_counter:04d}"

        task = TaskAssignment(
            task_id=task_id,
            robot_id="",
            task_type=task_type,
            target=target,
            priority=priority,
            estimated_duration=estimated_duration,
            dependencies=dependencies or [],
        )

        self._pending_tasks.append(task)
        return task_id

    def allocate(
        self,
        robots: Dict[str, RobotInfo],
        zone_reservations: List[ZoneReservation],
    ) -> List[Tuple[str, str]]:
        """
        分配任务给机器人

        Args:
            robots: 机器人信息字典
            zone_reservations: 区域预约列表

        Returns:
            (task_id, robot_id) 分配结果列表
        """
        allocations = []

        # 按优先级排序待分配任务
        self._pending_tasks.sort(key=lambda t: t.priority.value)

        # 获取可用机器人
        available_robots = [
            (rid, info) for rid, info in robots.items()
            if info.is_available()
        ]

        for task in self._pending_tasks[:]:
            if not available_robots:
                break

            # 检查依赖是否满足
            if not self._check_dependencies(task):
                continue

            # 选择最佳机器人
            best_robot_id = self._select_best_robot(
                task, available_robots, zone_reservations
            )

            if best_robot_id:
                # 分配任务
                task.robot_id = best_robot_id
                task.start_time = time.time()
                task.status = "assigned"

                self._active_tasks[task.task_id] = task
                self._pending_tasks.remove(task)
                allocations.append((task.task_id, best_robot_id))

                # 更新可用机器人列表
                available_robots = [
                    (rid, info) for rid, info in available_robots
                    if rid != best_robot_id
                ]

        return allocations

    def _check_dependencies(self, task: TaskAssignment) -> bool:
        """检查任务依赖是否满足"""
        for dep_id in task.dependencies:
            if dep_id in self._active_tasks:
                return False
            if dep_id not in [t.task_id for t in self._completed_tasks]:
                return False
        return True

    def _select_best_robot(
        self,
        task: TaskAssignment,
        available_robots: List[Tuple[str, RobotInfo]],
        zone_reservations: List[ZoneReservation],
    ) -> Optional[str]:
        """
        选择最佳机器人执行任务

        考虑因素:
        1. 距离目标的距离
        2. 电池电量
        3. 当前负载
        4. 区域冲突
        """
        if not available_robots:
            return None

        best_robot_id = None
        best_score = float('inf')

        for robot_id, info in available_robots:
            # 计算距离 (简化：使用欧几里得距离)
            # 实际应使用路径规划计算
            distance = 0.0  # 需要根据任务目标计算

            # 计算得分 (越低越好)
            score = (
                distance * 0.4 +                          # 距离权重
                (1.0 - info.battery_soc) * 100 * 0.3 +    # 电量权重
                len(info.carrying_items) * 10 * 0.2 +     # 负载权重
                task.priority.value * 10 * 0.1            # 优先级权重
            )

            # 检查区域冲突
            if self._has_zone_conflict(robot_id, task.target, zone_reservations):
                score += 1000  # 大幅降低得分

            if score < best_score:
                best_score = score
                best_robot_id = robot_id

        return best_robot_id

    def _has_zone_conflict(
        self,
        robot_id: str,
        target_zone: str,
        reservations: List[ZoneReservation],
    ) -> bool:
        """检查区域冲突"""
        current_time = time.time()
        for res in reservations:
            if res.zone_id == target_zone and res.robot_id != robot_id:
                if res.start_time <= current_time <= res.end_time:
                    return True
        return False

    def complete_task(self, task_id: str) -> bool:
        """
        完成任务

        Args:
            task_id: 任务 ID

        Returns:
            是否成功
        """
        if task_id in self._active_tasks:
            task = self._active_tasks.pop(task_id)
            task.status = "completed"
            self._completed_tasks.append(task)
            return True
        return False

    def fail_task(self, task_id: str, reason: str = "") -> bool:
        """
        标记任务失败

        Args:
            task_id: 任务 ID
            reason: 失败原因

        Returns:
            是否成功
        """
        if task_id in self._active_tasks:
            task = self._active_tasks.pop(task_id)
            task.status = "failed"
            # 可以选择重新加入待分配队列
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        """获取任务分配器状态"""
        return {
            "pending_count": len(self._pending_tasks),
            "active_count": len(self._active_tasks),
            "completed_count": len(self._completed_tasks),
            "pending_tasks": [
                {"id": t.task_id, "type": t.task_type, "target": t.target}
                for t in self._pending_tasks[:5]  # 只返回前5个
            ],
            "active_tasks": [
                {"id": t.task_id, "robot": t.robot_id, "type": t.task_type}
                for t in self._active_tasks.values()
            ],
        }


class ConflictResolver:
    """
    冲突解决器

    检测和解决机器人之间的冲突。
    """

    def __init__(self, min_separation: float = 1.0):
        """
        初始化冲突解决器

        Args:
            min_separation: 最小安全距离 (m)
        """
        self.min_separation = min_separation
        self._detected_conflicts: List[Conflict] = []

    def detect_conflicts(
        self,
        robots: Dict[str, RobotInfo],
        zone_reservations: List[ZoneReservation],
    ) -> List[Conflict]:
        """
        检测冲突

        Args:
            robots: 机器人信息字典
            zone_reservations: 区域预约列表

        Returns:
            冲突列表
        """
        conflicts = []
        robot_list = list(robots.values())

        # 检测位置冲突
        for i, info1 in enumerate(robot_list):
            for info2 in robot_list[i + 1:]:
                dist = np.sqrt(
                    (info1.position.x - info2.position.x) ** 2 +
                    (info1.position.y - info2.position.y) ** 2
                )
                if dist < self.min_separation:
                    conflicts.append(Conflict(
                        conflict_type=ConflictType.POSITION,
                        robot_ids=[info1.robot_id, info2.robot_id],
                        location=(
                            (info1.position.x + info2.position.x) / 2,
                            (info1.position.y + info2.position.y) / 2,
                        ),
                    ))

        # 检测区域预约冲突
        current_time = time.time()
        for i, res1 in enumerate(zone_reservations):
            for res2 in zone_reservations[i + 1:]:
                if (res1.zone_id == res2.zone_id and
                    res1.robot_id != res2.robot_id):
                    # 检查时间窗口是否重叠
                    if (res1.start_time <= res2.end_time and
                        res2.start_time <= res1.end_time):
                        conflicts.append(Conflict(
                            conflict_type=ConflictType.RESOURCE,
                            robot_ids=[res1.robot_id, res2.robot_id],
                            resource_id=res1.zone_id,
                            time_window=(
                                max(res1.start_time, res2.start_time),
                                min(res1.end_time, res2.end_time),
                            ),
                        ))

        self._detected_conflicts = conflicts
        return conflicts

    def resolve(self, conflict: Conflict) -> str:
        """
        解决冲突

        Args:
            conflict: 冲突信息

        Returns:
            解决方案描述
        """
        if conflict.conflict_type == ConflictType.POSITION:
            return self._resolve_position_conflict(conflict)
        elif conflict.conflict_type == ConflictType.RESOURCE:
            return self._resolve_resource_conflict(conflict)
        elif conflict.conflict_type == ConflictType.PATH:
            return self._resolve_path_conflict(conflict)
        else:
            return "unknown_conflict"

    def _resolve_position_conflict(self, conflict: Conflict) -> str:
        """解决位置冲突"""
        # 简单策略：让优先级高的机器人先通过
        # 实际应考虑更多因素
        return f"robots_{conflict.robot_ids[0]}_wait_for_{conflict.robot_ids[1]}"

    def _resolve_resource_conflict(self, conflict: Conflict) -> str:
        """解决资源冲突"""
        # 简单策略：先到先得
        return f"robot_{conflict.robot_ids[0]}_has_priority"

    def _resolve_path_conflict(self, conflict: Conflict) -> str:
        """解决路径冲突"""
        # 简单策略：一个机器人等待
        return f"robot_{conflict.robot_ids[0]}_yields_path"

    def get_conflict_summary(self) -> Dict[str, int]:
        """获取冲突统计"""
        summary = defaultdict(int)
        for conflict in self._detected_conflicts:
            summary[conflict.conflict_type.value] += 1
        return dict(summary)


class MultiRobotManager:
    """
    多机器人管理器

    管理多个机器人的协作，包括任务分配、冲突避免和通信。
    """

    def __init__(
        self,
        min_separation: float = 1.0,
        enable_communication: bool = True,
    ):
        """
        初始化多机器人管理器

        Args:
            min_separation: 最小安全距离 (m)
            enable_communication: 是否启用通信
        """
        self._robots: Dict[str, RobotInfo] = {}
        self._task_allocator = TaskAllocator()
        self._conflict_resolver = ConflictResolver(min_separation)
        self._communication = CommunicationProtocol() if enable_communication else None
        self._zone_reservations: List[ZoneReservation] = []
        self._current_time = 0.0
        self._is_running = False

    def register_robot(self, robot: GenesisBot, zone: Optional[str] = None) -> str:
        """
        注册机器人

        Args:
            robot: 机器人实例
            zone: 分配的区域

        Returns:
            机器人 ID
        """
        robot_id = robot.name
        pose = robot.get_base_pose()

        info = RobotInfo(
            robot_id=robot_id,
            robot=robot,
            position=Pose2D(pose[0], pose[1], pose[2]),
            battery_soc=robot.get_battery_soc(),
            assigned_zone=zone,
        )

        self._robots[robot_id] = info
        return robot_id

    def unregister_robot(self, robot_id: str) -> bool:
        """
        注销机器人

        Args:
            robot_id: 机器人 ID

        Returns:
            是否成功
        """
        if robot_id in self._robots:
            del self._robots[robot_id]
            return True
        return False

    def add_task(
        self,
        task_type: str,
        target: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        estimated_duration: float = 60.0,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        """
        添加任务

        Args:
            task_type: 任务类型
            target: 目标
            priority: 优先级
            estimated_duration: 预估时长
            dependencies: 依赖任务 ID 列表

        Returns:
            任务 ID
        """
        return self._task_allocator.add_task(
            task_type, target, priority, estimated_duration, dependencies
        )

    def reserve_zone(
        self,
        zone_id: str,
        robot_id: str,
        duration: float,
        priority: TaskPriority = TaskPriority.NORMAL,
    ) -> bool:
        """
        预约区域

        Args:
            zone_id: 区域 ID
            robot_id: 机器人 ID
            duration: 持续时间 (s)
            priority: 优先级

        Returns:
            是否成功
        """
        # 检查是否已有预约
        for res in self._zone_reservations:
            if res.zone_id == zone_id and res.robot_id != robot_id:
                if self._current_time < res.end_time:
                    # 区域已被预约
                    return False

        reservation = ZoneReservation(
            zone_id=zone_id,
            robot_id=robot_id,
            start_time=self._current_time,
            end_time=self._current_time + duration,
            priority=priority,
        )

        self._zone_reservations.append(reservation)
        return True

    def release_zone(self, zone_id: str, robot_id: str) -> bool:
        """
        释放区域预约

        Args:
            zone_id: 区域 ID
            robot_id: 机器人 ID

        Returns:
            是否成功
        """
        for i, res in enumerate(self._zone_reservations):
            if res.zone_id == zone_id and res.robot_id == robot_id:
                self._zone_reservations.pop(i)
                return True
        return False

    def update(self, dt: float):
        """
        更新管理器状态

        Args:
            dt: 时间步长 (s)
        """
        self._current_time += dt

        # 更新机器人状态
        for robot_id, info in self._robots.items():
            robot = info.robot
            pose = robot.get_base_pose()
            info.position = Pose2D(pose[0], pose[1], pose[2])
            info.battery_soc = robot.get_battery_soc()
            info.last_update_time = self._current_time

            # 更新机器人状态
            if info.needs_charging() and info.status != RobotStatus.CHARGING:
                info.status = RobotStatus.CHARGING
            elif info.current_task_id:
                info.status = RobotStatus.WORKING
            elif robot.base.is_moving:
                info.status = RobotStatus.NAVIGATING
            else:
                info.status = RobotStatus.IDLE

        # 检测冲突
        conflicts = self._conflict_resolver.detect_conflicts(
            self._robots, self._zone_reservations
        )

        # 解决冲突
        for conflict in conflicts:
            resolution = self._conflict_resolver.resolve(conflict)
            # 应用解决方案 (简化)
            # 实际应发送指令给机器人

        # 分配任务
        allocations = self._task_allocator.allocate(
            self._robots, self._zone_reservations
        )

        for task_id, robot_id in allocations:
            self._robots[robot_id].current_task_id = task_id
            self._robots[robot_id].status = RobotStatus.WORKING

        # 清理过期的区域预约
        self._zone_reservations = [
            res for res in self._zone_reservations
            if res.end_time > self._current_time
        ]

    def get_robot_status(self, robot_id: str) -> Optional[Dict[str, Any]]:
        """
        获取机器人状态

        Args:
            robot_id: 机器人 ID

        Returns:
            状态字典
        """
        if robot_id not in self._robots:
            return None

        info = self._robots[robot_id]
        return {
            "robot_id": robot_id,
            "status": info.status.value,
            "position": (info.position.x, info.position.y, info.position.yaw),
            "battery_soc": info.battery_soc,
            "current_task": info.current_task_id,
            "carrying_items": info.carrying_items,
            "assigned_zone": info.assigned_zone,
        }

    def get_all_status(self) -> Dict[str, Any]:
        """
        获取所有机器人状态

        Returns:
            状态字典
        """
        return {
            "robots": {
                rid: self.get_robot_status(rid)
                for rid in self._robots
            },
            "tasks": self._task_allocator.get_status(),
            "conflicts": self._conflict_resolver.get_conflict_summary(),
            "zone_reservations": len(self._zone_reservations),
            "current_time": self._current_time,
        }

    def get_available_robots(self) -> List[str]:
        """获取可用机器人列表"""
        return [
            rid for rid, info in self._robots.items()
            if info.is_available()
        ]

    def get_robots_by_status(self, status: RobotStatus) -> List[str]:
        """
        按状态获取机器人

        Args:
            status: 机器人状态

        Returns:
            机器人 ID 列表
        """
        return [
            rid for rid, info in self._robots.items()
            if info.status == status
        ]

    async def broadcast_message(
        self,
        sender_id: str,
        message_type: str,
        content: Dict[str, Any],
    ) -> bool:
        """
        广播消息

        Args:
            sender_id: 发送者 ID
            message_type: 消息类型
            content: 消息内容

        Returns:
            是否成功
        """
        if self._communication is None:
            return False

        return await self._communication.send_message(
            sender_id, "broadcast", message_type, content
        )

    async def send_direct_message(
        self,
        sender_id: str,
        receiver_id: str,
        message_type: str,
        content: Dict[str, Any],
    ) -> bool:
        """
        发送直接消息

        Args:
            sender_id: 发送者 ID
            receiver_id: 接收者 ID
            message_type: 消息类型
            content: 消息内容

        Returns:
            是否成功
        """
        if self._communication is None:
            return False

        return await self._communication.send_message(
            sender_id, receiver_id, message_type, content
        )

    def get_summary(self) -> Dict[str, Any]:
        """
        获取管理器摘要

        Returns:
            摘要字典
        """
        status_counts = defaultdict(int)
        for info in self._robots.values():
            status_counts[info.status.value] += 1

        return {
            "total_robots": len(self._robots),
            "available_robots": len(self.get_available_robots()),
            "status_distribution": dict(status_counts),
            "pending_tasks": self._task_allocator._pending_tasks.__len__(),
            "active_tasks": len(self._task_allocator._active_tasks),
            "detected_conflicts": len(self._conflict_resolver._detected_conflicts),
            "zone_reservations": len(self._zone_reservations),
        }


class CooperativeTaskPlanner:
    """
    协作任务规划器

    为多机器人系统规划协作任务。
    """

    def __init__(self, manager: MultiRobotManager):
        """
        初始化协作任务规划器

        Args:
            manager: 多机器人管理器
        """
        self._manager = manager

    def plan_parallel_mining(
        self,
        ore_type: str,
        quantity: int,
        mine_zones: List[str],
    ) -> List[str]:
        """
        规划并行采矿任务

        Args:
            ore_type: 矿石类型
            quantity: 总数量
            mine_zones: 矿区列表

        Returns:
            任务 ID 列表
        """
        task_ids = []
        available_robots = self._manager.get_available_robots()

        if not available_robots:
            return task_ids

        # 计算每个机器人的任务量
        per_robot = quantity // len(available_robots)
        remainder = quantity % len(available_robots)

        for i, robot_id in enumerate(available_robots):
            robot_quantity = per_robot + (1 if i < remainder else 0)
            if robot_quantity == 0:
                continue

            # 分配矿区
            zone = mine_zones[i % len(mine_zones)]

            task_id = self._manager.add_task(
                task_type="mine",
                target=f"{zone}:{ore_type}",
                priority=TaskPriority.NORMAL,
                estimated_duration=robot_quantity * 30.0,  # 假设每个30秒
            )
            task_ids.append(task_id)

        return task_ids

    def plan_parallel_transport(
        self,
        items: List[Tuple[str, str]],  # (item_type, destination)
    ) -> List[str]:
        """
        规划并行运输任务

        Args:
            items: 物品列表 [(物品类型, 目的地)]

        Returns:
            任务 ID 列表
        """
        task_ids = []
        available_robots = self._manager.get_available_robots()

        if not available_robots:
            return task_ids

        # 分配运输任务
        for i, (item_type, destination) in enumerate(items):
            robot_id = available_robots[i % len(available_robots)]

            task_id = self._manager.add_task(
                task_type="transport",
                target=f"{item_type}:{destination}",
                priority=TaskPriority.NORMAL,
                estimated_duration=60.0,
            )
            task_ids.append(task_id)

        return task_ids

    def plan_coordinated_assembly(
        self,
        recipe_name: str,
        station_id: str,
    ) -> List[str]:
        """
        规划协调装配任务

        Args:
            recipe_name: 配方名称
            station_id: 工站 ID

        Returns:
            任务 ID 列表
        """
        task_ids = []

        # 装配任务通常需要多个机器人协作
        # 简化：创建一系列依赖任务

        # 任务 1: 准备零件
        prep_task_id = self._manager.add_task(
            task_type="prepare_parts",
            target=recipe_name,
            priority=TaskPriority.HIGH,
            estimated_duration=120.0,
        )
        task_ids.append(prep_task_id)

        # 任务 2: 装配 (依赖任务 1)
        assembly_task_id = self._manager.add_task(
            task_type="assemble",
            target=f"{station_id}:{recipe_name}",
            priority=TaskPriority.HIGH,
            estimated_duration=180.0,
            dependencies=[prep_task_id],
        )
        task_ids.append(assembly_task_id)

        # 任务 3: 质量检查 (依赖任务 2)
        qc_task_id = self._manager.add_task(
            task_type="quality_check",
            target=recipe_name,
            priority=TaskPriority.NORMAL,
            estimated_duration=30.0,
            dependencies=[assembly_task_id],
        )
        task_ids.append(qc_task_id)

        return task_ids

    def optimize_task_distribution(self) -> Dict[str, List[str]]:
        """
        优化任务分配

        Returns:
            机器人 ID 到任务 ID 列表的映射
        """
        distribution = defaultdict(list)

        # 获取所有待分配任务
        pending = self._manager._task_allocator._pending_tasks
        available_robots = self._manager.get_available_robots()

        if not available_robots:
            return dict(distribution)

        # 按优先级排序
        pending.sort(key=lambda t: t.priority.value)

        # 简单轮询分配
        for i, task in enumerate(pending):
            robot_id = available_robots[i % len(available_robots)]
            distribution[robot_id].append(task.task_id)

        return dict(distribution)
