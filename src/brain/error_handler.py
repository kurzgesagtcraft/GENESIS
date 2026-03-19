"""
异常处理模块

负责错误检测、分类和恢复策略。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from .strategic_planner import StrategicPlanner, TaskPlan


class ErrorType(Enum):
    """错误类型"""
    GRASP_FAILED = "grasp_failed"
    NAVIGATION_BLOCKED = "navigation_blocked"
    STATION_ERROR = "station_error"
    BATTERY_CRITICAL = "battery_critical"
    ITEM_LOST = "item_lost"
    PLAN_TIMEOUT = "plan_timeout"
    UNKNOWN = "unknown"


@dataclass
class Recovery:
    """恢复策略"""
    actions: List[str]
    max_retries: int = 3
    priority: str = "normal"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "actions": self.actions,
            "max_retries": self.max_retries,
            "priority": self.priority
        }


class ErrorHandler:
    """
    异常处理器
    
    负责检测错误并提供恢复建议。
    """
    
    def __init__(self, planner: StrategicPlanner):
        self.planner = planner
        self.error_history: List[Dict[str, Any]] = []
        self._recovery_strategies = {
            ErrorType.GRASP_FAILED: Recovery(
                actions=["retry_grasp", "adjust_pose", "replan"],
                max_retries=3
            ),
            ErrorType.NAVIGATION_BLOCKED: Recovery(
                actions=["reroute", "wait_and_retry"],
                max_retries=5
            ),
            ErrorType.STATION_ERROR: Recovery(
                actions=["reset_station", "use_alternate_station", "replan"],
                max_retries=2
            ),
            ErrorType.BATTERY_CRITICAL: Recovery(
                actions=["emergency_charge"],
                max_retries=1,
                priority="highest"
            ),
            ErrorType.ITEM_LOST: Recovery(
                actions=["search_nearby", "mine_replacement", "replan"],
                max_retries=2
            ),
        }
        
    def handle_error(self, error_type: ErrorType, context: Dict[str, Any]) -> Recovery:
        """
        处理错误并返回恢复策略
        """
        recovery = self._recovery_strategies.get(error_type, Recovery(actions=["replan"]))
        
        # 记录错误
        self.error_history.append({
            "type": error_type.value,
            "context": context,
            "recovery": recovery.to_dict()
        })
        
        return recovery
        
    def request_replan(self, current_plan: TaskPlan, failure_info: str) -> TaskPlan:
        """
        请求规划器重新规划
        """
        print(f"Requesting Replan: {failure_info}")
        return self.planner.replan(current_plan, failure_info)
        
    def get_error_summary(self) -> Dict[str, int]:
        """
        获取错误统计摘要
        """
        summary = {}
        for error in self.error_history:
            err_type = error["type"]
            summary[err_type] = summary.get(err_type, 0) + 1
        return summary
