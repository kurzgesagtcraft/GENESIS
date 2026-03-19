"""
GENESIS Semiconductor Fabrication Module

芯片制造极简模拟，展示框架可扩展性。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import time


class ProcessStage(Enum):
    """工艺阶段"""
    IDLE = "idle"
    WAITING_WAFER = "waiting_wafer"
    CLEANING = "cleaning"
    PHOTOLITHOGRAPHY = "photolithography"
    ETCHING = "etching"
    DEPOSITION = "deposition"
    DOPING = "doping"
    METALLIZATION = "metallization"
    TESTING = "testing"
    PACKAGING = "packaging"
    COMPLETED = "completed"
    FAILED = "failed"


class WaferStatus(Enum):
    """晶圆状态"""
    RAW = "raw"                     # 原始晶圆
    CLEANED = "cleaned"             # 已清洗
    PATTERNED = "patterned"         # 已光刻
    ETCHED = "etched"               # 已蚀刻
    DEPOSITED = "deposited"         # 已沉积
    DOPED = "doped"                 # 已掺杂
    METALIZED = "metalized"         # 已金属化
    TESTED = "tested"               # 已测试
    PACKAGED = "packaged"           # 已封装
    DEFECTIVE = "defective"         # 缺陷
    COMPLETED = "completed"         # 完成


class DefectSeverity(Enum):
    """缺陷严重程度"""
    MINOR = "minor"       # 轻微缺陷
    MAJOR = "major"       # 主要缺陷
    CRITICAL = "critical" # 严重缺陷
    FATAL = "fatal"       # 致命缺陷


@dataclass
class WaferSpec:
    """晶圆规格"""
    wafer_id: str
    diameter_mm: float = 300.0      # 晶圆直径 (mm)
    thickness_um: float = 775.0     # 厚度 (μm)
    material: str = "silicon"       # 材料
    orientation: str = "<100>"      # 晶向
    resistivity_ohm_cm: float = 10.0  # 电阻率


@dataclass
class ProcessStep:
    """工艺步骤"""
    name: str
    stage: ProcessStage
    duration_seconds: float
    temperature_c: float = 25.0
    pressure_pa: float = 101325.0   # 标准大气压
    gas_flow: Dict[str, float] = field(default_factory=dict)
    power_watts: float = 0.0
    precision_nm: float = 10.0      # 精度要求 (nm)
    defect_probability: float = 0.01


@dataclass
class WaferDefect:
    """晶圆缺陷"""
    defect_type: str
    severity: DefectSeverity
    location: Tuple[float, float]   # (x, y) mm
    size_um: float                  # 缺陷尺寸 (μm)
    detected_at_stage: ProcessStage


@dataclass
class ChipSpec:
    """芯片规格"""
    name: str
    node_nm: int = 7                # 工艺节点 (nm)
    die_size_mm2: float = 100.0     # 裸片面积 (mm²)
    transistor_count: int = 10_000_000_000  # 晶体管数量
    layers: int = 15                # 金属层数
    power_watts: float = 15.0       # 功耗 (W)


class Wafer:
    """
    晶圆类

    表示一个正在加工的晶圆。
    """

    def __init__(self, spec: WaferSpec):
        """
        初始化晶圆

        Args:
            spec: 晶圆规格
        """
        self.spec = spec
        self.status = WaferStatus.RAW
        self.current_stage = ProcessStage.IDLE
        self.defects: List[WaferDefect] = []
        self.yield_percentage = 100.0
        self.process_history: List[Dict] = []

        # 晶圆上的芯片
        self._chips: List[Dict] = []
        self._initialize_chips()

    def _initialize_chips(self):
        """初始化晶圆上的芯片"""
        # 简化：假设晶圆上有一定数量的芯片位置
        # 实际应根据晶圆尺寸和芯片尺寸计算
        num_chips = 100  # 简化数量

        for i in range(num_chips):
            self._chips.append({
                "id": f"{self.spec.wafer_id}_die_{i:03d}",
                "status": "pending",
                "defects": [],
            })

    def apply_process(self, step: ProcessStep) -> bool:
        """
        应用工艺步骤

        Args:
            step: 工艺步骤

        Returns:
            是否成功
        """
        # 记录工艺历史
        self.process_history.append({
            "step": step.name,
            "stage": step.stage.value,
            "timestamp": time.time(),
            "duration": step.duration_seconds,
        })

        # 更新阶段
        self.current_stage = step.stage

        # 检查是否产生缺陷
        if np.random.random() < step.defect_probability:
            self._add_random_defect(step)

        # 更新状态
        self._update_status(step.stage)

        return True

    def _add_random_defect(self, step: ProcessStep):
        """添加随机缺陷"""
        defect_types = {
            ProcessStage.CLEANING: ["particle", "contamination"],
            ProcessStage.PHOTOLITHOGRAPHY: ["pattern_error", "alignment_error", "photoresist_defect"],
            ProcessStage.ETCHING: ["overetch", "underetch", "sidewall_roughness"],
            ProcessStage.DEPOSITION: ["pinhole", "nonuniformity", "delamination"],
            ProcessStage.DOPING: ["doping_variation", "activation_failure"],
            ProcessStage.METALLIZATION: ["short", "open", "electromigration"],
        }

        defect_type = np.random.choice(
            defect_types.get(step.stage, ["unknown"])
        )

        # 随机位置
        x = np.random.uniform(0, self.spec.diameter_mm)
        y = np.random.uniform(0, self.spec.diameter_mm)

        # 随机严重程度
        severity = np.random.choice(
            [DefectSeverity.MINOR, DefectSeverity.MAJOR, DefectSeverity.CRITICAL, DefectSeverity.FATAL],
            p=[0.5, 0.3, 0.15, 0.05],
        )

        defect = WaferDefect(
            defect_type=defect_type,
            severity=severity,
            location=(x, y),
            size_um=np.random.uniform(0.1, 10.0),
            detected_at_stage=step.stage,
        )

        self.defects.append(defect)

        # 更新良率
        yield_loss = {
            DefectSeverity.MINOR: 0.5,
            DefectSeverity.MAJOR: 2.0,
            DefectSeverity.CRITICAL: 10.0,
            DefectSeverity.FATAL: 50.0,
        }
        self.yield_percentage -= yield_loss[severity]

    def _update_status(self, stage: ProcessStage):
        """更新晶圆状态"""
        status_map = {
            ProcessStage.CLEANING: WaferStatus.CLEANED,
            ProcessStage.PHOTOLITHOGRAPHY: WaferStatus.PATTERNED,
            ProcessStage.ETCHING: WaferStatus.ETCHED,
            ProcessStage.DEPOSITION: WaferStatus.DEPOSITED,
            ProcessStage.DOPING: WaferStatus.DOPED,
            ProcessStage.METALLIZATION: WaferStatus.METALIZED,
            ProcessStage.TESTING: WaferStatus.TESTED,
            ProcessStage.PACKAGING: WaferStatus.PACKAGED,
        }

        if stage in status_map:
            self.status = status_map[stage]

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "wafer_id": self.spec.wafer_id,
            "status": self.status.value,
            "current_stage": self.current_stage.value,
            "yield_percentage": max(0, self.yield_percentage),
            "defect_count": len(self.defects),
            "process_steps_completed": len(self.process_history),
            "chips_total": len(self._chips),
        }


class ProcessStation:
    """
    工艺站

    执行特定的半导体工艺。
    """

    def __init__(
        self,
        name: str,
        station_type: ProcessStage,
        capacity: int = 1,
    ):
        """
        初始化工艺站

        Args:
            name: 工艺站名称
            station_type: 工艺站类型
            capacity: 容量 (同时处理的晶圆数)
        """
        self.name = name
        self.station_type = station_type
        self.capacity = capacity

        self._current_wafers: List[Wafer] = []
        self._process_queue: List[Wafer] = []
        self._is_processing = False
        self._process_start_time = 0.0
        self._current_step: Optional[ProcessStep] = None

        # 统计
        self._total_processed = 0
        self._total_defects_generated = 0

    def load_wafer(self, wafer: Wafer) -> bool:
        """
        加载晶圆

        Args:
            wafer: 晶圆实例

        Returns:
            是否成功
        """
        if len(self._current_wafers) >= self.capacity:
            # 加入队列
            self._process_queue.append(wafer)
            return True

        self._current_wafers.append(wafer)
        return True

    def start_process(self, step: ProcessStep) -> bool:
        """
        开始工艺

        Args:
            step: 工艺步骤

        Returns:
            是否成功
        """
        if not self._current_wafers:
            return False

        if step.stage != self.station_type:
            return False

        self._current_step = step
        self._is_processing = True
        self._process_start_time = time.time()

        return True

    def update(self, dt: float) -> List[Wafer]:
        """
        更新工艺站状态

        Args:
            dt: 时间步长 (s)

        Returns:
            完成的晶圆列表
        """
        completed_wafers = []

        if self._is_processing and self._current_step:
            elapsed = time.time() - self._process_start_time

            if elapsed >= self._current_step.duration_seconds:
                # 工艺完成
                for wafer in self._current_wafers:
                    wafer.apply_process(self._current_step)
                    self._total_processed += 1
                    self._total_defects_generated += len(wafer.defects) - len([
                        d for d in wafer.defects
                        if d.detected_at_stage != self._current_step.stage
                    ])
                    completed_wafers.append(wafer)

                self._current_wafers = []
                self._is_processing = False
                self._current_step = None

                # 从队列加载新晶圆
                while self._process_queue and len(self._current_wafers) < self.capacity:
                    self._current_wafers.append(self._process_queue.pop(0))

        return completed_wafers

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "name": self.name,
            "type": self.station_type.value,
            "is_processing": self._is_processing,
            "current_wafers": len(self._current_wafers),
            "queue_length": len(self._process_queue),
            "total_processed": self._total_processed,
            "total_defects": self._total_defects_generated,
        }


class SemiconductorFab:
    """
    半导体制造厂

    管理整个芯片制造流程。
    """

    def __init__(self, name: str = "genesis_fab"):
        """
        初始化半导体制造厂

        Args:
            name: 制造厂名称
        """
        self.name = name

        # 工艺站
        self._stations: Dict[ProcessStage, ProcessStation] = {}
        self._initialize_stations()

        # 晶圆追踪
        self._wafers: Dict[str, Wafer] = {}
        self._completed_wafers: List[Wafer] = []

        # 工艺流程
        self._process_flow = self._create_process_flow()

        # 统计
        self._total_wafers_started = 0
        self._total_chips_produced = 0

    def _initialize_stations(self):
        """初始化工艺站"""
        station_configs = [
            (ProcessStage.CLEANING, "clean_station", 2),
            (ProcessStage.PHOTOLITHOGRAPHY, "photo_station", 1),
            (ProcessStage.ETCHING, "etch_station", 1),
            (ProcessStage.DEPOSITION, "dep_station", 1),
            (ProcessStage.DOPING, "doping_station", 1),
            (ProcessStage.METALLIZATION, "metal_station", 1),
            (ProcessStage.TESTING, "test_station", 2),
            (ProcessStage.PACKAGING, "package_station", 1),
        ]

        for stage, name, capacity in station_configs:
            self._stations[stage] = ProcessStation(name, stage, capacity)

    def _create_process_flow(self) -> List[ProcessStep]:
        """创建工艺流程"""
        return [
            ProcessStep(
                name="wafer_cleaning",
                stage=ProcessStage.CLEANING,
                duration_seconds=30.0,
                temperature_c=80.0,
                defect_probability=0.005,
            ),
            ProcessStep(
                name="photoresist_coating",
                stage=ProcessStage.PHOTOLITHOGRAPHY,
                duration_seconds=20.0,
                precision_nm=5.0,
                defect_probability=0.02,
            ),
            ProcessStep(
                name="exposure",
                stage=ProcessStage.PHOTOLITHOGRAPHY,
                duration_seconds=15.0,
                precision_nm=2.0,
                defect_probability=0.03,
            ),
            ProcessStep(
                name="plasma_etch",
                stage=ProcessStage.ETCHING,
                duration_seconds=45.0,
                temperature_c=100.0,
                precision_nm=1.0,
                defect_probability=0.04,
            ),
            ProcessStep(
                name="cvd_deposition",
                stage=ProcessStage.DEPOSITION,
                duration_seconds=60.0,
                temperature_c=400.0,
                pressure_pa=100.0,
                defect_probability=0.03,
            ),
            ProcessStep(
                name="ion_implant",
                stage=ProcessStage.DOPING,
                duration_seconds=30.0,
                power_watts=1000.0,
                defect_probability=0.02,
            ),
            ProcessStep(
                name="metal_deposition",
                stage=ProcessStage.METALLIZATION,
                duration_seconds=40.0,
                temperature_c=300.0,
                defect_probability=0.03,
            ),
            ProcessStep(
                name="electrical_test",
                stage=ProcessStage.TESTING,
                duration_seconds=20.0,
                defect_probability=0.01,
            ),
            ProcessStep(
                name="die_packaging",
                stage=ProcessStage.PACKAGING,
                duration_seconds=50.0,
                defect_probability=0.02,
            ),
        ]

    def create_wafer(self, wafer_id: Optional[str] = None) -> Wafer:
        """
        创建新晶圆

        Args:
            wafer_id: 晶圆 ID (可选)

        Returns:
            晶圆实例
        """
        if wafer_id is None:
            wafer_id = f"wafer_{len(self._wafers) + 1:04d}"

        spec = WaferSpec(wafer_id=wafer_id)
        wafer = Wafer(spec)

        self._wafers[wafer_id] = wafer
        self._total_wafers_started += 1

        return wafer

    def process_wafer(self, wafer: Wafer) -> bool:
        """
        处理晶圆

        将晶圆送入工艺流程。

        Args:
            wafer: 晶圆实例

        Returns:
            是否成功开始处理
        """
        # 找到下一个工艺站
        current_stage = wafer.current_stage

        # 确定下一个工艺步骤
        next_step = None
        for step in self._process_flow:
            if step.stage != current_stage:
                # 检查是否已完成此步骤
                completed_stages = [
                    h["stage"] for h in wafer.process_history
                ]
                if step.stage.value not in completed_stages:
                    next_step = step
                    break

        if next_step is None:
            # 所有工艺完成
            return False

        # 加载到对应工艺站
        station = self._stations.get(next_step.stage)
        if station:
            station.load_wafer(wafer)
            station.start_process(next_step)
            return True

        return False

    def update(self, dt: float):
        """
        更新制造厂状态

        Args:
            dt: 时间步长 (s)
        """
        for station in self._stations.values():
            completed = station.update(dt)

            for wafer in completed:
                # 检查是否完成所有工艺
                if wafer.status == WaferStatus.PACKAGED:
                    self._completed_wafers.append(wafer)
                    self._total_chips_produced += len([
                        c for c in wafer._chips
                        if c["status"] != "defective"
                    ])
                else:
                    # 继续下一个工艺
                    self.process_wafer(wafer)

    def get_yield_statistics(self) -> Dict[str, Any]:
        """获取良率统计"""
        if not self._completed_wafers:
            return {"total_wafers": 0}

        yields = [w.yield_percentage for w in self._completed_wafers]

        return {
            "total_wafers": len(self._completed_wafers),
            "average_yield": np.mean(yields),
            "min_yield": np.min(yields),
            "max_yield": np.max(yields),
            "total_chips_produced": self._total_chips_produced,
            "total_defects": sum(len(w.defects) for w in self._completed_wafers),
        }

    def get_status(self) -> Dict[str, Any]:
        """获取制造厂状态"""
        return {
            "name": self.name,
            "wafers_in_process": len(self._wafers) - len(self._completed_wafers),
            "wafers_completed": len(self._completed_wafers),
            "stations": {
                stage.value: station.get_status()
                for stage, station in self._stations.items()
            },
            "yield_stats": self.get_yield_statistics(),
        }


class ChipManufacturingWorkflow:
    """
    芯片制造工作流

    协调机器人在各工艺站之间搬运晶圆。
    """

    def __init__(self, fab: SemiconductorFab):
        """
        初始化工作流

        Args:
            fab: 半导体制造厂实例
        """
        self._fab = fab
        self._pending_transfers: List[Dict] = []
        self._active_transfers: List[Dict] = []

    def plan_transfers(self) -> List[Dict]:
        """
        规划晶圆转移

        Returns:
            转移任务列表
        """
        transfers = []

        # 检查每个工艺站的完成状态
        for stage, station in self._fab._stations.items():
            completed_wafers = [
                w for w in self._fab._wafers.values()
                if w.current_stage == stage and w not in station._current_wafers
            ]

            for wafer in completed_wafers:
                # 找到下一个工艺站
                next_stage = self._get_next_stage(stage)
                if next_stage:
                    transfers.append({
                        "wafer_id": wafer.spec.wafer_id,
                        "from_stage": stage.value,
                        "to_stage": next_stage.value,
                        "priority": 1,
                    })

        return transfers

    def _get_next_stage(self, current_stage: ProcessStage) -> Optional[ProcessStage]:
        """获取下一个工艺阶段"""
        stage_order = [
            ProcessStage.CLEANING,
            ProcessStage.PHOTOLITHOGRAPHY,
            ProcessStage.ETCHING,
            ProcessStage.DEPOSITION,
            ProcessStage.DOPING,
            ProcessStage.METALLIZATION,
            ProcessStage.TESTING,
            ProcessStage.PACKAGING,
        ]

        try:
            idx = stage_order.index(current_stage)
            if idx < len(stage_order) - 1:
                return stage_order[idx + 1]
        except ValueError:
            pass

        return None

    def execute_transfer(
        self,
        wafer_id: str,
        from_stage: str,
        to_stage: str,
    ) -> bool:
        """
        执行晶圆转移

        Args:
            wafer_id: 晶圆 ID
            from_stage: 源工艺阶段
            to_stage: 目标工艺阶段

        Returns:
            是否成功
        """
        wafer = self._fab._wafers.get(wafer_id)
        if wafer is None:
            return False

        # 加载到目标工艺站
        target_stage = ProcessStage(to_stage)
        target_station = self._fab._stations.get(target_stage)

        if target_station:
            target_station.load_wafer(wafer)
            return True

        return False

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "pending_transfers": len(self._pending_transfers),
            "active_transfers": len(self._active_transfers),
            "fab_status": self._fab.get_status(),
        }
