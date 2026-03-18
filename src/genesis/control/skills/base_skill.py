"""
GENESIS Base Skill - 技能基类

定义所有操作技能的基类和通用接口。
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Callable
import numpy as np

from genesis.utils.geometry import SE3


class SkillStatus(Enum):
    """技能状态"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SkillResult:
    """技能执行结果"""
    success: bool
    status: SkillStatus
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None


@dataclass
class SkillContext:
    """
    技能执行上下文

    包含技能执行所需的所有接口和数据。
    """
    # 机器人接口
    robot: Any = None  # GenesisBot 实例

    # 感知接口
    perception: Any = None  # PerceptionSystem 实例

    # 导航接口
    navigator: Any = None  # Navigator 实例

    # 世界管理器
    world_manager: Any = None  # WorldManager 实例

    # 控制器
    ik_solver: Any = None  # IKSolver 实例
    trajectory_planner: Any = None  # TrajectoryPlanner 实例

    # 参数
    params: Dict[str, Any] = field(default_factory=dict)

    # 状态数据
    state: Dict[str, Any] = field(default_factory=dict)


class BaseSkill(ABC):
    """
    技能基类

    所有操作技能都继承此类。
    """

    def __init__(self, name: str, context: SkillContext = None):
        """
        初始化技能

        Args:
            name: 技能名称
            context: 执行上下文
        """
        self.name = name
        self.context = context or SkillContext()

        # 状态
        self._status = SkillStatus.IDLE
        self._progress = 0.0
        self._result: Optional[SkillResult] = None

        # 回调
        self._on_progress: Optional[Callable[[float], None]] = None
        self._on_status_change: Optional[Callable[[SkillStatus], None]] = None

        # 取消标志
        self._cancel_flag = False

    @abstractmethod
    async def execute(self, **kwargs) -> SkillResult:
        """
        执行技能

        Args:
            **kwargs: 技能参数

        Returns:
            执行结果
        """
        pass

    @abstractmethod
    async def cancel(self) -> bool:
        """
        取消技能执行

        Returns:
            是否成功取消
        """
        self._cancel_flag = True
        self._status = SkillStatus.CANCELLED
        return True

    def set_progress_callback(self, callback: Callable[[float], None]):
        """设置进度回调"""
        self._on_progress = callback

    def set_status_callback(self, callback: Callable[[SkillStatus], None]):
        """设置状态回调"""
        self._on_status_change = callback

    def _update_progress(self, progress: float):
        """更新进度"""
        self._progress = max(0.0, min(1.0, progress))
        if self._on_progress:
            self._on_progress(self._progress)

    def _set_status(self, status: SkillStatus):
        """设置状态"""
        old_status = self._status
        self._status = status
        if old_status != status and self._on_status_change:
            self._on_status_change(status)

    def _check_cancelled(self) -> bool:
        """检查是否被取消"""
        return self._cancel_flag

    async def _wait_for_motion(
        self,
        is_moving: Callable[[], bool],
        timeout: float = 30.0,
        poll_interval: float = 0.01,
    ) -> bool:
        """
        等待运动完成

        Args:
            is_moving: 返回是否正在运动的函数
            timeout: 超时时间 (s)
            poll_interval: 轮询间隔 (s)

        Returns:
            是否成功完成
        """
        start_time = asyncio.get_event_loop().time()

        while is_moving():
            if self._check_cancelled():
                return False

            if asyncio.get_event_loop().time() - start_time > timeout:
                return False

            await asyncio.sleep(poll_interval)

        return True

    @property
    def status(self) -> SkillStatus:
        """获取状态"""
        return self._status

    @property
    def progress(self) -> float:
        """获取进度"""
        return self._progress

    @property
    def result(self) -> Optional[SkillResult]:
        """获取结果"""
        return self._result


class SkillLibrary:
    """
    技能库

    管理所有可用技能。
    """

    def __init__(self, context: SkillContext = None):
        """
        初始化技能库

        Args:
            context: 执行上下文
        """
        self.context = context
        self._skills: Dict[str, type] = {}

    def register(self, name: str, skill_class: type):
        """
        注册技能

        Args:
            name: 技能名称
            skill_class: 技能类
        """
        self._skills[name] = skill_class

    def create(self, name: str, **kwargs) -> BaseSkill:
        """
        创建技能实例

        Args:
            name: 技能名称
            **kwargs: 技能参数

        Returns:
            技能实例
        """
        if name not in self._skills:
            raise ValueError(f"Unknown skill: {name}")

        return self._skills[name](context=self.context, **kwargs)

    def list_skills(self) -> List[str]:
        """列出所有技能"""
        return list(self._skills.keys())

    def has_skill(self, name: str) -> bool:
        """检查技能是否存在"""
        return name in self._skills


__all__ = [
    "SkillStatus",
    "SkillResult",
    "SkillContext",
    "BaseSkill",
    "SkillLibrary",
]
