"""
GENESIS Station Interface - 工站统一接口

定义机器人与工站交互的统一接口。
提供查询状态、提交任务、检查进度、领取产品的功能。

接口设计:
- StationInterface: 主接口类
- JobID: 任务标识
- JobStatus: 任务状态
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from genesis.world.items import Item
from .base_station import WorkStation, StationState, StationStatus

if TYPE_CHECKING:
    from .station_manager import StationManager


class JobState(Enum):
    """任务状态"""
    PENDING = "pending"        # 等待中
    QUEUED = "queued"          # 已入队
    RUNNING = "running"        # 执行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消


@dataclass
class JobID:
    """
    任务标识
    
    Attributes:
        station_name: 工站名称
        recipe_name: 配方名称
        sequence: 序列号
    """
    station_name: str
    recipe_name: str
    sequence: int = 0
    
    def __str__(self) -> str:
        return f"{self.station_name}:{self.recipe_name}:{self.sequence}"
    
    def __hash__(self) -> int:
        return hash(str(self))
    
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, JobID):
            return False
        return (
            self.station_name == other.station_name and
            self.recipe_name == other.recipe_name and
            self.sequence == other.sequence
        )


@dataclass
class JobStatus:
    """
    任务状态信息
    
    Attributes:
        job_id: 任务ID
        state: 任务状态
        progress: 进度 (0-1)
        start_time: 开始时间
        end_time: 结束时间
        error_message: 错误信息
        output_items: 输出物品列表
    """
    job_id: JobID
    state: JobState
    progress: float = 0.0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: str = ""
    output_items: List[str] = field(default_factory=list)


@dataclass
class StationQueryResult:
    """
    工站查询结果
    
    Attributes:
        success: 是否成功
        station_name: 工站名称
        status: 工站状态
        message: 消息
    """
    success: bool
    station_name: str
    status: Optional[StationStatus] = None
    message: str = ""


class StationInterface:
    """
    工站统一接口
    
    提供机器人与工站交互的统一接口。
    
    主要功能:
    - 查询工站状态
    - 提交加工任务
    - 检查任务进度
    - 领取产品
    
    使用示例:
        interface = StationInterface(station_manager)
        
        # 查询状态
        status = interface.query_status("smelter")
        
        # 提交任务
        job_id = interface.submit_job("smelter", "smelt_iron", {"iron_ore": 3})
        
        # 检查进度
        job_status = interface.check_job(job_id)
        
        # 领取产品
        items = interface.collect_product("smelter")
    
    Attributes:
        station_manager: 工站管理器
    """
    
    def __init__(self, station_manager: Optional[StationManager] = None):
        """
        初始化接口
        
        Args:
            station_manager: 工站管理器
        """
        self._station_manager = station_manager
        self._job_counter: int = 0
        self._active_jobs: Dict[str, JobStatus] = {}
    
    def set_station_manager(self, manager: StationManager) -> None:
        """
        设置工站管理器
        
        Args:
            manager: 工站管理器
        """
        self._station_manager = manager
    
    def query_status(self, station_name: str) -> StationQueryResult:
        """
        查询工站状态
        
        Args:
            station_name: 工站名称
            
        Returns:
            查询结果
        """
        station = self._get_station(station_name)
        if station is None:
            return StationQueryResult(
                success=False,
                station_name=station_name,
                message=f"Station not found: {station_name}",
            )
        
        return StationQueryResult(
            success=True,
            station_name=station_name,
            status=station.get_status(),
        )
    
    def query_all_stations(self) -> Dict[str, StationStatus]:
        """
        查询所有工站状态
        
        Returns:
            工站状态字典 {station_name: status}
        """
        if self._station_manager is None:
            return {}
        
        return {
            name: station.get_status()
            for name, station in self._station_manager.get_all_stations().items()
        }
    
    def submit_job(
        self,
        station_name: str,
        recipe_name: str,
        inputs: Dict[str, int],
    ) -> Optional[JobID]:
        """
        提交加工任务
        
        Args:
            station_name: 工站名称
            recipe_name: 配方名称
            inputs: 输入物品 {item_type: quantity}
            
        Returns:
            任务ID，如果失败返回 None
        """
        station = self._get_station(station_name)
        if station is None:
            return None
        
        # 检查配方是否可用
        if recipe_name not in station.get_available_recipes():
            return None
        
        # 投入物料
        for item_type, quantity in inputs.items():
            if not station.receive_input(item_type, quantity):
                return None
        
        # 创建任务ID
        self._job_counter += 1
        job_id = JobID(
            station_name=station_name,
            recipe_name=recipe_name,
            sequence=self._job_counter,
        )
        
        # 记录任务状态
        job_status = JobStatus(
            job_id=job_id,
            state=JobState.QUEUED,
        )
        self._active_jobs[str(job_id)] = job_status
        
        return job_id
    
    def check_job(self, job_id: JobID) -> Optional[JobStatus]:
        """
        查询任务进度
        
        Args:
            job_id: 任务ID
            
        Returns:
            任务状态，如果不存在返回 None
        """
        job_str = str(job_id)
        if job_str not in self._active_jobs:
            return None
        
        job_status = self._active_jobs[job_str]
        station = self._get_station(job_id.station_name)
        
        if station is None:
            job_status.state = JobState.FAILED
            job_status.error_message = "Station not found"
            return job_status
        
        # 更新任务状态
        station_status = station.get_status()
        
        if station_status.state == StationState.PROCESSING:
            job_status.state = JobState.RUNNING
            job_status.progress = 1.0 - (station_status.process_remaining / 
                                        max(0.001, station.current_recipe.process_time if station.current_recipe else 1.0))
        elif station_status.state == StationState.DONE:
            job_status.state = JobState.COMPLETED
            job_status.progress = 1.0
            job_status.output_items = [
                item.item_type for item in station.output_buffer
            ]
        elif station_status.state == StationState.ERROR:
            job_status.state = JobState.FAILED
            job_status.error_message = station_status.error_message
        elif station_status.state == StationState.IDLE:
            if job_status.state == JobState.QUEUED:
                job_status.state = JobState.PENDING
        
        return job_status
    
    def collect_product(
        self,
        station_name: str,
        item_type: Optional[str] = None,
    ) -> Optional[Item]:
        """
        领取产品
        
        Args:
            station_name: 工站名称
            item_type: 指定物品类型 (可选)
            
        Returns:
            产品物品，如果没有返回 None
        """
        station = self._get_station(station_name)
        if station is None:
            return None
        
        # 如果指定了类型，尝试取出指定类型
        if item_type:
            for i, item in enumerate(station.output_buffer):
                if item.item_type == item_type:
                    return station.output_buffer.pop(i)
            return None
        
        # 否则取出第一个
        return station.collect_output()
    
    def collect_all_products(self, station_name: str) -> List[Item]:
        """
        领取所有产品
        
        Args:
            station_name: 工站名称
            
        Returns:
            产品列表
        """
        station = self._get_station(station_name)
        if station is None:
            return []
        
        return station.collect_all_output()
    
    def can_submit_job(
        self,
        station_name: str,
        recipe_name: str,
    ) -> bool:
        """
        检查是否可以提交任务
        
        Args:
            station_name: 工站名称
            recipe_name: 配方名称
            
        Returns:
            是否可以提交
        """
        station = self._get_station(station_name)
        if station is None:
            return False
        
        # 检查配方是否可用
        if recipe_name not in station.get_available_recipes():
            return False
        
        # 检查工站状态
        if station.state == StationState.ERROR:
            return False
        
        return True
    
    def get_station_input_port(self, station_name: str) -> Optional[Any]:
        """
        获取工站入料口位姿
        
        Args:
            station_name: 工站名称
            
        Returns:
            入料口位姿 (SE3)
        """
        station = self._get_station(station_name)
        if station is None:
            return None
        
        return station.get_input_port_pose()
    
    def get_station_output_port(self, station_name: str) -> Optional[Any]:
        """
        获取工站出料口位姿
        
        Args:
            station_name: 工站名称
            
        Returns:
            出料口位姿 (SE3)
        """
        station = self._get_station(station_name)
        if station is None:
            return None
        
        return station.get_output_port_pose()
    
    def cancel_job(self, job_id: JobID) -> bool:
        """
        取消任务
        
        Args:
            job_id: 任务ID
            
        Returns:
            是否成功取消
        """
        job_str = str(job_id)
        if job_str not in self._active_jobs:
            return False
        
        job_status = self._active_jobs[job_str]
        
        # 只能取消待执行的任务
        if job_status.state in [JobState.PENDING, JobState.QUEUED]:
            job_status.state = JobState.CANCELLED
            return True
        
        return False
    
    def clear_completed_jobs(self) -> int:
        """
        清除已完成的任务记录
        
        Returns:
            清除的任务数量
        """
        to_remove = [
            job_id for job_id, status in self._active_jobs.items()
            if status.state in [JobState.COMPLETED, JobState.FAILED, JobState.CANCELLED]
        ]
        
        for job_id in to_remove:
            del self._active_jobs[job_id]
        
        return len(to_remove)
    
    def _get_station(self, station_name: str) -> Optional[WorkStation]:
        """
        获取工站实例
        
        Args:
            station_name: 工站名称
            
        Returns:
            工站实例
        """
        if self._station_manager is None:
            return None
        
        return self._station_manager.get_station(station_name)
    
    def get_active_jobs(self) -> Dict[str, JobStatus]:
        """获取所有活动任务"""
        return dict(self._active_jobs)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        total_jobs = len(self._active_jobs)
        pending = sum(1 for j in self._active_jobs.values() if j.state == JobState.PENDING)
        running = sum(1 for j in self._active_jobs.values() if j.state == JobState.RUNNING)
        completed = sum(1 for j in self._active_jobs.values() if j.state == JobState.COMPLETED)
        failed = sum(1 for j in self._active_jobs.values() if j.state == JobState.FAILED)
        
        return {
            "total_jobs": total_jobs,
            "pending": pending,
            "running": running,
            "completed": completed,
            "failed": failed,
        }


__all__ = [
    "JobState",
    "JobID",
    "JobStatus",
    "StationQueryResult",
    "StationInterface",
]
