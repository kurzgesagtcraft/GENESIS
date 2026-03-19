"""
GENESIS 路径优化模块

使用 TSP (旅行商问题) 算法优化任务访问顺序，
减少空跑距离，提高运输效率。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum
import math
import random
from abc import ABC, abstractmethod


class OptimizationMethod(Enum):
    """优化方法"""
    NEAREST_NEIGHBOR = "nearest_neighbor"   # 最近邻启发式
    TWO_OPT = "two_opt"                     # 2-opt 局部搜索
    SIMULATED_ANNEALING = "simulated_annealing"  # 模拟退火
    GENETIC = "genetic"                     # 遗传算法
    BRUTE_FORCE = "brute_force"             # 暴力搜索（小规模）


@dataclass
class Location:
    """位置点"""
    id: str
    x: float
    y: float
    zone: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def distance_to(self, other: "Location") -> float:
        """计算到另一点的欧氏距离"""
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2)
    
    def to_tuple(self) -> Tuple[float, float]:
        """转换为元组"""
        return (self.x, self.y)


@dataclass
class TaskLocation(Location):
    """任务位置（带任务信息）"""
    task_id: str = ""
    task_type: str = ""
    priority: int = 0
    estimated_duration: float = 0.0
    dependencies: List[str] = field(default_factory=list)


@dataclass
class TaskSequence:
    """任务序列"""
    locations: List[TaskLocation]
    total_distance: float = 0.0
    total_time: float = 0.0
    optimization_method: str = ""
    improvement_ratio: float = 0.0  # 相比原始顺序的改进比例
    
    def get_order(self) -> List[str]:
        """获取任务 ID 顺序"""
        return [loc.task_id for loc in self.locations]
    
    def get_zone_order(self) -> List[str]:
        """获取区域顺序"""
        return [loc.zone for loc in self.locations]
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "locations": [
                {
                    "task_id": loc.task_id,
                    "zone": loc.zone,
                    "position": (loc.x, loc.y),
                    "task_type": loc.task_type,
                }
                for loc in self.locations
            ],
            "total_distance": self.total_distance,
            "total_time": self.total_time,
            "optimization_method": self.optimization_method,
            "improvement_ratio": self.improvement_ratio,
            "order": self.get_order(),
        }


class TSPSolver(ABC):
    """TSP 求解器基类"""
    
    @abstractmethod
    def solve(
        self,
        locations: List[TaskLocation],
        start: Optional[Location] = None,
        end: Optional[Location] = None,
    ) -> TaskSequence:
        """求解 TSP 问题"""
        pass
    
    @staticmethod
    def calculate_total_distance(
        sequence: List[TaskLocation],
        start: Optional[Location] = None,
        end: Optional[Location] = None,
    ) -> float:
        """计算序列总距离"""
        total = 0.0
        
        if start and sequence:
            total += start.distance_to(sequence[0])
        
        for i in range(len(sequence) - 1):
            total += sequence[i].distance_to(sequence[i + 1])
        
        if end and sequence:
            total += sequence[-1].distance_to(end)
        
        return total


class NearestNeighborSolver(TSPSolver):
    """最近邻启发式求解器"""
    
    def solve(
        self,
        locations: List[TaskLocation],
        start: Optional[Location] = None,
        end: Optional[Location] = None,
    ) -> TaskSequence:
        """最近邻启发式求解"""
        if not locations:
            return TaskSequence(locations=[], optimization_method="nearest_neighbor")
        
        remaining = list(locations)
        sequence = []
        current = start if start else remaining.pop(0)
        
        if start is None and remaining:
            sequence.append(current)
        
        while remaining:
            # 找最近的点
            nearest = min(remaining, key=lambda l: current.distance_to(l))
            sequence.append(nearest)
            remaining.remove(nearest)
            current = nearest
        
        total_distance = self.calculate_total_distance(sequence, start, end)
        
        return TaskSequence(
            locations=sequence,
            total_distance=total_distance,
            optimization_method="nearest_neighbor",
        )


class TwoOptSolver(TSPSolver):
    """2-opt 局部搜索求解器"""
    
    def __init__(self, max_iterations: int = 1000):
        """初始化"""
        self.max_iterations = max_iterations
    
    def solve(
        self,
        locations: List[TaskLocation],
        start: Optional[Location] = None,
        end: Optional[Location] = None,
    ) -> TaskSequence:
        """2-opt 局部搜索求解"""
        if len(locations) <= 2:
            total_distance = self.calculate_total_distance(locations, start, end)
            return TaskSequence(
                locations=locations,
                total_distance=total_distance,
                optimization_method="two_opt",
            )
        
        # 初始解（使用最近邻）
        nn_solver = NearestNeighborSolver()
        current_sequence = nn_solver.solve(locations, start, end).locations
        
        current_distance = self.calculate_total_distance(current_sequence, start, end)
        improved = True
        iterations = 0
        
        while improved and iterations < self.max_iterations:
            improved = False
            iterations += 1
            
            for i in range(len(current_sequence) - 1):
                for j in range(i + 2, len(current_sequence)):
                    # 尝试 2-opt 交换
                    new_sequence = (
                        current_sequence[:i + 1] +
                        current_sequence[i + 1:j + 1][::-1] +
                        current_sequence[j + 1:]
                    )
                    new_distance = self.calculate_total_distance(new_sequence, start, end)
                    
                    if new_distance < current_distance:
                        current_sequence = new_sequence
                        current_distance = new_distance
                        improved = True
        
        return TaskSequence(
            locations=current_sequence,
            total_distance=current_distance,
            optimization_method="two_opt",
        )


class SimulatedAnnealingSolver(TSPSolver):
    """模拟退火求解器"""
    
    def __init__(
        self,
        initial_temp: float = 10000.0,
        cooling_rate: float = 0.995,
        min_temp: float = 1.0,
        iterations_per_temp: int = 100,
    ):
        """初始化"""
        self.initial_temp = initial_temp
        self.cooling_rate = cooling_rate
        self.min_temp = min_temp
        self.iterations_per_temp = iterations_per_temp
    
    def solve(
        self,
        locations: List[TaskLocation],
        start: Optional[Location] = None,
        end: Optional[Location] = None,
    ) -> TaskSequence:
        """模拟退火求解"""
        if len(locations) <= 2:
            total_distance = self.calculate_total_distance(locations, start, end)
            return TaskSequence(
                locations=locations,
                total_distance=total_distance,
                optimization_method="simulated_annealing",
            )
        
        # 初始解
        current = list(locations)
        random.shuffle(current)
        current_distance = self.calculate_total_distance(current, start, end)
        
        best = current[:]
        best_distance = current_distance
        
        temp = self.initial_temp
        
        while temp > self.min_temp:
            for _ in range(self.iterations_per_temp):
                # 随机交换两个位置
                i, j = random.sample(range(len(current)), 2)
                new = current[:]
                new[i], new[j] = new[j], new[i]
                new_distance = self.calculate_total_distance(new, start, end)
                
                # 接受准则
                delta = new_distance - current_distance
                if delta < 0 or random.random() < math.exp(-delta / temp):
                    current = new
                    current_distance = new_distance
                    
                    if current_distance < best_distance:
                        best = current[:]
                        best_distance = current_distance
            
            temp *= self.cooling_rate
        
        return TaskSequence(
            locations=best,
            total_distance=best_distance,
            optimization_method="simulated_annealing",
        )


class PathOptimizer:
    """路径优化器"""
    
    SOLVER_MAP = {
        OptimizationMethod.NEAREST_NEIGHBOR: NearestNeighborSolver,
        OptimizationMethod.TWO_OPT: TwoOptSolver,
        OptimizationMethod.SIMULATED_ANNEALING: SimulatedAnnealingSolver,
    }
    
    def __init__(
        self,
        method: OptimizationMethod = OptimizationMethod.TWO_OPT,
        distance_matrix: Optional[Dict[str, Dict[str, float]]] = None,
    ):
        """
        初始化路径优化器
        
        Args:
            method: 优化方法
            distance_matrix: 预计算的距离矩阵（可选）
        """
        self.method = method
        self.distance_matrix = distance_matrix or {}
        self.solver = self.SOLVER_MAP.get(method, TwoOptSolver)()
    
    def set_distance_matrix(self, matrix: Dict[str, Dict[str, float]]) -> None:
        """设置距离矩阵"""
        self.distance_matrix = matrix
    
    def get_distance(self, from_id: str, to_id: str) -> float:
        """获取两点间距离"""
        if from_id in self.distance_matrix and to_id in self.distance_matrix[from_id]:
            return self.distance_matrix[from_id][to_id]
        return 0.0
    
    def optimize(
        self,
        tasks: List[TaskLocation],
        start: Optional[Location] = None,
        end: Optional[Location] = None,
        respect_dependencies: bool = True,
    ) -> TaskSequence:
        """
        优化任务访问顺序
        
        Args:
            tasks: 任务位置列表
            start: 起始位置
            end: 结束位置
            respect_dependencies: 是否尊重任务依赖关系
        
        Returns:
            优化后的任务序列
        """
        if not tasks:
            return TaskSequence(locations=[], optimization_method=self.method.value)
        
        # 处理依赖关系
        if respect_dependencies:
            tasks = self._topological_sort(tasks)
        
        # 计算原始距离
        original_distance = TSPSolver.calculate_total_distance(tasks, start, end)
        
        # 求解优化序列
        result = self.solver.solve(tasks, start, end)
        
        # 计算改进比例
        if original_distance > 0:
            result.improvement_ratio = 1 - result.total_distance / original_distance
        
        return result
    
    def _topological_sort(self, tasks: List[TaskLocation]) -> List[TaskLocation]:
        """拓扑排序（处理依赖关系）"""
        # 构建依赖图
        task_map = {t.task_id: t for t in tasks}
        in_degree = {t.task_id: 0 for t in tasks}
        
        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id in task_map:
                    in_degree[task.task_id] += 1
        
        # Kahn 算法
        queue = [t for t in tasks if in_degree[t.task_id] == 0]
        result = []
        
        while queue:
            # 按优先级排序队列
            queue.sort(key=lambda t: -t.priority)
            current = queue.pop(0)
            result.append(current)
            
            for task in tasks:
                if current.task_id in task.dependencies:
                    in_degree[task.task_id] -= 1
                    if in_degree[task.task_id] == 0:
                        queue.append(task)
        
        return result
    
    def optimize_batch_transport(
        self,
        pickup_tasks: List[TaskLocation],
        delivery_tasks: List[TaskLocation],
        capacity: int = 2,
    ) -> List[TaskSequence]:
        """
        优化批量运输
        
        Args:
            pickup_tasks: 取货任务列表
            delivery_tasks: 送货任务列表
            capacity: 每次最大携带数量
        
        Returns:
            分批后的任务序列列表
        """
        sequences = []
        
        # 按容量分批
        for i in range(0, len(pickup_tasks), capacity):
            batch_pickup = pickup_tasks[i:i + capacity]
            batch_delivery = delivery_tasks[i:i + capacity]
            
            # 优化取货顺序
            pickup_seq = self.optimize(batch_pickup, respect_dependencies=False)
            
            # 优化送货顺序
            if batch_delivery:
                delivery_seq = self.optimize(
                    batch_delivery,
                    start=batch_pickup[-1] if batch_pickup else None,
                    respect_dependencies=False
                )
                # 合并序列
                combined = TaskSequence(
                    locations=pickup_seq.locations + delivery_seq.locations,
                    total_distance=pickup_seq.total_distance + delivery_seq.total_distance,
                    optimization_method=f"{self.method.value}_batch",
                )
                sequences.append(combined)
            else:
                sequences.append(pickup_seq)
        
        return sequences
    
    def calculate_savings(
        self,
        original_sequence: List[TaskLocation],
        optimized_sequence: TaskSequence,
    ) -> Dict:
        """计算优化节省"""
        original_distance = TSPSolver.calculate_total_distance(original_sequence)
        
        return {
            "original_distance": original_distance,
            "optimized_distance": optimized_sequence.total_distance,
            "distance_saved": original_distance - optimized_sequence.total_distance,
            "percentage_saved": (
                (original_distance - optimized_sequence.total_distance) / original_distance * 100
                if original_distance > 0 else 0
            ),
            "original_order": [t.task_id for t in original_sequence],
            "optimized_order": optimized_sequence.get_order(),
        }


def optimize_task_order(
    tasks: List[Dict],
    method: OptimizationMethod = OptimizationMethod.TWO_OPT,
) -> TaskSequence:
    """
    优化任务顺序的便捷函数
    
    Args:
        tasks: 任务字典列表，每个字典包含 id, x, y, zone 等字段
        method: 优化方法
    
    Returns:
        优化后的任务序列
    """
    task_locations = [
        TaskLocation(
            id=t.get("id", str(i)),
            x=t.get("x", 0),
            y=t.get("y", 0),
            zone=t.get("zone", ""),
            task_id=t.get("id", str(i)),
            task_type=t.get("type", ""),
            priority=t.get("priority", 0),
        )
        for i, t in enumerate(tasks)
    ]
    
    optimizer = PathOptimizer(method=method)
    return optimizer.optimize(task_locations)
