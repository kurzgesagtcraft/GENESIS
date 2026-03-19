"""
GENESIS 可靠性分析模块

分析系统故障模式，统计各技能失败率，
计算 MTBF 和故障恢复成功率，提供可靠性优化建议。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict


class FailureType(Enum):
    """故障类型"""
    GRASP_FAILED = "grasp_failed"               # 抓取失败
    NAVIGATION_BLOCKED = "navigation_blocked"   # 导航受阻
    STATION_ERROR = "station_error"             # 工站错误
    BATTERY_CRITICAL = "battery_critical"       # 电量临界
    ITEM_LOST = "item_lost"                     # 物品丢失
    PERCEPTION_ERROR = "perception_error"       # 感知错误
    PLANNING_ERROR = "planning_error"           # 规划错误
    TIMEOUT = "timeout"                         # 超时
    UNKNOWN = "unknown"                         # 未知错误


class RecoveryAction(Enum):
    """恢复动作"""
    RETRY = "retry"                     # 重试
    ADJUST_POSE = "adjust_pose"         # 调整位姿
    REROUTE = "reroute"                 # 重新路由
    REPLAN = "replan"                   # 重新规划
    EMERGENCY_CHARGE = "emergency_charge"  # 紧急充电
    SEARCH_NEARBY = "search_nearby"     # 搜索附近
    RESET_STATION = "reset_station"     # 重置工站
    USE_ALTERNATE = "use_alternate"     # 使用替代方案
    ABORT = "abort"                     # 中止
    MANUAL_INTERVENTION = "manual_intervention"  # 人工干预


class Severity(Enum):
    """严重程度"""
    LOW = "low"           # 低：不影响主流程
    MEDIUM = "medium"     # 中：需要恢复动作
    HIGH = "high"         # 高：影响任务完成
    CRITICAL = "critical" # 严重：系统级故障


@dataclass
class FailureEvent:
    """故障事件"""
    timestamp: float
    failure_type: FailureType
    severity: Severity
    task_id: str
    task_type: str
    description: str
    context: Dict = field(default_factory=dict)
    recovery_actions: List[RecoveryAction] = field(default_factory=list)
    recovery_success: Optional[bool] = None
    recovery_time: float = 0.0
    retry_count: int = 0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "failure_type": self.failure_type.value,
            "severity": self.severity.value,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "context": self.context,
            "recovery_actions": [a.value for a in self.recovery_actions],
            "recovery_success": self.recovery_success,
            "recovery_time": self.recovery_time,
            "retry_count": self.retry_count,
        }


@dataclass
class FailureStats:
    """故障统计"""
    failure_type: FailureType
    count: int = 0
    success_recovery_count: int = 0
    failed_recovery_count: int = 0
    total_recovery_time: float = 0.0
    total_retry_count: int = 0
    avg_recovery_time: float = 0.0
    recovery_success_rate: float = 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "failure_type": self.failure_type.value,
            "count": self.count,
            "success_recovery_count": self.success_recovery_count,
            "failed_recovery_count": self.failed_recovery_count,
            "total_recovery_time": self.total_recovery_time,
            "total_retry_count": self.total_retry_count,
            "avg_recovery_time": self.avg_recovery_time,
            "recovery_success_rate": self.recovery_success_rate,
        }


@dataclass
class SkillReliabilityStats:
    """技能可靠性统计"""
    skill_name: str
    total_attempts: int = 0
    success_count: int = 0
    failure_count: int = 0
    success_rate: float = 0.0
    avg_execution_time: float = 0.0
    total_execution_time: float = 0.0
    failure_types: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "skill_name": self.skill_name,
            "total_attempts": self.total_attempts,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "avg_execution_time": self.avg_execution_time,
            "total_execution_time": self.total_execution_time,
            "failure_types": self.failure_types,
        }


@dataclass
class ReliabilityReport:
    """可靠性报告"""
    total_failures: int = 0
    total_tasks: int = 0
    overall_success_rate: float = 0.0
    mtbf: float = 0.0  # 平均故障间隔时间 (秒)
    mttr: float = 0.0  # 平均恢复时间 (秒)
    
    failure_stats: Dict[str, FailureStats] = field(default_factory=dict)
    skill_stats: Dict[str, SkillReliabilityStats] = field(default_factory=dict)
    
    reliability_score: float = 0.0  # 综合可靠性评分 (0-100)
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_failures": self.total_failures,
            "total_tasks": self.total_tasks,
            "overall_success_rate": self.overall_success_rate,
            "mtbf": self.mtbf,
            "mttr": self.mttr,
            "failure_stats": {k: v.to_dict() for k, v in self.failure_stats.items()},
            "skill_stats": {k: v.to_dict() for k, v in self.skill_stats.items()},
            "reliability_score": self.reliability_score,
            "recommendations": self.recommendations,
        }


class ReliabilityAnalyzer:
    """可靠性分析器"""
    
    # 技能到故障类型的映射
    SKILL_FAILURE_MAP = {
        "top_grasp": [FailureType.GRASP_FAILED, FailureType.PERCEPTION_ERROR],
        "side_grasp": [FailureType.GRASP_FAILED, FailureType.PERCEPTION_ERROR],
        "place": [FailureType.GRASP_FAILED, FailureType.ITEM_LOST],
        "feed_station": [FailureType.STATION_ERROR, FailureType.ITEM_LOST],
        "retrieve_station": [FailureType.STATION_ERROR, FailureType.ITEM_LOST],
        "navigate_to_zone": [FailureType.NAVIGATION_BLOCKED, FailureType.TIMEOUT],
        "charge": [FailureType.BATTERY_CRITICAL, FailureType.TIMEOUT],
    }
    
    # 故障严重程度默认映射
    FAILURE_SEVERITY_MAP = {
        FailureType.GRASP_FAILED: Severity.MEDIUM,
        FailureType.NAVIGATION_BLOCKED: Severity.MEDIUM,
        FailureType.STATION_ERROR: Severity.HIGH,
        FailureType.BATTERY_CRITICAL: Severity.CRITICAL,
        FailureType.ITEM_LOST: Severity.HIGH,
        FailureType.PERCEPTION_ERROR: Severity.MEDIUM,
        FailureType.PLANNING_ERROR: Severity.HIGH,
        FailureType.TIMEOUT: Severity.LOW,
        FailureType.UNKNOWN: Severity.MEDIUM,
    }
    
    def __init__(self):
        """初始化可靠性分析器"""
        self.failure_events: List[FailureEvent] = []
        self.task_records: List[Dict] = []  # 任务执行记录
        self.report = ReliabilityReport()
        
    def add_failure_event(self, event: FailureEvent) -> None:
        """添加故障事件"""
        self.failure_events.append(event)
        
    def add_failure(
        self,
        timestamp: float,
        failure_type: FailureType,
        task_id: str,
        task_type: str,
        description: str = "",
        severity: Optional[Severity] = None,
        context: Optional[Dict] = None,
        recovery_actions: Optional[List[RecoveryAction]] = None,
        recovery_success: Optional[bool] = None,
        recovery_time: float = 0.0,
        retry_count: int = 0,
    ) -> None:
        """添加故障事件（简化接口）"""
        if severity is None:
            severity = self.FAILURE_SEVERITY_MAP.get(failure_type, Severity.MEDIUM)
        
        event = FailureEvent(
            timestamp=timestamp,
            failure_type=failure_type,
            severity=severity,
            task_id=task_id,
            task_type=task_type,
            description=description,
            context=context or {},
            recovery_actions=recovery_actions or [],
            recovery_success=recovery_success,
            recovery_time=recovery_time,
            retry_count=retry_count,
        )
        self.add_failure_event(event)
    
    def add_task_record(
        self,
        task_id: str,
        task_type: str,
        start_time: float,
        end_time: float,
        success: bool,
        failure_type: Optional[FailureType] = None,
    ) -> None:
        """添加任务执行记录"""
        self.task_records.append({
            "task_id": task_id,
            "task_type": task_type,
            "start_time": start_time,
            "end_time": end_time,
            "success": success,
            "failure_type": failure_type.value if failure_type else None,
        })
    
    def analyze(self) -> ReliabilityReport:
        """分析所有故障事件"""
        self.report = ReliabilityReport()
        
        # 统计故障
        failure_type_stats: Dict[FailureType, FailureStats] = {}
        skill_stats: Dict[str, SkillReliabilityStats] = {}
        
        for event in self.failure_events:
            # 按故障类型统计
            if event.failure_type not in failure_type_stats:
                failure_type_stats[event.failure_type] = FailureStats(
                    failure_type=event.failure_type
                )
            stats = failure_type_stats[event.failure_type]
            stats.count += 1
            
            if event.recovery_success is not None:
                if event.recovery_success:
                    stats.success_recovery_count += 1
                else:
                    stats.failed_recovery_count += 1
            
            stats.total_recovery_time += event.recovery_time
            stats.total_retry_count += event.retry_count
            
            # 按技能统计
            skill_name = event.task_type
            if skill_name not in skill_stats:
                skill_stats[skill_name] = SkillReliabilityStats(skill_name=skill_name)
            skill_stat = skill_stats[skill_name]
            skill_stat.failure_count += 1
            
            # 记录故障类型分布
            ft_key = event.failure_type.value
            if ft_key not in skill_stat.failure_types:
                skill_stat.failure_types[ft_key] = 0
            skill_stat.failure_types[ft_key] += 1
        
        # 计算故障类型的恢复成功率
        for stats in failure_type_stats.values():
            total_recovery = stats.success_recovery_count + stats.failed_recovery_count
            if total_recovery > 0:
                stats.recovery_success_rate = stats.success_recovery_count / total_recovery
            if stats.count > 0:
                stats.avg_recovery_time = stats.total_recovery_time / stats.count
        
        # 从任务记录统计技能成功率
        for record in self.task_records:
            skill_name = record["task_type"]
            if skill_name not in skill_stats:
                skill_stats[skill_name] = SkillReliabilityStats(skill_name=skill_name)
            
            skill_stat = skill_stats[skill_name]
            skill_stat.total_attempts += 1
            skill_stat.total_execution_time += record["end_time"] - record["start_time"]
            
            if record["success"]:
                skill_stat.success_count += 1
            else:
                skill_stat.failure_count += 1
        
        # 计算技能成功率
        for skill_stat in skill_stats.values():
            if skill_stat.total_attempts > 0:
                skill_stat.success_rate = skill_stat.success_count / skill_stat.total_attempts
                skill_stat.avg_execution_time = (
                    skill_stat.total_execution_time / skill_stat.total_attempts
                )
        
        # 计算总体指标
        self.report.total_failures = len(self.failure_events)
        self.report.total_tasks = len(self.task_records)
        
        if self.report.total_tasks > 0:
            success_tasks = sum(1 for r in self.task_records if r["success"])
            self.report.overall_success_rate = success_tasks / self.report.total_tasks
        
        # 计算 MTBF (平均故障间隔时间)
        if len(self.failure_events) >= 2:
            sorted_events = sorted(self.failure_events, key=lambda e: e.timestamp)
            intervals = []
            for i in range(1, len(sorted_events)):
                interval = sorted_events[i].timestamp - sorted_events[i-1].timestamp
                intervals.append(interval)
            self.report.mtbf = sum(intervals) / len(intervals) if intervals else 0.0
        
        # 计算 MTTR (平均恢复时间)
        recovery_times = [
            e.recovery_time for e in self.failure_events 
            if e.recovery_time > 0 and e.recovery_success is not None
        ]
        if recovery_times:
            self.report.mttr = sum(recovery_times) / len(recovery_times)
        
        # 存储统计结果
        self.report.failure_stats = {ft.value: stats for ft, stats in failure_type_stats.items()}
        self.report.skill_stats = {name: stats for name, stats in skill_stats.items()}
        
        # 计算可靠性评分
        self.report.reliability_score = self._calculate_reliability_score()
        
        # 生成建议
        self.report.recommendations = self._generate_recommendations()
        
        return self.report
    
    def _calculate_reliability_score(self) -> float:
        """
        计算综合可靠性评分 (0-100)
        
        评分因素：
        - 任务成功率 (40%)
        - 恢复成功率 (30%)
        - MTBF (20%)
        - 关键故障率 (10%)
        """
        score = 0.0
        
        # 任务成功率贡献 (40%)
        success_rate = self.report.overall_success_rate
        score += success_rate * 40
        
        # 恢复成功率贡献 (30%)
        if self.report.failure_stats:
            total_recovery = sum(
                s.success_recovery_count + s.failed_recovery_count 
                for s in self.report.failure_stats.values()
            )
            if total_recovery > 0:
                success_recovery = sum(
                    s.success_recovery_count for s in self.report.failure_stats.values()
                )
                recovery_rate = success_recovery / total_recovery
                score += recovery_rate * 30
        else:
            score += 30  # 无故障则满分
        
        # MTBF 贡献 (20%)
        # 假设 MTBF > 3600秒 (1小时) 为满分
        if self.report.mtbf > 0:
            mtbf_score = min(1.0, self.report.mtbf / 3600.0)
            score += mtbf_score * 20
        else:
            score += 20  # 无故障则满分
        
        # 关键故障率贡献 (10%)
        critical_failures = sum(
            1 for e in self.failure_events 
            if e.severity == Severity.CRITICAL
        )
        if self.report.total_tasks > 0:
            critical_rate = 1 - (critical_failures / self.report.total_tasks)
            score += critical_rate * 10
        else:
            score += 10
        
        return min(100.0, score)
    
    def _generate_recommendations(self) -> List[str]:
        """生成可靠性优化建议"""
        recommendations = []
        
        # 基于成功率
        if self.report.overall_success_rate < 0.9:
            recommendations.append(
                f"整体成功率 {self.report.overall_success_rate:.1%} 低于目标 90%，"
                f"建议分析失败原因并优化"
            )
        
        # 基于技能统计
        for skill_name, stats in self.report.skill_stats.items():
            if stats.success_rate < 0.95:
                recommendations.append(
                    f"技能 '{skill_name}' 成功率 {stats.success_rate:.1%}，"
                    f"建议优化参数或增加重试机制"
                )
            
            if stats.failure_count > 5:
                # 分析主要故障类型
                if stats.failure_types:
                    top_failure = max(
                        stats.failure_types.items(), 
                        key=lambda x: x[1]
                    )
                    recommendations.append(
                        f"技能 '{skill_name}' 主要故障: {top_failure[0]} "
                        f"({top_failure[1]}次)，建议针对性优化"
                    )
        
        # 基于故障类型
        for failure_type, stats in self.report.failure_stats.items():
            if stats.count > 3:
                if stats.recovery_success_rate < 0.8:
                    recommendations.append(
                        f"故障 '{failure_type}' 恢复成功率 {stats.recovery_success_rate:.1%}，"
                        f"建议改进恢复策略"
                    )
        
        # 基于 MTBF
        if self.report.mtbf > 0 and self.report.mtbf < 600:  # 小于10分钟
            recommendations.append(
                f"MTBF 仅 {self.report.mtbf:.0f}秒，故障频率过高，"
                f"建议系统性排查故障根源"
            )
        
        # 基于 MTTR
        if self.report.mttr > 30:  # 大于30秒
            recommendations.append(
                f"MTTR {self.report.mttr:.1f}秒，恢复时间较长，"
                f"建议优化恢复流程"
            )
        
        # 基于严重程度
        critical_count = sum(
            1 for e in self.failure_events 
            if e.severity == Severity.CRITICAL
        )
        if critical_count > 0:
            recommendations.append(
                f"发生 {critical_count} 次严重故障，"
                f"建议优先解决系统级问题"
            )
        
        return recommendations
    
    def get_failure_distribution(self) -> Dict[str, int]:
        """获取故障类型分布"""
        distribution = defaultdict(int)
        for event in self.failure_events:
            distribution[event.failure_type.value] += 1
        return dict(distribution)
    
    def get_skill_failure_matrix(self) -> Dict[str, Dict[str, int]]:
        """获取技能-故障类型矩阵"""
        matrix = defaultdict(lambda: defaultdict(int))
        for event in self.failure_events:
            matrix[event.task_type][event.failure_type.value] += 1
        return {k: dict(v) for k, v in matrix.items()}
    
    def get_report(self) -> ReliabilityReport:
        """生成完整分析报告"""
        return self.analyze()
    
    def save_report(self, filepath: str) -> None:
        """保存报告到文件"""
        report = self.get_report()
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    
    def load_from_log(self, log_path: str) -> int:
        """从日志文件加载故障事件"""
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
                    
                    # 解析故障日志
                    if "failure" in entry:
                        failure_info = entry["failure"]
                        
                        failure_type_str = failure_info.get("type", "unknown")
                        try:
                            failure_type = FailureType(failure_type_str)
                        except ValueError:
                            failure_type = FailureType.UNKNOWN
                        
                        recovery_actions = []
                        for action_str in failure_info.get("recovery_actions", []):
                            try:
                                recovery_actions.append(RecoveryAction(action_str))
                            except ValueError:
                                pass
                        
                        self.add_failure(
                            timestamp=entry.get("time", 0),
                            failure_type=failure_type,
                            task_id=failure_info.get("task_id", "unknown"),
                            task_type=failure_info.get("task_type", "unknown"),
                            description=failure_info.get("description", ""),
                            recovery_actions=recovery_actions,
                            recovery_success=failure_info.get("recovery_success"),
                            recovery_time=failure_info.get("recovery_time", 0),
                            retry_count=failure_info.get("retry_count", 0),
                        )
                        loaded_count += 1
                    
                    # 解析任务日志
                    elif "task" in entry:
                        task_info = entry["task"]
                        self.add_task_record(
                            task_id=task_info.get("id", "unknown"),
                            task_type=task_info.get("type", "unknown"),
                            start_time=task_info.get("start_time", entry.get("time", 0)),
                            end_time=task_info.get("end_time", entry.get("time", 0)),
                            success=task_info.get("success", True),
                        )
                        
                except json.JSONDecodeError:
                    continue
        
        return loaded_count
    
    def clear(self) -> None:
        """清空所有记录"""
        self.failure_events.clear()
        self.task_records.clear()
        self.report = ReliabilityReport()


# 便捷函数
def analyze_reliability(log_path: str) -> Dict:
    """分析日志文件并返回可靠性报告"""
    analyzer = ReliabilityAnalyzer()
    analyzer.load_from_log(log_path)
    return analyzer.get_report().to_dict()


def calculate_mtbf(failure_timestamps: List[float]) -> float:
    """计算 MTBF"""
    if len(failure_timestamps) < 2:
        return 0.0
    
    sorted_timestamps = sorted(failure_timestamps)
    intervals = [
        sorted_timestamps[i] - sorted_timestamps[i-1]
        for i in range(1, len(sorted_timestamps))
    ]
    return sum(intervals) / len(intervals) if intervals else 0.0
