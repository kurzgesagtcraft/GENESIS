"""
GENESIS 并行调度模块

在工站加工等待期间调度其他任务，
提高系统整体效率，减少空闲时间。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
import math
from datetime import datetime


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0    # 关键任务（必须立即执行）
    HIGH = 1        # 高优先级
    MEDIUM = 2      # 中优先级
    LOW = 3         # 低优先级
    BACKGROUND = 4  # 后台任务


class TaskType(Enum):
    """任务类型"""
    MINING = "mining"               # 采矿
    DELIVERY = "delivery"           # 运输
    PROCESSING = "processing"       # 加工
    ASSEMBLY = "assembly"           # 装配
    CHARGING = "charging"           # 充电
    WAREHOUSE = "warehouse"         # 仓储
    WAITING = "waiting"             # 等待
    PARALLEL = "parallel"           # 可并行任务


@dataclass
class TaskWindow:
    """任务时间窗口"""
    task_id: str
    task_type: TaskType
    start_time: float
    end_time: float
    duration: float
    priority: TaskPriority
    dependencies: List[str] = field(default_factory=list)
    can_parallelize: bool = True
    station: str = ""
    location: str = ""
    metadata: Dict = field(default_factory=dict)
    
    @property
    def slack(self) -> float:
        """时间窗口的松弛时间"""
        return self.duration
    
    def overlaps(self, other: "TaskWindow") -> bool:
        """检查是否与另一窗口重叠"""
        return not (self.end_time <= other.start_time or other.end_time <= self.start_time)
    
    def contains(self, time: float) -> bool:
        """检查时间点是否在窗口内"""
        return self.start_time <= time <= self.end_time
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "can_parallelize": self.can_parallelize,
            "station": self.station,
            "location": self.location,
        }


@dataclass
class WaitingPeriod:
    """等待时段"""
    station: str
    recipe: str
    start_time: float
    end_time: float
    duration: float
    available_tasks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "station": self.station,
            "recipe": self.recipe,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "available_tasks": self.available_tasks,
        }


@dataclass
class ScheduledTask:
    """已调度任务"""
    task_id: str
    task_type: TaskType
    scheduled_start: float
    scheduled_end: float
    is_parallel: bool = False
    parallel_with: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "scheduled_start": self.scheduled_start,
            "scheduled_end": self.scheduled_end,
            "is_parallel": self.is_parallel,
            "parallel_with": self.parallel_with,
        }


@dataclass
class ScheduleResult:
    """调度结果"""
    scheduled_tasks: List[ScheduledTask]
    waiting_periods: List[WaitingPeriod]
    parallel_tasks: List[Tuple[str, str]]  # (主任务, 并行任务)
    total_time: float
    idle_time: float
    efficiency: float  # 有效工作时间占比
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "scheduled_tasks": [t.to_dict() for t in self.scheduled_tasks],
            "waiting_periods": [w.to_dict() for w in self.waiting_periods],
            "parallel_tasks": self.parallel_tasks,
            "total_time": self.total_time,
            "idle_time": self.idle_time,
            "efficiency": self.efficiency,
        }


class ParallelScheduler:
    """并行调度器"""
    
    # 可在等待期间执行的任务类型
    PARALLEL_COMPATIBLE_TASKS = {
        TaskType.MINING,
        TaskType.DELIVERY,
        TaskType.WAREHOUSE,
    }
    
    # 任务类型预估时间（秒）
    TASK_DURATION_ESTIMATES = {
        TaskType.MINING: 60.0,
        TaskType.DELIVERY: 30.0,
        TaskType.PROCESSING: 0.0,  # 取决于配方
        TaskType.ASSEMBLY: 0.0,    # 取决于配方
        TaskType.CHARGING: 300.0,
        TaskType.WAREHOUSE: 20.0,
        TaskType.WAITING: 0.0,
    }
    
    def __init__(
        self,
        min_parallel_window: float = 30.0,
        max_parallel_tasks: int = 1,
    ):
        """
        初始化并行调度器
        
        Args:
            min_parallel_window: 最小并行时间窗口（秒）
            max_parallel_tasks: 最大并行任务数
        """
        self.min_parallel_window = min_parallel_window
        self.max_parallel_tasks = max_parallel_tasks
        self.task_windows: List[TaskWindow] = []
        self.waiting_periods: List[WaitingPeriod] = []
        
    def add_task(self, task: TaskWindow) -> None:
        """添加任务"""
        self.task_windows.append(task)
    
    def add_waiting_period(
        self,
        station: str,
        recipe: str,
        start_time: float,
        duration: float,
    ) -> None:
        """添加等待时段"""
        self.waiting_periods.append(WaitingPeriod(
            station=station,
            recipe=recipe,
            start_time=start_time,
            end_time=start_time + duration,
            duration=duration,
        ))
    
    def find_parallelizable_tasks(
        self,
        waiting_period: WaitingPeriod,
        exclude_stations: Optional[Set[str]] = None,
    ) -> List[TaskWindow]:
        """
        找出可在等待期间执行的任务
        
        Args:
            waiting_period: 等待时段
            exclude_stations: 排除的工站集合
        
        Returns:
            可并行执行的任务列表
        """
        exclude_stations = exclude_stations or set()
        compatible_tasks = []
        
        for task in self.task_windows:
            # 检查任务类型是否兼容
            if task.task_type not in self.PARALLEL_COMPATIBLE_TASKS:
                continue
            
            # 检查是否在排除的工站
            if task.station in exclude_stations:
                continue
            
            # 检查时间窗口是否合适
            if task.duration <= waiting_period.duration:
                compatible_tasks.append(task)
        
        # 按优先级和持续时间排序
        compatible_tasks.sort(key=lambda t: (t.priority.value, -t.duration))
        
        return compatible_tasks
    
    def schedule(self) -> ScheduleResult:
        """执行调度"""
        scheduled_tasks: List[ScheduledTask] = []
        parallel_pairs: List[Tuple[str, str]] = []
        
        # 按开始时间排序任务
        sorted_tasks = sorted(self.task_windows, key=lambda t: t.start_time)
        
        # 按开始时间排序等待时段
        sorted_waitings = sorted(self.waiting_periods, key=lambda w: w.start_time)
        
        # 已调度任务集合
        scheduled_ids: Set[str] = set()
        
        # 处理每个等待时段
        for waiting in sorted_waitings:
            if waiting.duration < self.min_parallel_window:
                continue
            
            # 找可并行任务
            parallel_tasks = self.find_parallelizable_tasks(waiting)
            
            # 选择最佳并行任务
            selected_tasks = []
            remaining_time = waiting.duration
            
            for task in parallel_tasks:
                if task.task_id in scheduled_ids:
                    continue
                
                if task.duration <= remaining_time:
                    selected_tasks.append(task)
                    remaining_time -= task.duration
                    
                    if len(selected_tasks) >= self.max_parallel_tasks:
                        break
            
            # 记录并行任务
            for task in selected_tasks:
                scheduled_ids.add(task.task_id)
                
                scheduled_task = ScheduledTask(
                    task_id=task.task_id,
                    task_type=task.task_type,
                    scheduled_start=waiting.start_time,
                    scheduled_end=waiting.start_time + task.duration,
                    is_parallel=True,
                    parallel_with=[waiting.station],
                )
                scheduled_tasks.append(scheduled_task)
                
                parallel_pairs.append((waiting.station, task.task_id))
                waiting.available_tasks.append(task.task_id)
        
        # 调度剩余任务
        current_time = 0.0
        for task in sorted_tasks:
            if task.task_id in scheduled_ids:
                continue
            
            # 检查依赖
            for dep_id in task.dependencies:
                dep_task = next(
                    (t for t in scheduled_tasks if t.task_id == dep_id),
                    None
                )
                if dep_task:
                    current_time = max(current_time, dep_task.scheduled_end)
            
            scheduled_task = ScheduledTask(
                task_id=task.task_id,
                task_type=task.task_type,
                scheduled_start=current_time,
                scheduled_end=current_time + task.duration,
            )
            scheduled_tasks.append(scheduled_task)
            scheduled_ids.add(task.task_id)
            current_time = scheduled_task.scheduled_end
        
        # 计算统计信息
        total_time = max(t.scheduled_end for t in scheduled_tasks) if scheduled_tasks else 0
        total_work_time = sum(t.scheduled_end - t.scheduled_start for t in scheduled_tasks)
        idle_time = total_time - total_work_time
        efficiency = total_work_time / total_time if total_time > 0 else 0
        
        return ScheduleResult(
            scheduled_tasks=scheduled_tasks,
            waiting_periods=self.waiting_periods,
            parallel_tasks=parallel_pairs,
            total_time=total_time,
            idle_time=idle_time,
            efficiency=efficiency,
        )
    
    def optimize_schedule(self) -> ScheduleResult:
        """优化调度（尝试最大化并行）"""
        # 多次尝试不同的调度策略
        best_result = self.schedule()
        
        # 尝试不同的任务组合
        for waiting in self.waiting_periods:
            if waiting.duration < self.min_parallel_window:
                continue
            
            # 尝试选择不同的任务组合
            parallel_tasks = self.find_parallelizable_tasks(waiting)
            
            if len(parallel_tasks) > self.max_parallel_tasks:
                # 尝试选择总时间最长的组合
                best_combo = []
                best_time = 0
                
                for i in range(len(parallel_tasks) - self.max_parallel_tasks + 1):
                    combo = parallel_tasks[i:i + self.max_parallel_tasks]
                    combo_time = sum(t.duration for t in combo)
                    
                    if combo_time > best_time:
                        best_time = combo_time
                        best_combo = combo
                
                # 更新等待时段的可用任务
                waiting.available_tasks = [t.task_id for t in best_combo]
        
        return self.schedule()
    
    def get_schedule_gantt_data(self) -> List[Dict]:
        """生成甘特图数据"""
        result = self.schedule()
        gantt_data = []
        
        for task in result.scheduled_tasks:
            gantt_data.append({
                "task_id": task.task_id,
                "task_type": task.task_type.value,
                "start": task.scheduled_start,
                "end": task.scheduled_end,
                "is_parallel": task.is_parallel,
                "parallel_with": task.parallel_with,
            })
        
        return gantt_data
    
    def calculate_parallel_efficiency(self) -> Dict:
        """计算并行效率"""
        result = self.schedule()
        
        total_waiting_time = sum(w.duration for w in self.waiting_periods)
        parallel_time = sum(
            sum(
                t.duration for t in self.find_parallelizable_tasks(w)
                if t.task_id in [st.task_id for st in result.scheduled_tasks if st.is_parallel]
            )
            for w in self.waiting_periods
        )
        
        return {
            "total_waiting_time": total_waiting_time,
            "parallel_execution_time": parallel_time,
            "parallel_efficiency": parallel_time / total_waiting_time if total_waiting_time > 0 else 0,
            "parallel_task_count": len(result.parallel_tasks),
            "efficiency_improvement": result.efficiency,
        }
    
    def clear(self) -> None:
        """清空调度器"""
        self.task_windows.clear()
        self.waiting_periods.clear()


def schedule_parallel_tasks(
    tasks: List[Dict],
    waiting_periods: List[Dict],
) -> ScheduleResult:
    """
    调度并行任务的便捷函数
    
    Args:
        tasks: 任务字典列表
        waiting_periods: 等待时段字典列表
    
    Returns:
        调度结果
    """
    scheduler = ParallelScheduler()
    
    # 添加任务
    for task in tasks:
        task_window = TaskWindow(
            task_id=task.get("id", ""),
            task_type=TaskType(task.get("type", "mining")),
            start_time=task.get("start_time", 0),
            end_time=task.get("end_time", 0),
            duration=task.get("duration", 0),
            priority=TaskPriority(task.get("priority", 2)),
            dependencies=task.get("dependencies", []),
            station=task.get("station", ""),
            location=task.get("location", ""),
        )
        scheduler.add_task(task_window)
    
    # 添加等待时段
    for wp in waiting_periods:
        scheduler.add_waiting_period(
            station=wp.get("station", ""),
            recipe=wp.get("recipe", ""),
            start_time=wp.get("start_time", 0),
            duration=wp.get("duration", 0),
        )
    
    return scheduler.optimize_schedule()
