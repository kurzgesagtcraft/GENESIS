"""
GENESIS 技能策略优化模块

基于历史执行数据优化技能参数，
特别是抓取参数调优，提高操作成功率。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Callable
from enum import Enum
import math
import json
from pathlib import Path


class OptimizationStrategy(Enum):
    """优化策略"""
    BAYESIAN = "bayesian"           # 贝叶斯优化
    GRID_SEARCH = "grid_search"     # 网格搜索
    RANDOM_SEARCH = "random_search" # 随机搜索
    GRADIENT = "gradient"           # 梯度下降
    EVOLUTIONARY = "evolutionary"   # 进化算法


class SkillType(Enum):
    """技能类型"""
    TOP_GRASP = "top_grasp"
    SIDE_GRASP = "side_grasp"
    PLACE = "place"
    FEED_STATION = "feed_station"
    RETRIEVE_STATION = "retrieve_station"
    CHARGE = "charge"
    WAREHOUSE = "warehouse"


@dataclass
class GraspParams:
    """抓取参数"""
    # 接近参数
    approach_height: float = 0.15       # 接近高度 (m)
    approach_speed: float = 0.1         # 接近速度 (m/s)
    
    # 抓取参数
    grasp_width: float = 0.08           # 抓取宽度 (m)
    grasp_force: float = 30.0           # 抓取力 (N)
    grasp_duration: float = 1.0         # 抓取持续时间 (s)
    
    # 提起参数
    lift_height: float = 0.15           # 提起高度 (m)
    lift_speed: float = 0.05            # 提起速度 (m/s)
    
    # 重试参数
    max_retries: int = 3                # 最大重试次数
    retry_offset: float = 0.01          # 重试偏移量 (m)
    
    # 物体类型特定参数
    object_type: str = ""               # 物体类型
    object_size: Tuple[float, float, float] = (0.1, 0.1, 0.1)  # 物体尺寸
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "approach_height": self.approach_height,
            "approach_speed": self.approach_speed,
            "grasp_width": self.grasp_width,
            "grasp_force": self.grasp_force,
            "grasp_duration": self.grasp_duration,
            "lift_height": self.lift_height,
            "lift_speed": self.lift_speed,
            "max_retries": self.max_retries,
            "retry_offset": self.retry_offset,
            "object_type": self.object_type,
            "object_size": self.object_size,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "GraspParams":
        """从字典创建"""
        return cls(
            approach_height=data.get("approach_height", 0.15),
            approach_speed=data.get("approach_speed", 0.1),
            grasp_width=data.get("grasp_width", 0.08),
            grasp_force=data.get("grasp_force", 30.0),
            grasp_duration=data.get("grasp_duration", 1.0),
            lift_height=data.get("lift_height", 0.15),
            lift_speed=data.get("lift_speed", 0.05),
            max_retries=data.get("max_retries", 3),
            retry_offset=data.get("retry_offset", 0.01),
            object_type=data.get("object_type", ""),
            object_size=tuple(data.get("object_size", (0.1, 0.1, 0.1))),
        )


@dataclass
class ExecutionRecord:
    """执行记录"""
    timestamp: float
    skill_type: SkillType
    params: Dict
    success: bool
    execution_time: float
    failure_reason: str = ""
    context: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "skill_type": self.skill_type.value,
            "params": self.params,
            "success": self.success,
            "execution_time": self.execution_time,
            "failure_reason": self.failure_reason,
            "context": self.context,
        }


@dataclass
class OptimizationResult:
    """优化结果"""
    skill_type: SkillType
    best_params: Dict
    original_params: Dict
    success_rate_before: float
    success_rate_after: float
    improvement: float
    confidence: float
    optimization_method: str
    iterations: int
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "skill_type": self.skill_type.value,
            "best_params": self.best_params,
            "original_params": self.original_params,
            "success_rate_before": self.success_rate_before,
            "success_rate_after": self.success_rate_after,
            "improvement": self.improvement,
            "confidence": self.confidence,
            "optimization_method": self.optimization_method,
            "iterations": self.iterations,
            "recommendations": self.recommendations,
        }


class SkillOptimizer:
    """技能优化器"""
    
    # 物体类型默认参数
    OBJECT_DEFAULT_PARAMS = {
        "iron_ore": {
            "grasp_width": 0.10,
            "grasp_force": 40.0,
            "approach_height": 0.12,
        },
        "silicon_ore": {
            "grasp_width": 0.08,
            "grasp_force": 35.0,
            "approach_height": 0.12,
        },
        "iron_bar": {
            "grasp_width": 0.05,
            "grasp_force": 25.0,
            "approach_height": 0.15,
        },
        "circuit_board": {
            "grasp_width": 0.10,
            "grasp_force": 20.0,
            "approach_height": 0.10,
        },
        "motor": {
            "grasp_width": 0.06,
            "grasp_force": 35.0,
            "approach_height": 0.12,
        },
        "joint_module": {
            "grasp_width": 0.08,
            "grasp_force": 30.0,
            "approach_height": 0.12,
        },
        "frame_segment": {
            "grasp_width": 0.06,
            "grasp_force": 40.0,
            "approach_height": 0.15,
        },
        "controller_board": {
            "grasp_width": 0.12,
            "grasp_force": 20.0,
            "approach_height": 0.10,
        },
    }
    
    # 参数搜索范围
    PARAM_RANGES = {
        "approach_height": (0.08, 0.20),
        "approach_speed": (0.05, 0.15),
        "grasp_width": (0.04, 0.12),
        "grasp_force": (15.0, 50.0),
        "grasp_duration": (0.5, 2.0),
        "lift_height": (0.10, 0.20),
        "lift_speed": (0.03, 0.10),
    }
    
    def __init__(
        self,
        strategy: OptimizationStrategy = OptimizationStrategy.GRID_SEARCH,
        min_samples: int = 10,
    ):
        """
        初始化技能优化器
        
        Args:
            strategy: 优化策略
            min_samples: 最小样本数
        """
        self.strategy = strategy
        self.min_samples = min_samples
        self.execution_records: List[ExecutionRecord] = []
        self.optimized_params: Dict[str, GraspParams] = {}
        
    def add_execution_record(self, record: ExecutionRecord) -> None:
        """添加执行记录"""
        self.execution_records.append(record)
    
    def record_execution(
        self,
        skill_type: SkillType,
        params: Dict,
        success: bool,
        execution_time: float,
        failure_reason: str = "",
        context: Optional[Dict] = None,
    ) -> None:
        """记录执行结果"""
        import time
        record = ExecutionRecord(
            timestamp=time.time(),
            skill_type=skill_type,
            params=params,
            success=success,
            execution_time=execution_time,
            failure_reason=failure_reason,
            context=context or {},
        )
        self.add_execution_record(record)
    
    def get_object_params(self, object_type: str) -> GraspParams:
        """获取物体类型的默认参数"""
        base_params = GraspParams(object_type=object_type)
        
        if object_type in self.OBJECT_DEFAULT_PARAMS:
            object_params = self.OBJECT_DEFAULT_PARAMS[object_type]
            for key, value in object_params.items():
                if hasattr(base_params, key):
                    setattr(base_params, key, value)
        
        return base_params
    
    def analyze_failures(self, skill_type: SkillType) -> Dict:
        """分析失败模式"""
        failures = [
            r for r in self.execution_records
            if r.skill_type == skill_type and not r.success
        ]
        
        if not failures:
            return {"failure_count": 0, "patterns": []}
        
        # 统计失败原因
        failure_reasons = {}
        for f in failures:
            reason = f.failure_reason or "unknown"
            if reason not in failure_reasons:
                failure_reasons[reason] = 0
            failure_reasons[reason] += 1
        
        # 分析参数分布
        param_analysis = {}
        for param in self.PARAM_RANGES.keys():
            values = [f.params.get(param, 0) for f in failures if param in f.params]
            if values:
                param_analysis[param] = {
                    "mean": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }
        
        return {
            "failure_count": len(failures),
            "failure_reasons": failure_reasons,
            "param_analysis": param_analysis,
            "patterns": self._identify_failure_patterns(failures),
        }
    
    def _identify_failure_patterns(self, failures: List[ExecutionRecord]) -> List[str]:
        """识别失败模式"""
        patterns = []
        
        # 检查参数相关性
        for param in ["grasp_force", "grasp_width", "approach_height"]:
            values = [f.params.get(param, 0) for f in failures]
            if not values:
                continue
            
            min_val, max_val = self.PARAM_RANGES.get(param, (0, 1))
            mean_val = sum(values) / len(values)
            
            if mean_val < min_val + (max_val - min_val) * 0.25:
                patterns.append(f"{param} 可能过低")
            elif mean_val > min_val + (max_val - min_val) * 0.75:
                patterns.append(f"{param} 可能过高")
        
        return patterns
    
    def optimize(
        self,
        skill_type: SkillType,
        object_type: Optional[str] = None,
    ) -> OptimizationResult:
        """优化技能参数"""
        # 获取相关记录
        records = [
            r for r in self.execution_records
            if r.skill_type == skill_type
        ]
        
        if len(records) < self.min_samples:
            # 样本不足，返回默认参数
            default_params = self.get_object_params(object_type or "")
            return OptimizationResult(
                skill_type=skill_type,
                best_params=default_params.to_dict(),
                original_params={},
                success_rate_before=0.0,
                success_rate_after=0.0,
                improvement=0.0,
                confidence=0.0,
                optimization_method="default",
                iterations=0,
                recommendations=["样本数不足，使用默认参数"],
            )
        
        # 计算原始成功率
        original_success_rate = sum(1 for r in records if r.success) / len(records)
        
        # 根据策略选择优化方法
        if self.strategy == OptimizationStrategy.GRID_SEARCH:
            best_params, iterations = self._grid_search_optimize(records)
        elif self.strategy == OptimizationStrategy.RANDOM_SEARCH:
            best_params, iterations = self._random_search_optimize(records)
        else:
            best_params, iterations = self._bayesian_optimize(records)
        
        # 计算优化后预期成功率
        optimized_success_rate = self._estimate_success_rate(records, best_params)
        
        # 生成建议
        recommendations = self._generate_recommendations(
            records, best_params, original_success_rate, optimized_success_rate
        )
        
        return OptimizationResult(
            skill_type=skill_type,
            best_params=best_params,
            original_params=records[0].params if records else {},
            success_rate_before=original_success_rate,
            success_rate_after=optimized_success_rate,
            improvement=optimized_success_rate - original_success_rate,
            confidence=min(1.0, len(records) / 100),
            optimization_method=self.strategy.value,
            iterations=iterations,
            recommendations=recommendations,
        )
    
    def _grid_search_optimize(
        self,
        records: List[ExecutionRecord],
    ) -> Tuple[Dict, int]:
        """网格搜索优化"""
        best_params = {}
        best_score = 0.0
        iterations = 0
        
        # 简化：只优化关键参数
        key_params = ["grasp_force", "grasp_width", "approach_height"]
        
        for param in key_params:
            min_val, max_val = self.PARAM_RANGES.get(param, (0, 1))
            step = (max_val - min_val) / 5
            
            for value in [min_val + step * i for i in range(6)]:
                test_params = {param: value}
                score = self._estimate_success_rate(records, test_params)
                iterations += 1
                
                if score > best_score:
                    best_score = score
                    best_params[param] = value
        
        # 填充其他参数
        for param, (min_val, max_val) in self.PARAM_RANGES.items():
            if param not in best_params:
                best_params[param] = (min_val + max_val) / 2
        
        return best_params, iterations
    
    def _random_search_optimize(
        self,
        records: List[ExecutionRecord],
        n_iterations: int = 50,
    ) -> Tuple[Dict, int]:
        """随机搜索优化"""
        import random
        
        best_params = {}
        best_score = 0.0
        
        for _ in range(n_iterations):
            test_params = {}
            for param, (min_val, max_val) in self.PARAM_RANGES.items():
                test_params[param] = min_val + random.random() * (max_val - min_val)
            
            score = self._estimate_success_rate(records, test_params)
            
            if score > best_score:
                best_score = score
                best_params = test_params
        
        return best_params, n_iterations
    
    def _bayesian_optimize(
        self,
        records: List[ExecutionRecord],
    ) -> Tuple[Dict, int]:
        """贝叶斯优化（简化版）"""
        # 简化实现：使用随机搜索作为近似
        return self._random_search_optimize(records, n_iterations=30)
    
    def _estimate_success_rate(
        self,
        records: List[ExecutionRecord],
        params: Dict,
    ) -> float:
        """估计参数的成功率"""
        # 简化：基于参数相似度加权计算成功率
        total_weight = 0.0
        weighted_success = 0.0
        
        for record in records:
            # 计算参数相似度
            similarity = self._calculate_param_similarity(record.params, params)
            weight = similarity ** 2  # 平方强调相似性
            
            total_weight += weight
            weighted_success += weight * (1.0 if record.success else 0.0)
        
        return weighted_success / total_weight if total_weight > 0 else 0.5
    
    def _calculate_param_similarity(self, params1: Dict, params2: Dict) -> float:
        """计算参数相似度"""
        common_keys = set(params1.keys()) & set(params2.keys())
        if not common_keys:
            return 0.0
        
        total_diff = 0.0
        for key in common_keys:
            if key not in self.PARAM_RANGES:
                continue
            
            min_val, max_val = self.PARAM_RANGES[key]
            range_val = max_val - min_val
            
            if range_val > 0:
                diff = abs(params1.get(key, 0) - params2.get(key, 0)) / range_val
                total_diff += diff ** 2
        
        return math.exp(-total_diff) if total_diff > 0 else 1.0
    
    def _generate_recommendations(
        self,
        records: List[ExecutionRecord],
        best_params: Dict,
        original_rate: float,
        optimized_rate: float,
    ) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if optimized_rate > original_rate + 0.05:
            recommendations.append(
                f"参数优化可提升成功率 {original_rate:.1%} → {optimized_rate:.1%}"
            )
        
        # 分析关键参数变化
        if records:
            original = records[0].params
            
            for param in ["grasp_force", "grasp_width", "approach_height"]:
                if param in best_params and param in original:
                    change = best_params[param] - original.get(param, 0)
                    if abs(change) > 0.01:
                        direction = "增加" if change > 0 else "减少"
                        recommendations.append(
                            f"建议{direction} {param}: "
                            f"{original.get(param, 0):.2f} → {best_params[param]:.2f}"
                        )
        
        # 失败分析建议
        failure_analysis = self.analyze_failures(records[0].skill_type if records else SkillType.TOP_GRASP)
        for pattern in failure_analysis.get("patterns", []):
            recommendations.append(f"发现失败模式: {pattern}")
        
        return recommendations
    
    def save_optimized_params(self, filepath: str) -> None:
        """保存优化参数"""
        data = {
            k: v.to_dict() for k, v in self.optimized_params.items()
        }
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_optimized_params(self, filepath: str) -> None:
        """加载优化参数"""
        path = Path(filepath)
        if not path.exists():
            return
        
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.optimized_params = {
            k: GraspParams.from_dict(v) for k, v in data.items()
        }
    
    def clear(self) -> None:
        """清空记录"""
        self.execution_records.clear()


def optimize_grasp_params(
    execution_history: List[Dict],
    object_type: str = "",
) -> OptimizationResult:
    """
    优化抓取参数的便捷函数
    
    Args:
        execution_history: 执行历史记录列表
        object_type: 物体类型
    
    Returns:
        优化结果
    """
    optimizer = SkillOptimizer()
    
    for record in execution_history:
        optimizer.record_execution(
            skill_type=SkillType(record.get("skill_type", "top_grasp")),
            params=record.get("params", {}),
            success=record.get("success", False),
            execution_time=record.get("execution_time", 0),
            failure_reason=record.get("failure_reason", ""),
        )
    
    return optimizer.optimize(SkillType.TOP_GRASP, object_type)
