"""
GENESIS Self-Repair Module

自我修复机制，检测零件磨损并协调修复过程。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import time
from collections import defaultdict


class ComponentType(Enum):
    """组件类型"""
    JOINT = "joint"                 # 关节
    MOTOR = "motor"                 # 电机
    GEARBOX = "gearbox"             # 减速器
    BEARING = "bearing"             # 轴承
    GRIPPER = "gripper"             # 夹爪
    SENSOR = "sensor"               # 传感器
    BATTERY = "battery"             # 电池
    CONTROLLER = "controller"       # 控制器
    WHEEL = "wheel"                 # 轮子
    ARM_SEGMENT = "arm_segment"     # 手臂段


class HealthStatus(Enum):
    """健康状态"""
    EXCELLENT = "excellent"   # 优秀 (>95%)
    GOOD = "good"             # 良好 (80-95%)
    FAIR = "fair"             # 一般 (60-80%)
    POOR = "poor"             # 较差 (40-60%)
    CRITICAL = "critical"     # 临界 (20-40%)
    FAILED = "failed"         # 失效 (<20%)


class RepairPriority(Enum):
    """修复优先级"""
    EMERGENCY = 0   # 紧急 (立即修复)
    HIGH = 1        # 高优先级
    NORMAL = 2      # 正常优先级
    LOW = 3         # 低优先级
    SCHEDULED = 4   # 计划维护


class RepairStatus(Enum):
    """修复状态"""
    PENDING = "pending"
    DIAGNOSING = "diagnosing"
    PARTS_ORDERED = "parts_ordered"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ComponentHealth:
    """组件健康状态"""
    component_id: str
    component_type: ComponentType
    health_percentage: float = 100.0
    total_operations: int = 0
    total_runtime_hours: float = 0.0
    last_maintenance_time: float = 0.0
    predicted_failure_time: Optional[float] = None
    wear_indicators: Dict[str, float] = field(default_factory=dict)


@dataclass
class RepairTask:
    """修复任务"""
    task_id: str
    component_id: str
    component_type: ComponentType
    priority: RepairPriority
    status: RepairStatus
    required_parts: List[str]
    estimated_duration_hours: float
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    assigned_robot: Optional[str] = None
    notes: List[str] = field(default_factory=list)


@dataclass
class MaintenanceRecord:
    """维护记录"""
    component_id: str
    maintenance_type: str
    timestamp: float
    duration_hours: float
    parts_replaced: List[str]
    health_before: float
    health_after: float
    technician: Optional[str] = None
    notes: str = ""


class HealthMonitor:
    """
    健康监控器

    监控机器人各组件的健康状态。
    """

    def __init__(self):
        """初始化健康监控器"""
        self._components: Dict[str, ComponentHealth] = {}
        self._health_history: Dict[str, List[float]] = defaultdict(list)
        self._alert_thresholds = {
            HealthStatus.EXCELLENT: 95.0,
            HealthStatus.GOOD: 80.0,
            HealthStatus.FAIR: 60.0,
            HealthStatus.POOR: 40.0,
            HealthStatus.CRITICAL: 20.0,
        }

    def register_component(
        self,
        component_id: str,
        component_type: ComponentType,
        initial_health: float = 100.0,
    ):
        """
        注册组件

        Args:
            component_id: 组件 ID
            component_type: 组件类型
            initial_health: 初始健康度
        """
        self._components[component_id] = ComponentHealth(
            component_id=component_id,
            component_type=component_type,
            health_percentage=initial_health,
            last_maintenance_time=time.time(),
        )

    def update_health(
        self,
        component_id: str,
        health_delta: float,
        operation_count: int = 1,
        runtime_hours: float = 0.0,
    ):
        """
        更新组件健康状态

        Args:
            component_id: 组件 ID
            health_delta: 健康度变化 (负值表示磨损)
            operation_count: 操作次数
            runtime_hours: 运行时间
        """
        if component_id not in self._components:
            return

        component = self._components[component_id]
        component.health_percentage = max(0, min(100, component.health_percentage + health_delta))
        component.total_operations += operation_count
        component.total_runtime_hours += runtime_hours

        # 记录历史
        self._health_history[component_id].append(component.health_percentage)

        # 限制历史记录长度
        if len(self._health_history[component_id]) > 1000:
            self._health_history[component_id] = self._health_history[component_id][-1000:]

    def get_health_status(self, component_id: str) -> HealthStatus:
        """
        获取健康状态

        Args:
            component_id: 组件 ID

        Returns:
            健康状态
        """
        if component_id not in self._components:
            return HealthStatus.FAILED

        health = self._components[component_id].health_percentage

        if health >= self._alert_thresholds[HealthStatus.EXCELLENT]:
            return HealthStatus.EXCELLENT
        elif health >= self._alert_thresholds[HealthStatus.GOOD]:
            return HealthStatus.GOOD
        elif health >= self._alert_thresholds[HealthStatus.FAIR]:
            return HealthStatus.FAIR
        elif health >= self._alert_thresholds[HealthStatus.POOR]:
            return HealthStatus.POOR
        elif health >= self._alert_thresholds[HealthStatus.CRITICAL]:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.FAILED

    def predict_failure(self, component_id: str) -> Optional[float]:
        """
        预测失效时间

        Args:
            component_id: 组件 ID

        Returns:
            预测失效时间 (小时)，如果无法预测则返回 None
        """
        if component_id not in self._components:
            return None

        history = self._health_history.get(component_id, [])
        if len(history) < 10:
            return None

        # 简单线性预测
        recent_history = history[-10:]
        degradation_rate = (recent_history[0] - recent_history[-1]) / len(recent_history)

        if degradation_rate <= 0:
            return None

        current_health = self._components[component_id].health_percentage
        hours_to_failure = current_health / degradation_rate

        return hours_to_failure

    def get_components_needing_repair(self) -> List[Tuple[str, RepairPriority]]:
        """
        获取需要修复的组件

        Returns:
            (组件 ID, 优先级) 列表
        """
        needs_repair = []

        for component_id, component in self._components.items():
            status = self.get_health_status(component_id)

            if status == HealthStatus.FAILED:
                needs_repair.append((component_id, RepairPriority.EMERGENCY))
            elif status == HealthStatus.CRITICAL:
                needs_repair.append((component_id, RepairPriority.HIGH))
            elif status == HealthStatus.POOR:
                needs_repair.append((component_id, RepairPriority.NORMAL))
            elif status == HealthStatus.FAIR:
                needs_repair.append((component_id, RepairPriority.LOW))

        # 按优先级排序
        needs_repair.sort(key=lambda x: x[1].value)

        return needs_repair

    def get_status(self) -> Dict[str, Any]:
        """获取监控器状态"""
        status_counts = defaultdict(int)
        for component_id in self._components:
            status = self.get_health_status(component_id)
            status_counts[status.value] += 1

        return {
            "total_components": len(self._components),
            "status_distribution": dict(status_counts),
            "components_needing_repair": len(self.get_components_needing_repair()),
        }


class RepairCoordinator:
    """
    修复协调器

    协调自我修复过程。
    """

    def __init__(self, health_monitor: HealthMonitor):
        """
        初始化修复协调器

        Args:
            health_monitor: 健康监控器
        """
        self._health_monitor = health_monitor
        self._repair_queue: List[RepairTask] = []
        self._active_repairs: Dict[str, RepairTask] = {}
        self._completed_repairs: List[RepairTask] = []
        self._maintenance_records: List[MaintenanceRecord] = []
        self._task_counter = 0

    def create_repair_task(
        self,
        component_id: str,
        priority: RepairPriority,
    ) -> Optional[RepairTask]:
        """
        创建修复任务

        Args:
            component_id: 组件 ID
            priority: 优先级

        Returns:
            修复任务
        """
        if component_id not in self._health_monitor._components:
            return None

        component = self._health_monitor._components[component_id]

        self._task_counter += 1
        task = RepairTask(
            task_id=f"repair_{self._task_counter:04d}",
            component_id=component_id,
            component_type=component.component_type,
            priority=priority,
            status=RepairStatus.PENDING,
            required_parts=self._determine_required_parts(component),
            estimated_duration_hours=self._estimate_repair_duration(component),
        )

        self._repair_queue.append(task)
        self._repair_queue.sort(key=lambda t: t.priority.value)

        return task

    def _determine_required_parts(self, component: ComponentHealth) -> List[str]:
        """确定所需零件"""
        parts_map = {
            ComponentType.JOINT: ["joint_assembly", "bearings", "seals"],
            ComponentType.MOTOR: ["motor_unit", "encoder", "cables"],
            ComponentType.GEARBOX: ["gears", "bearings", "lubricant"],
            ComponentType.BEARING: ["bearing_set"],
            ComponentType.GRIPPER: ["gripper_fingers", "actuator", "sensors"],
            ComponentType.SENSOR: ["sensor_unit", "cables"],
            ComponentType.BATTERY: ["battery_pack", "bms"],
            ComponentType.CONTROLLER: ["controller_board", "firmware"],
            ComponentType.WHEEL: ["wheel_unit", "tire", "bearings"],
            ComponentType.ARM_SEGMENT: ["arm_segment", "fasteners"],
        }

        return parts_map.get(component.component_type, ["generic_parts"])

    def _estimate_repair_duration(self, component: ComponentHealth) -> float:
        """估算修复时长"""
        base_duration = {
            ComponentType.JOINT: 2.0,
            ComponentType.MOTOR: 3.0,
            ComponentType.GEARBOX: 4.0,
            ComponentType.BEARING: 1.0,
            ComponentType.GRIPPER: 1.5,
            ComponentType.SENSOR: 0.5,
            ComponentType.BATTERY: 1.0,
            ComponentType.CONTROLLER: 2.0,
            ComponentType.WHEEL: 0.5,
            ComponentType.ARM_SEGMENT: 3.0,
        }

        duration = base_duration.get(component.component_type, 1.0)

        # 根据健康度调整
        if component.health_percentage < 20:
            duration *= 1.5  # 更严重的损坏需要更长时间

        return duration

    def assign_repair(self, task_id: str, robot_id: str) -> bool:
        """
        分配修复任务

        Args:
            task_id: 任务 ID
            robot_id: 机器人 ID

        Returns:
            是否成功
        """
        for task in self._repair_queue:
            if task.task_id == task_id:
                task.assigned_robot = robot_id
                task.status = RepairStatus.IN_PROGRESS
                task.start_time = time.time()
                self._active_repairs[task_id] = task
                self._repair_queue.remove(task)
                return True
        return False

    def complete_repair(
        self,
        task_id: str,
        health_restored: float = 100.0,
        notes: str = "",
    ) -> bool:
        """
        完成修复

        Args:
            task_id: 任务 ID
            health_restored: 恢复的健康度
            notes: 备注

        Returns:
            是否成功
        """
        if task_id not in self._active_repairs:
            return False

        task = self._active_repairs.pop(task_id)
        task.status = RepairStatus.COMPLETED
        task.end_time = time.time()
        task.notes.append(notes)

        # 更新组件健康度
        component = self._health_monitor._components.get(task.component_id)
        if component:
            health_before = component.health_percentage
            component.health_percentage = health_restored
            component.last_maintenance_time = time.time()

            # 记录维护
            record = MaintenanceRecord(
                component_id=task.component_id,
                maintenance_type="repair",
                timestamp=time.time(),
                duration_hours=(task.end_time - task.start_time) / 3600,
                parts_replaced=task.required_parts,
                health_before=health_before,
                health_after=health_restored,
                notes=notes,
            )
            self._maintenance_records.append(record)

        self._completed_repairs.append(task)
        return True

    def get_repair_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取修复状态"""
        # 检查活动修复
        if task_id in self._active_repairs:
            task = self._active_repairs[task_id]
            return {
                "task_id": task_id,
                "status": task.status.value,
                "component_id": task.component_id,
                "assigned_robot": task.assigned_robot,
                "elapsed_time": time.time() - task.start_time if task.start_time else 0,
            }

        # 检查队列
        for task in self._repair_queue:
            if task.task_id == task_id:
                return {
                    "task_id": task_id,
                    "status": task.status.value,
                    "component_id": task.component_id,
                    "queue_position": self._repair_queue.index(task),
                }

        return None

    def get_status(self) -> Dict[str, Any]:
        """获取协调器状态"""
        return {
            "pending_repairs": len(self._repair_queue),
            "active_repairs": len(self._active_repairs),
            "completed_repairs": len(self._completed_repairs),
            "maintenance_records": len(self._maintenance_records),
            "queue_summary": [
                {
                    "task_id": t.task_id,
                    "component_id": t.component_id,
                    "priority": t.priority.value,
                }
                for t in self._repair_queue[:5]
            ],
        }


class SelfRepairSystem:
    """
    自我修复系统

    整合健康监控和修复协调。
    """

    def __init__(self):
        """初始化自我修复系统"""
        self.health_monitor = HealthMonitor()
        self.repair_coordinator = RepairCoordinator(self.health_monitor)

        # 自动检测配置
        self._auto_detect_enabled = True
        self._detection_interval = 60.0  # 检测间隔 (秒)
        self._last_detection_time = 0.0

        # 预防性维护配置
        self._preventive_maintenance_threshold = 70.0  # 触发预防性维护的健康度阈值

    def register_component(
        self,
        component_id: str,
        component_type: ComponentType,
        initial_health: float = 100.0,
    ):
        """注册组件"""
        self.health_monitor.register_component(
            component_id, component_type, initial_health
        )

    def update(self, dt: float, operation_counts: Dict[str, int] = None):
        """
        更新系统状态

        Args:
            dt: 时间步长 (s)
            operation_counts: 各组件操作次数
        """
        current_time = time.time()

        # 自动检测
        if self._auto_detect_enabled:
            if current_time - self._last_detection_time > self._detection_interval:
                self._perform_detection()
                self._last_detection_time = current_time

        # 更新组件健康度
        if operation_counts:
            for component_id, count in operation_counts.items():
                # 简化：每次操作减少0.01%健康度
                self.health_monitor.update_health(
                    component_id,
                    health_delta=-0.01 * count,
                    operation_count=count,
                    runtime_hours=dt / 3600,
                )

    def _perform_detection(self):
        """执行检测"""
        needs_repair = self.health_monitor.get_components_needing_repair()

        for component_id, priority in needs_repair:
            # 检查是否已有修复任务
            existing_task = None
            for task in self.repair_coordinator._repair_queue:
                if task.component_id == component_id:
                    existing_task = task
                    break

            if existing_task is None and component_id not in self.repair_coordinator._active_repairs:
                # 创建新的修复任务
                self.repair_coordinator.create_repair_task(component_id, priority)

    def check_preventive_maintenance(self) -> List[str]:
        """
        检查预防性维护

        Returns:
            需要预防性维护的组件列表
        """
        preventive_needed = []

        for component_id, component in self.health_monitor._components.items():
            if component.health_percentage < self._preventive_maintenance_threshold:
                if component.health_percentage >= 40:  # 不包括已经需要紧急修复的
                    preventive_needed.append(component_id)

        return preventive_needed

    def schedule_preventive_maintenance(self, component_id: str) -> Optional[RepairTask]:
        """
        安排预防性维护

        Args:
            component_id: 组件 ID

        Returns:
            修复任务
        """
        return self.repair_coordinator.create_repair_task(
            component_id, RepairPriority.SCHEDULED
        )

    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "health_monitor": self.health_monitor.get_status(),
            "repair_coordinator": self.repair_coordinator.get_status(),
            "auto_detect_enabled": self._auto_detect_enabled,
            "last_detection_time": self._last_detection_time,
            "preventive_maintenance_threshold": self._preventive_maintenance_threshold,
        }


class SimToRealBridge:
    """
    Sim-to-Real 桥接

    为将仿真策略迁移到真实机器人做准备。
    """

    def __init__(self):
        """初始化桥接"""
        self._domain_randomization_config: Dict[str, Any] = {}
        self._reality_gap_metrics: Dict[str, float] = {}
        self._transfer_strategies: List[Dict] = []

    def configure_domain_randomization(
        self,
        physics_variance: float = 0.1,
        visual_variance: float = 0.1,
        sensor_noise: float = 0.05,
    ):
        """
        配置域随机化

        Args:
            physics_variance: 物理参数方差
            visual_variance: 视觉参数方差
            sensor_noise: 传感器噪声
        """
        self._domain_randomization_config = {
            "physics": {
                "mass_variance": physics_variance,
                "friction_variance": physics_variance,
                "inertia_variance": physics_variance,
            },
            "visual": {
                "lighting_variance": visual_variance,
                "texture_variance": visual_variance,
                "color_variance": visual_variance,
            },
            "sensor": {
                "position_noise": sensor_noise,
                "velocity_noise": sensor_noise,
                "force_noise": sensor_noise,
            },
        }

    def apply_domain_randomization(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        应用域随机化

        Args:
            params: 原始参数

        Returns:
            随机化后的参数
        """
        randomized = params.copy()

        # 物理随机化
        if "mass" in params:
            variance = self._domain_randomization_config.get("physics", {}).get("mass_variance", 0.1)
            randomized["mass"] *= (1 + np.random.normal(0, variance))

        if "friction" in params:
            variance = self._domain_randomization_config.get("physics", {}).get("friction_variance", 0.1)
            randomized["friction"] *= (1 + np.random.normal(0, variance))

        # 传感器噪声
        if "position" in params:
            noise = self._domain_randomization_config.get("sensor", {}).get("position_noise", 0.05)
            randomized["position"] = np.array(params["position"]) + np.random.normal(0, noise, 3)

        return randomized

    def estimate_reality_gap(
        self,
        sim_performance: Dict[str, float],
        real_performance: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        估计现实差距

        Args:
            sim_performance: 仿真性能指标
            real_performance: 真实性能指标 (可选)

        Returns:
            差距指标
        """
        if real_performance is None:
            # 估计差距
            estimated_gap = {
                "success_rate_gap": 0.1,  # 假设10%的成功率差距
                "precision_gap": 0.02,    # 2cm精度差距
                "speed_gap": 0.2,         # 20%速度差距
            }
        else:
            estimated_gap = {
                "success_rate_gap": sim_performance.get("success_rate", 1.0) - real_performance.get("success_rate", 0.8),
                "precision_gap": abs(sim_performance.get("precision", 0.01) - real_performance.get("precision", 0.03)),
                "speed_gap": (sim_performance.get("speed", 1.0) - real_performance.get("speed", 0.8)) / sim_performance.get("speed", 1.0),
            }

        self._reality_gap_metrics = estimated_gap
        return estimated_gap

    def generate_transfer_strategy(self) -> Dict[str, Any]:
        """
        生成迁移策略

        Returns:
            迁移策略
        """
        strategy = {
            "domain_randomization": self._domain_randomization_config,
            "reality_gap": self._reality_gap_metrics,
            "recommendations": [],
        }

        # 根据差距生成建议
        if self._reality_gap_metrics.get("success_rate_gap", 0) > 0.15:
            strategy["recommendations"].append({
                "type": "increase_training_diversity",
                "description": "增加训练场景多样性以提高鲁棒性",
            })

        if self._reality_gap_metrics.get("precision_gap", 0) > 0.01:
            strategy["recommendations"].append({
                "type": "add_sensor_calibration",
                "description": "添加传感器校准步骤",
            })

        if self._reality_gap_metrics.get("speed_gap", 0) > 0.1:
            strategy["recommendations"].append({
                "type": "conservative_execution",
                "description": "在真实机器人上使用保守的执行速度",
            })

        self._transfer_strategies.append(strategy)
        return strategy

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "domain_randomization_configured": bool(self._domain_randomization_config),
            "reality_gap_estimated": bool(self._reality_gap_metrics),
            "transfer_strategies_generated": len(self._transfer_strategies),
        }
