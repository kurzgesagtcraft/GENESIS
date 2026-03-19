"""
GENESIS Realistic Manufacturing System Module

更真实的制造系统，包含装配动作、质量检测和工具更换。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import numpy as np
import time
from abc import ABC, abstractmethod


class AssemblyStage(Enum):
    """装配阶段"""
    IDLE = "idle"
    PREPARING = "preparing"
    ALIGNING = "aligning"
    INSERTING = "inserting"
    FASTENING = "fastening"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"


class QualityGrade(Enum):
    """质量等级"""
    EXCELLENT = "excellent"   # 优秀 (>95%)
    GOOD = "good"             # 良好 (85-95%)
    ACCEPTABLE = "acceptable" # 合格 (70-85%)
    POOR = "poor"             # 较差 (50-70%)
    DEFECTIVE = "defective"   # 缺陷 (<50%)


class DefectType(Enum):
    """缺陷类型"""
    NONE = "none"
    MISALIGNED = "misaligned"       # 对齐偏差
    LOOSE_CONNECTION = "loose"      # 连接松动
    MISSING_PART = "missing"        # 缺少零件
    DAMAGED = "damaged"             # 损坏
    CONTAMINATION = "contamination" # 污染
    DIMENSION_ERROR = "dimension"   # 尺寸误差
    ELECTRICAL_FAULT = "electrical" # 电气故障


class ToolType(Enum):
    """工具类型"""
    GRIPPER = "gripper"             # 通用夹爪
    PARALLEL_JAW = "parallel_jaw"   # 平行颚夹爪
    THREE_FINGER = "three_finger"   # 三指夹爪
    SUCTION = "suction"             # 吸盘
    SCREWDRIVER = "screwdriver"     # 螺丝刀
    NUT_RUNNER = "nut_runner"       # 螺母扳手
    WELDING_TORCH = "welding"       # 焊接枪
    GLUE_DISPENSER = "glue"         # 点胶器
    INSPECTION_CAMERA = "camera"    # 检测相机
    FORCE_SENSOR = "force_sensor"   # 力传感器


@dataclass
class ToolSpec:
    """工具规格"""
    tool_type: ToolType
    name: str
    weight_kg: float = 0.5
    max_force_n: float = 50.0
    precision_mm: float = 0.1
    compatible_operations: List[str] = field(default_factory=list)
    wear_rate: float = 0.001  # 每次操作的磨损率
    current_wear: float = 0.0  # 当前磨损程度 (0-1)


@dataclass
class AssemblyOperation:
    """装配操作"""
    name: str
    description: str
    required_tool: ToolType
    duration_seconds: float
    force_required_n: float = 10.0
    precision_required_mm: float = 1.0
    torque_required_nm: float = 0.0
    temperature_c: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class QualityCheckResult:
    """质量检查结果"""
    grade: QualityGrade
    score: float  # 0-100
    defects: List[DefectType]
    measurements: Dict[str, float]
    passed: bool
    timestamp: float = 0.0


@dataclass
class ProductSpecification:
    """产品规格"""
    name: str
    target_dimensions: Tuple[float, float, float]  # (长, 宽, 高) mm
    required_operations: List[str]  # 必需的操作列表
    tolerance_mm: float = 0.5
    weight_kg: float = 1.0
    quality_threshold: float = 70.0  # 最低合格分数


class EndEffector(ABC):
    """
    末端执行器基类

    所有工具的抽象基类。
    """

    def __init__(self, spec: ToolSpec):
        """
        初始化末端执行器

        Args:
            spec: 工具规格
        """
        self.spec = spec
        self._is_attached = False
        self._current_wear = spec.current_wear

    @abstractmethod
    def execute(self, operation: AssemblyOperation, params: Dict[str, Any]) -> bool:
        """
        执行操作

        Args:
            operation: 装配操作
            params: 操作参数

        Returns:
            是否成功
        """
        pass

    @abstractmethod
    def can_execute(self, operation: AssemblyOperation) -> bool:
        """
        检查是否可以执行操作

        Args:
            operation: 装配操作

        Returns:
            是否可以执行
        """
        pass

    def attach(self):
        """安装工具"""
        self._is_attached = True

    def detach(self):
        """拆卸工具"""
        self._is_attached = False

    def wear(self, amount: float = 0.001):
        """
        磨损工具

        Args:
            amount: 磨损量
        """
        self._current_wear = min(1.0, self._current_wear + amount)

    def needs_replacement(self) -> bool:
        """是否需要更换"""
        return self._current_wear > 0.8

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "type": self.spec.tool_type.value,
            "name": self.spec.name,
            "is_attached": self._is_attached,
            "wear": self._current_wear,
            "needs_replacement": self.needs_replacement(),
        }


class GripperTool(EndEffector):
    """通用夹爪"""

    def __init__(self, spec: Optional[ToolSpec] = None):
        spec = spec or ToolSpec(
            tool_type=ToolType.GRIPPER,
            name="standard_gripper",
            compatible_operations=["grasp", "place", "hold"],
        )
        super().__init__(spec)
        self._current_width = 0.0
        self._current_force = 0.0

    def execute(self, operation: AssemblyOperation, params: Dict[str, Any]) -> bool:
        if not self.can_execute(operation):
            return False

        # 模拟抓取
        self._current_width = params.get("width", 0.05)
        self._current_force = params.get("force", 30.0)

        # 磨损
        self.wear(self.spec.wear_rate)

        return True

    def can_execute(self, operation: AssemblyOperation) -> bool:
        return operation.name in self.spec.compatible_operations


class ScrewdriverTool(EndEffector):
    """螺丝刀"""

    def __init__(self, spec: Optional[ToolSpec] = None):
        spec = spec or ToolSpec(
            tool_type=ToolType.SCREWDRIVER,
            name="electric_screwdriver",
            compatible_operations=["screw", "unscrew", "fasten"],
            max_force_n=20.0,
        )
        super().__init__(spec)
        self._current_torque = 0.0
        self._rpm = 0.0

    def execute(self, operation: AssemblyOperation, params: Dict[str, Any]) -> bool:
        if not self.can_execute(operation):
            return False

        # 模拟拧螺丝
        self._current_torque = params.get("torque", operation.torque_required_nm)
        self._rpm = params.get("rpm", 100.0)

        # 磨损
        self.wear(self.spec.wear_rate * 2)  # 螺丝刀磨损更快

        return True

    def can_execute(self, operation: AssemblyOperation) -> bool:
        return operation.name in self.spec.compatible_operations


class WeldingTool(EndEffector):
    """焊接枪"""

    def __init__(self, spec: Optional[ToolSpec] = None):
        spec = spec or ToolSpec(
            tool_type=ToolType.WELDING_TORCH,
            name="spot_welder",
            compatible_operations=["weld", "join"],
            max_force_n=5.0,
        )
        super().__init__(spec)
        self._temperature = 25.0
        self._is_active = False

    def execute(self, operation: AssemblyOperation, params: Dict[str, Any]) -> bool:
        if not self.can_execute(operation):
            return False

        # 模拟焊接
        self._temperature = params.get("temperature", 1500.0)
        self._is_active = True

        # 磨损
        self.wear(self.spec.wear_rate * 3)  # 焊接磨损最快

        return True

    def can_execute(self, operation: AssemblyOperation) -> bool:
        return operation.name in self.spec.compatible_operations


class ToolChanger:
    """
    工具更换器

    管理末端执行器的更换。
    """

    def __init__(self):
        """初始化工具更换器"""
        self._tools: Dict[ToolType, EndEffector] = {}
        self._current_tool: Optional[EndEffector] = None
        self._tool_change_time = 5.0  # 更换时间 (秒)
        self._is_changing = False

    def register_tool(self, tool: EndEffector):
        """
        注册工具

        Args:
            tool: 工具实例
        """
        self._tools[tool.spec.tool_type] = tool

    def change_tool(self, tool_type: ToolType) -> bool:
        """
        更换工具

        Args:
            tool_type: 目标工具类型

        Returns:
            是否成功
        """
        if tool_type not in self._tools:
            return False

        # 卸载当前工具
        if self._current_tool is not None:
            self._current_tool.detach()

        # 安装新工具
        self._current_tool = self._tools[tool_type]
        self._current_tool.attach()
        self._is_changing = True

        return True

    def get_current_tool(self) -> Optional[EndEffector]:
        """获取当前工具"""
        return self._current_tool

    def get_available_tools(self) -> List[ToolType]:
        """获取可用工具列表"""
        return list(self._tools.keys())

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "current_tool": self._current_tool.spec.name if self._current_tool else None,
            "available_tools": [t.value for t in self._tools.keys()],
            "is_changing": self._is_changing,
            "tools_status": {
                t.value: tool.get_status()
                for t, tool in self._tools.items()
            },
        }


class QualityInspector:
    """
    质量检测器

    执行产品质量检测。
    """

    def __init__(self, defect_rate: float = 0.05):
        """
        初始化质量检测器

        Args:
            defect_rate: 基础缺陷率
        """
        self._defect_rate = defect_rate
        self._inspections: List[QualityCheckResult] = []
        self._defect_counts: Dict[DefectType, int] = {
            d: 0 for d in DefectType
        }

    def inspect(
        self,
        product: ProductSpecification,
        assembly_quality: float,
    ) -> QualityCheckResult:
        """
        检测产品质量

        Args:
            product: 产品规格
            assembly_quality: 装配质量 (0-100)

        Returns:
            检测结果
        """
        # 计算基础分数
        base_score = assembly_quality

        # 添加随机缺陷
        defects = []
        if np.random.random() < self._defect_rate:
            defect_type = self._random_defect()
            defects.append(defect_type)
            base_score -= np.random.uniform(10, 30)

        # 测量尺寸
        measurements = self._measure_dimensions(product)

        # 检查尺寸偏差
        for dim_name, (measured, target, tolerance) in measurements.items():
            if abs(measured - target) > tolerance:
                if DefectType.DIMENSION_ERROR not in defects:
                    defects.append(DefectType.DIMENSION_ERROR)
                base_score -= 5

        # 确定等级
        score = max(0, min(100, base_score))
        grade = self._score_to_grade(score)
        passed = score >= product.quality_threshold

        result = QualityCheckResult(
            grade=grade,
            score=score,
            defects=defects,
            measurements={k: v[0] for k, v in measurements.items()},
            passed=passed,
            timestamp=time.time(),
        )

        self._inspections.append(result)
        for defect in defects:
            self._defect_counts[defect] += 1

        return result

    def _random_defect(self) -> DefectType:
        """随机选择缺陷类型"""
        defect_weights = {
            DefectType.MISALIGNED: 0.3,
            DefectType.LOOSE_CONNECTION: 0.25,
            DefectType.MISSING_PART: 0.1,
            DefectType.DAMAGED: 0.15,
            DefectType.CONTAMINATION: 0.1,
            DefectType.ELECTRICAL_FAULT: 0.1,
        }
        defects = list(defect_weights.keys())
        weights = list(defect_weights.values())
        return np.random.choice(defects, p=weights)

    def _measure_dimensions(
        self,
        product: ProductSpecification,
    ) -> Dict[str, Tuple[float, float, float]]:
        """测量尺寸"""
        measurements = {}
        dims = ["length", "width", "height"]
        targets = product.target_dimensions

        for i, dim in enumerate(dims):
            # 添加测量噪声
            noise = np.random.normal(0, 0.1)
            measured = targets[i] + noise
            measurements[dim] = (measured, targets[i], product.tolerance_mm)

        return measurements

    def _score_to_grade(self, score: float) -> QualityGrade:
        """分数转等级"""
        if score > 95:
            return QualityGrade.EXCELLENT
        elif score > 85:
            return QualityGrade.GOOD
        elif score > 70:
            return QualityGrade.ACCEPTABLE
        elif score > 50:
            return QualityGrade.POOR
        else:
            return QualityGrade.DEFECTIVE

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        if not self._inspections:
            return {"total_inspections": 0}

        passed = sum(1 for i in self._inspections if i.passed)
        total = len(self._inspections)

        return {
            "total_inspections": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": passed / total if total > 0 else 0,
            "average_score": sum(i.score for i in self._inspections) / total,
            "defect_counts": {
                d.value: c for d, c in self._defect_counts.items() if c > 0
            },
        }


class RealisticAssembler:
    """
    真实装配站

    执行真实的装配操作，需要机器人参与。
    """

    def __init__(
        self,
        name: str = "realistic_assembler",
        defect_rate: float = 0.05,
    ):
        """
        初始化装配站

        Args:
            name: 装配站名称
            defect_rate: 缺陷率
        """
        self.name = name
        self._stage = AssemblyStage.IDLE
        self._tool_changer = ToolChanger()
        self._quality_inspector = QualityInspector(defect_rate)

        # 注册默认工具
        self._tool_changer.register_tool(GripperTool())
        self._tool_changer.register_tool(ScrewdriverTool())
        self._tool_changer.register_tool(WeldingTool())

        # 装配状态
        self._current_product: Optional[ProductSpecification] = None
        self._current_operation_idx = 0
        self._assembly_quality = 100.0
        self._operation_history: List[Dict] = []

        # 时间追踪
        self._stage_start_time = 0.0
        self._total_assembly_time = 0.0

    def start_assembly(self, product: ProductSpecification) -> bool:
        """
        开始装配

        Args:
            product: 产品规格

        Returns:
            是否成功开始
        """
        if self._stage != AssemblyStage.IDLE:
            return False

        self._current_product = product
        self._stage = AssemblyStage.PREPARING
        self._current_operation_idx = 0
        self._assembly_quality = 100.0
        self._stage_start_time = time.time()

        return True

    def execute_operation(
        self,
        operation: AssemblyOperation,
        params: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        执行装配操作

        Args:
            operation: 装配操作
            params: 操作参数

        Returns:
            是否成功
        """
        # 检查工具
        current_tool = self._tool_changer.get_current_tool()
        if current_tool is None or not current_tool.can_execute(operation):
            # 尝试更换工具
            if not self._tool_changer.change_tool(operation.required_tool):
                return False
            current_tool = self._tool_changer.get_current_tool()

        # 执行操作
        params = params or {}
        success = current_tool.execute(operation, params)

        if success:
            # 记录操作
            self._operation_history.append({
                "operation": operation.name,
                "tool": operation.required_tool.value,
                "duration": operation.duration_seconds,
                "timestamp": time.time(),
            })

            # 更新质量 (基于工具磨损)
            quality_loss = current_tool._current_wear * 5
            self._assembly_quality -= quality_loss

            # 更新阶段
            self._update_stage(operation)

        return success

    def _update_stage(self, operation: AssemblyOperation):
        """更新装配阶段"""
        # 根据操作类型更新阶段
        if "align" in operation.name.lower():
            self._stage = AssemblyStage.ALIGNING
        elif "insert" in operation.name.lower():
            self._stage = AssemblyStage.INSERTING
        elif "fasten" in operation.name.lower() or "screw" in operation.name.lower():
            self._stage = AssemblyStage.FASTENING
        elif "weld" in operation.name.lower():
            self._stage = AssemblyStage.FASTENING
        elif "verify" in operation.name.lower() or "check" in operation.name.lower():
            self._stage = AssemblyStage.VERIFYING

    def complete_assembly(self) -> QualityCheckResult:
        """
        完成装配

        Returns:
            质量检测结果
        """
        if self._current_product is None:
            return QualityCheckResult(
                grade=QualityGrade.DEFECTIVE,
                score=0,
                defects=[DefectType.MISSING_PART],
                measurements={},
                passed=False,
            )

        # 执行质量检测
        result = self._quality_inspector.inspect(
            self._current_product,
            self._assembly_quality,
        )

        # 更新状态
        self._total_assembly_time = time.time() - self._stage_start_time
        self._stage = AssemblyStage.COMPLETED if result.passed else AssemblyStage.FAILED

        return result

    def get_required_operations(self) -> List[AssemblyOperation]:
        """获取所需操作列表"""
        if self._current_product is None:
            return []

        # 根据产品生成操作序列
        operations = []
        for op_name in self._current_product.required_operations:
            op = self._create_operation(op_name)
            if op:
                operations.append(op)

        return operations

    def _create_operation(self, name: str) -> Optional[AssemblyOperation]:
        """创建操作"""
        operation_templates = {
            "align": AssemblyOperation(
                name="align",
                description="对齐零件",
                required_tool=ToolType.GRIPPER,
                duration_seconds=5.0,
                precision_required_mm=0.5,
            ),
            "insert": AssemblyOperation(
                name="insert",
                description="插入零件",
                required_tool=ToolType.GRIPPER,
                duration_seconds=10.0,
                force_required_n=20.0,
            ),
            "screw": AssemblyOperation(
                name="screw",
                description="拧紧螺丝",
                required_tool=ToolType.SCREWDRIVER,
                duration_seconds=15.0,
                torque_required_nm=2.0,
            ),
            "weld": AssemblyOperation(
                name="weld",
                description="焊接连接",
                required_tool=ToolType.WELDING_TORCH,
                duration_seconds=20.0,
                temperature_c=1500.0,
            ),
            "verify": AssemblyOperation(
                name="verify",
                description="验证装配",
                required_tool=ToolType.INSPECTION_CAMERA,
                duration_seconds=5.0,
            ),
        }
        return operation_templates.get(name)

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "name": self.name,
            "stage": self._stage.value,
            "current_product": self._current_product.name if self._current_product else None,
            "assembly_quality": self._assembly_quality,
            "operations_completed": len(self._operation_history),
            "total_assembly_time": self._total_assembly_time,
            "tool_changer": self._tool_changer.get_status(),
            "quality_stats": self._quality_inspector.get_statistics(),
        }


class WearSimulator:
    """
    磨损模拟器

    模拟机器人零件的磨损过程。
    """

    def __init__(self):
        """初始化磨损模拟器"""
        self._components: Dict[str, Dict[str, Any]] = {}
        self._wear_history: List[Dict] = []

    def register_component(
        self,
        name: str,
        component_type: str,
        initial_health: float = 100.0,
        wear_rate: float = 0.001,
        critical_threshold: float = 20.0,
    ):
        """
        注册组件

        Args:
            name: 组件名称
            component_type: 组件类型
            initial_health: 初始健康度
            wear_rate: 磨损率
            critical_threshold: 临界阈值
        """
        self._components[name] = {
            "type": component_type,
            "health": initial_health,
            "wear_rate": wear_rate,
            "critical_threshold": critical_threshold,
            "total_operations": 0,
        }

    def apply_wear(self, component_name: str, intensity: float = 1.0):
        """
        应用磨损

        Args:
            component_name: 组件名称
            intensity: 磨损强度
        """
        if component_name not in self._components:
            return

        component = self._components[component_name]
        wear = component["wear_rate"] * intensity
        component["health"] = max(0, component["health"] - wear)
        component["total_operations"] += 1

        # 记录磨损历史
        self._wear_history.append({
            "component": component_name,
            "wear": wear,
            "health": component["health"],
            "timestamp": time.time(),
        })

    def get_health(self, component_name: str) -> float:
        """获取组件健康度"""
        if component_name not in self._components:
            return 0.0
        return self._components[component_name]["health"]

    def needs_replacement(self, component_name: str) -> bool:
        """是否需要更换"""
        if component_name not in self._components:
            return False
        component = self._components[component_name]
        return component["health"] < component["critical_threshold"]

    def repair(self, component_name: str, restore_amount: float = 100.0):
        """
        修复组件

        Args:
            component_name: 组件名称
            restore_amount: 恢复量
        """
        if component_name not in self._components:
            return

        component = self._components[component_name]
        component["health"] = min(100.0, component["health"] + restore_amount)

    def get_all_status(self) -> Dict[str, Any]:
        """获取所有组件状态"""
        return {
            "components": {
                name: {
                    "type": info["type"],
                    "health": info["health"],
                    "needs_replacement": self.needs_replacement(name),
                    "total_operations": info["total_operations"],
                }
                for name, info in self._components.items()
            },
            "total_wear_events": len(self._wear_history),
        }


class SelfRepairSystem:
    """
    自我修复系统

    检测磨损并协调修复过程。
    """

    def __init__(self, wear_simulator: WearSimulator):
        """
        初始化自我修复系统

        Args:
            wear_simulator: 磨损模拟器
        """
        self._wear_simulator = wear_simulator
        self._repair_queue: List[Dict] = []
        self._repair_history: List[Dict] = []

    def check_health(self) -> List[str]:
        """
        检查健康状态

        Returns:
            需要修复的组件列表
        """
        needs_repair = []
        for name in self._wear_simulator._components:
            if self._wear_simulator.needs_replacement(name):
                needs_repair.append(name)
        return needs_repair

    def schedule_repair(self, component_name: str, priority: int = 1) -> bool:
        """
        安排修复

        Args:
            component_name: 组件名称
            priority: 优先级 (1=高, 2=中, 3=低)

        Returns:
            是否成功安排
        """
        if component_name not in self._wear_simulator._components:
            return False

        self._repair_queue.append({
            "component": component_name,
            "priority": priority,
            "scheduled_time": time.time(),
        })

        # 按优先级排序
        self._repair_queue.sort(key=lambda x: x["priority"])

        return True

    def execute_repair(self, component_name: str) -> bool:
        """
        执行修复

        Args:
            component_name: 组件名称

        Returns:
            是否成功
        """
        # 从队列中移除
        self._repair_queue = [
            r for r in self._repair_queue
            if r["component"] != component_name
        ]

        # 执行修复
        self._wear_simulator.repair(component_name)

        # 记录历史
        self._repair_history.append({
            "component": component_name,
            "repair_time": time.time(),
        })

        return True

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "pending_repairs": len(self._repair_queue),
            "repair_queue": self._repair_queue,
            "total_repairs": len(self._repair_history),
            "components_status": self._wear_simulator.get_all_status(),
        }
