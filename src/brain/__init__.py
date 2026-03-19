"""
GENESIS 智能决策大脑模块

层级决策架构:
┌─────────────────────────────────────────────────────────┐
│ L3: Strategic Planner (LLM/VLM)                        │
│     "我需要先冶炼铁矿→制造电路板→制造电机→..."          │
│     输出: TaskPlan (有序任务列表)                        │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ L2: Task Executor (行为树)                              │
│     "执行任务: go_to_mine → pick_ore → go_to_smelter    │
│      → feed_smelter → wait → collect_product →..."      │
│     输出: Skill序列调用                                  │
└──────────────────────┬──────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────┐
│ L1: Skill Executor (P4中实现的技能)                     │
│     "执行 top_grasp(object_pose)"                       │
│     输出: 关节指令                                       │
└─────────────────────────────────────────────────────────┘
"""

from .strategic_planner import StrategicPlanner, TaskPlan, Task
from .llm_client import LLMClient, LLMConfig
from .behavior_tree import (
    Blackboard,
    BehaviorTree,
    SequenceNode,
    SelectorNode,
    ActionNode,
    ConditionNode,
    ParallelNode,
    RepeatNode,
    NodeStatus,
)
from .task_executor import TaskExecutor
from .error_handler import ErrorHandler, Recovery, ErrorType
from .dashboard import Dashboard

__all__ = [
    # L3: 战略规划器
    "StrategicPlanner",
    "TaskPlan",
    "Task",
    # LLM 客户端
    "LLMClient",
    "LLMConfig",
    # L2: 行为树
    "Blackboard",
    "BehaviorTree",
    "SequenceNode",
    "SelectorNode",
    "ActionNode",
    "ConditionNode",
    "ParallelNode",
    "RepeatNode",
    "NodeStatus",
    # 任务执行器
    "TaskExecutor",
    # 异常处理
    "ErrorHandler",
    "Recovery",
    "ErrorType",
    # Dashboard
    "Dashboard",
]
