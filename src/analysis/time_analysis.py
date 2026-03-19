"""
GENESIS 时间分析模块

分析系统运行日志，统计各任务类型的时间占比，
识别性能瓶颈，生成时间分析报告。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import math
from datetime import datetime
from pathlib import Path


class TaskCategory(Enum):
    """任务类别枚举"""
    NAVIGATION = "navigation"       # 移动时间
    MANIPULATION = "manipulation"   # 操作时间
    WAITING = "waiting"             # 等待时间
    CHARGING = "charging"           # 充电时间
    PERCEPTION = "perception"       # 感知时间
    PLANNING = "planning"           # 规划时间
    IDLE = "idle"                   # 空闲时间
    UNKNOWN = "unknown"             # 未知时间


@dataclass
class TaskTimeStats:
    """单个任务时间统计"""
    task_id: str
    task_type: str
    category: TaskCategory
    start_time: float
    end_time: float
    duration: float
    success: bool
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "category": self.category.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "success": self.success,
            "metadata": self.metadata,
        }


@dataclass
class TimeBreakdown:
    """时间分解统计"""
    total_time: float = 0.0
    navigation_time: float = 0.0
    manipulation_time: float = 0.0
    waiting_time: float = 0.0
    charging_time: float = 0.0
    perception_time: float = 0.0
    planning_time: float = 0.0
    idle_time: float = 0.0
    unknown_time: float = 0.0
    
    # 详细统计
    task_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    # 各类型任务统计
    task_type_durations: Dict[str, float] = field(default_factory=dict)
    task_type_counts: Dict[str, int] = field(default_factory=dict)
    
    @property
    def navigation_ratio(self) -> float:
        """移动时间占比"""
        return self.navigation_time / self.total_time if self.total_time > 0 else 0.0
    
    @property
    def manipulation_ratio(self) -> float:
        """操作时间占比"""
        return self.manipulation_time / self.total_time if self.total_time > 0 else 0.0
    
    @property
    def waiting_ratio(self) -> float:
        """等待时间占比"""
        return self.waiting_time / self.total_time if self.total_time > 0 else 0.0
    
    @property
    def charging_ratio(self) -> float:
        """充电时间占比"""
        return self.charging_time / self.total_time if self.total_time > 0 else 0.0
    
    @property
    def success_rate(self) -> float:
        """任务成功率"""
        return self.success_count / self.task_count if self.task_count > 0 else 0.0
    
    @property
    def productive_ratio(self) -> float:
        """有效工作时间占比（移动+操作+感知+规划）"""
        productive = (self.navigation_time + self.manipulation_time + 
                      self.perception_time + self.planning_time)
        return productive / self.total_time if self.total_time > 0 else 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_time": self.total_time,
            "navigation_time": self.navigation_time,
            "manipulation_time": self.manipulation_time,
            "waiting_time": self.waiting_time,
            "charging_time": self.charging_time,
            "perception_time": self.perception_time,
            "planning_time": self.planning_time,
            "idle_time": self.idle_time,
            "unknown_time": self.unknown_time,
            "navigation_ratio": self.navigation_ratio,
            "manipulation_ratio": self.manipulation_ratio,
            "waiting_ratio": self.waiting_ratio,
            "charging_ratio": self.charging_ratio,
            "productive_ratio": self.productive_ratio,
            "task_count": self.task_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "task_type_durations": self.task_type_durations,
            "task_type_counts": self.task_type_counts,
        }


@dataclass
class BottleneckInfo:
    """瓶颈信息"""
    category: TaskCategory
    time_ratio: float
    avg_duration: float
    count: int
    impact_score: float  # 影响分数 (0-1)
    suggestions: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "category": self.category.value,
            "time_ratio": self.time_ratio,
            "avg_duration": self.avg_duration,
            "count": self.count,
            "impact_score": self.impact_score,
            "suggestions": self.suggestions,
        }


class TimeAnalyzer:
    """时间分析器"""
    
    # 任务类型到类别的映射
    TASK_CATEGORY_MAP = {
        # 导航类
        "navigate_to_zone": TaskCategory.NAVIGATION,
        "navigate_to_position": TaskCategory.NAVIGATION,
        "navigation": TaskCategory.NAVIGATION,
        "move_to": TaskCategory.NAVIGATION,
        # 操作类
        "grasp": TaskCategory.MANIPULATION,
        "top_grasp": TaskCategory.MANIPULATION,
        "side_grasp": TaskCategory.MANIPULATION,
        "place": TaskCategory.MANIPULATION,
        "feed_station": TaskCategory.MANIPULATION,
        "retrieve_station": TaskCategory.MANIPULATION,
        "pick": TaskCategory.MANIPULATION,
        "insert": TaskCategory.MANIPULATION,
        "assembly": TaskCategory.MANIPULATION,
        # 等待类
        "wait": TaskCategory.WAITING,
        "wait_for_station": TaskCategory.WAITING,
        "wait_for_processing": TaskCategory.WAITING,
        # 充电类
        "charge": TaskCategory.CHARGING,
        "charging": TaskCategory.CHARGING,
        "dock": TaskCategory.CHARGING,
        # 感知类
        "perceive": TaskCategory.PERCEPTION,
        "detect": TaskCategory.PERCEPTION,
        "localize": TaskCategory.PERCEPTION,
        "scan": TaskCategory.PERCEPTION,
        # 规划类
        "plan": TaskCategory.PLANNING,
        "replan": TaskCategory.PLANNING,
        "generate_plan": TaskCategory.PLANNING,
        # 其他
        "idle": TaskCategory.IDLE,
        "unknown": TaskCategory.UNKNOWN,
    }
    
    def __init__(self):
        """初始化时间分析器"""
        self.task_records: List[TaskTimeStats] = []
        self.breakdown = TimeBreakdown()
        self.bottlenecks: List[BottleneckInfo] = []
        
    def _categorize_task(self, task_type: str) -> TaskCategory:
        """将任务类型映射到类别"""
        task_type_lower = task_type.lower()
        
        # 直接匹配
        if task_type_lower in self.TASK_CATEGORY_MAP:
            return self.TASK_CATEGORY_MAP[task_type_lower]
        
        # 模糊匹配
        for key, category in self.TASK_CATEGORY_MAP.items():
            if key in task_type_lower or task_type_lower in key:
                return category
        
        return TaskCategory.UNKNOWN
    
    def add_task_record(self, record: TaskTimeStats) -> None:
        """添加任务记录"""
        self.task_records.append(record)
        
    def add_task(
        self,
        task_id: str,
        task_type: str,
        start_time: float,
        end_time: float,
        success: bool = True,
        metadata: Optional[Dict] = None,
    ) -> None:
        """添加任务记录（简化接口）"""
        category = self._categorize_task(task_type)
        duration = end_time - start_time
        
        record = TaskTimeStats(
            task_id=task_id,
            task_type=task_type,
            category=category,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            success=success,
            metadata=metadata or {},
        )
        self.add_task_record(record)
    
    def analyze(self) -> TimeBreakdown:
        """分析所有任务记录"""
        self.breakdown = TimeBreakdown()
        
        if not self.task_records:
            return self.breakdown
        
        # 统计各类时间
        for record in self.task_records:
            self.breakdown.task_count += 1
            
            if record.success:
                self.breakdown.success_count += 1
            else:
                self.breakdown.failure_count += 1
            
            # 按类别累加时间
            duration = record.duration
            if record.category == TaskCategory.NAVIGATION:
                self.breakdown.navigation_time += duration
            elif record.category == TaskCategory.MANIPULATION:
                self.breakdown.manipulation_time += duration
            elif record.category == TaskCategory.WAITING:
                self.breakdown.waiting_time += duration
            elif record.category == TaskCategory.CHARGING:
                self.breakdown.charging_time += duration
            elif record.category == TaskCategory.PERCEPTION:
                self.breakdown.perception_time += duration
            elif record.category == TaskCategory.PLANNING:
                self.breakdown.planning_time += duration
            elif record.category == TaskCategory.IDLE:
                self.breakdown.idle_time += duration
            else:
                self.breakdown.unknown_time += duration
            
            # 按任务类型统计
            if record.task_type not in self.breakdown.task_type_durations:
                self.breakdown.task_type_durations[record.task_type] = 0.0
                self.breakdown.task_type_counts[record.task_type] = 0
            self.breakdown.task_type_durations[record.task_type] += duration
            self.breakdown.task_type_counts[record.task_type] += 1
        
        # 计算总时间
        self.breakdown.total_time = (
            self.breakdown.navigation_time +
            self.breakdown.manipulation_time +
            self.breakdown.waiting_time +
            self.breakdown.charging_time +
            self.breakdown.perception_time +
            self.breakdown.planning_time +
            self.breakdown.idle_time +
            self.breakdown.unknown_time
        )
        
        return self.breakdown
    
    def identify_bottlenecks(self) -> List[BottleneckInfo]:
        """识别性能瓶颈"""
        self.bottlenecks = []
        
        if self.breakdown.total_time == 0:
            return self.bottlenecks
        
        # 按类别统计
        category_stats = {
            TaskCategory.NAVIGATION: (self.breakdown.navigation_time, 
                                       self.breakdown.task_type_counts.get("navigate_to_zone", 0) +
                                       self.breakdown.task_type_counts.get("navigate_to_position", 0)),
            TaskCategory.MANIPULATION: (self.breakdown.manipulation_time,
                                         sum(v for k, v in self.breakdown.task_type_counts.items()
                                             if k in ["grasp", "top_grasp", "side_grasp", "place", 
                                                     "feed_station", "retrieve_station"])),
            TaskCategory.WAITING: (self.breakdown.waiting_time,
                                    self.breakdown.task_type_counts.get("wait", 0) +
                                    self.breakdown.task_type_counts.get("wait_for_station", 0)),
            TaskCategory.CHARGING: (self.breakdown.charging_time,
                                     self.breakdown.task_type_counts.get("charge", 0)),
        }
        
        for category, (total_duration, count) in category_stats.items():
            if total_duration > 0:
                ratio = total_duration / self.breakdown.total_time
                avg_duration = total_duration / count if count > 0 else 0
                
                # 计算影响分数 (基于占比和频率)
                impact_score = ratio * (1 + math.log10(max(1, count)) / 10)
                impact_score = min(1.0, impact_score)
                
                # 生成优化建议
                suggestions = self._generate_suggestions(category, ratio, avg_duration, count)
                
                bottleneck = BottleneckInfo(
                    category=category,
                    time_ratio=ratio,
                    avg_duration=avg_duration,
                    count=count,
                    impact_score=impact_score,
                    suggestions=suggestions,
                )
                self.bottlenecks.append(bottleneck)
        
        # 按影响分数排序
        self.bottlenecks.sort(key=lambda x: x.impact_score, reverse=True)
        
        return self.bottlenecks
    
    def _generate_suggestions(
        self,
        category: TaskCategory,
        ratio: float,
        avg_duration: float,
        count: int,
    ) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        if category == TaskCategory.NAVIGATION:
            if ratio > 0.4:
                suggestions.append("导航时间占比过高，考虑优化路径规划")
                suggestions.append("使用 TSP 算法优化任务访问顺序")
            if avg_duration > 30:
                suggestions.append("单次导航时间较长，检查路径是否绕行")
            if count > 50:
                suggestions.append("导航次数过多，考虑批量运输减少往返")
                
        elif category == TaskCategory.MANIPULATION:
            if ratio > 0.3:
                suggestions.append("操作时间占比较高，属于正常范围")
            if avg_duration > 10:
                suggestions.append("单次操作时间较长，检查是否需要优化动作轨迹")
                
        elif category == TaskCategory.WAITING:
            if ratio > 0.2:
                suggestions.append("等待时间占比过高，考虑并行执行其他任务")
                suggestions.append("在工站加工期间执行采矿或运输任务")
            if avg_duration > 20:
                suggestions.append("单次等待时间较长，检查工站处理效率")
                
        elif category == TaskCategory.CHARGING:
            if ratio > 0.15:
                suggestions.append("充电时间占比较高，考虑智能充电调度")
                suggestions.append("在任务间隙预充电，避免低电量才充电")
            if count > 10:
                suggestions.append("充电次数较多，考虑增加电池容量或优化能耗")
        
        return suggestions
    
    def get_report(self) -> Dict:
        """生成完整分析报告"""
        self.analyze()
        self.identify_bottlenecks()
        
        return {
            "summary": {
                "total_time": self.breakdown.total_time,
                "task_count": self.breakdown.task_count,
                "success_rate": self.breakdown.success_rate,
                "productive_ratio": self.breakdown.productive_ratio,
            },
            "time_breakdown": self.breakdown.to_dict(),
            "bottlenecks": [b.to_dict() for b in self.bottlenecks],
            "task_details": [r.to_dict() for r in self.task_records],
        }
    
    def generate_gantt_data(self) -> List[Dict]:
        """生成甘特图数据"""
        gantt_data = []
        
        for record in self.task_records:
            gantt_data.append({
                "task_id": record.task_id,
                "task_type": record.task_type,
                "category": record.category.value,
                "start": record.start_time,
                "end": record.end_time,
                "duration": record.duration,
                "success": record.success,
            })
        
        return gantt_data
    
    def save_report(self, filepath: str) -> None:
        """保存报告到文件"""
        report = self.get_report()
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
    
    def load_from_log(self, log_path: str) -> int:
        """从日志文件加载任务记录"""
        path = Path(log_path)
        if not path.exists():
            return 0
        
        loaded_count = 0
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    
                    # 解析日志条目
                    if "task" in entry:
                        task_info = entry["task"]
                        self.add_task(
                            task_id=task_info.get("id", f"task_{loaded_count}"),
                            task_type=task_info.get("type", "unknown"),
                            start_time=task_info.get("start_time", entry.get("time", 0)),
                            end_time=task_info.get("end_time", entry.get("time", 0)),
                            success=task_info.get("success", True),
                            metadata=task_info,
                        )
                        loaded_count += 1
                        
                except json.JSONDecodeError:
                    continue
        
        return loaded_count
    
    def clear(self) -> None:
        """清空所有记录"""
        self.task_records.clear()
        self.breakdown = TimeBreakdown()
        self.bottlenecks.clear()


# 便捷函数
def analyze_time(log_path: str) -> Dict:
    """分析日志文件并返回报告"""
    analyzer = TimeAnalyzer()
    analyzer.load_from_log(log_path)
    return analyzer.get_report()


def identify_bottlenecks(log_path: str) -> List[BottleneckInfo]:
    """识别日志文件中的瓶颈"""
    analyzer = TimeAnalyzer()
    analyzer.load_from_log(log_path)
    analyzer.analyze()
    return analyzer.identify_bottlenecks()
