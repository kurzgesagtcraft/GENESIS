"""
GENESIS WorkStation Base - 工站基类

定义所有工站的基类和通用接口。
工站是机器人执行制造任务的核心场所。

状态机:
  IDLE → WAITING_INPUT → PROCESSING → DONE → IDLE
         ↓                    ↓
       ERROR ←───────────────┘
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import time

from genesis.utils.geometry import SE3
from genesis.world.items import Item, ItemRegistry
from genesis.world.recipes import Recipe, RecipeRegistry


class StationState(Enum):
    """工站状态"""
    IDLE = "idle"                    # 空闲，等待任务
    WAITING_INPUT = "waiting_input"  # 等待输入物料
    PROCESSING = "processing"        # 正在加工
    DONE = "done"                    # 加工完成，等待取料
    ERROR = "error"                  # 错误状态


@dataclass
class StationConfig:
    """
    工站配置基类
    
    Attributes:
        name: 工站名称
        station_type: 工站类型 (smelter, cnc_3dprint, assembly)
        position: 工站位置 [x, y, z]
        size: 工站尺寸 [length, width, height]
        input_port_offset: 入料口相对位置偏移
        output_port_offset: 出料口相对位置偏移
        max_input_buffer: 最大输入缓冲区容量
        max_output_buffer: 最大输出缓冲区容量
    """
    name: str = "unnamed_station"
    station_type: str = "unknown"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: Tuple[float, float, float] = (2.0, 2.0, 1.5)
    input_port_offset: Tuple[float, float, float] = (-0.5, 0.0, 0.5)
    output_port_offset: Tuple[float, float, float] = (0.5, 0.0, 0.5)
    max_input_buffer: int = 10
    max_output_buffer: int = 5


@dataclass
class StationStatus:
    """
    工站状态信息
    
    Attributes:
        name: 工站名称
        state: 当前状态
        input_buffer: 输入缓冲区内容 {item_type: quantity}
        output_buffer: 输出缓冲区内容 [Item]
        current_recipe: 当前执行的配方
        process_remaining: 剩余加工时间 (秒)
        available_recipes: 可用配方列表
        total_processed: 总加工次数
        error_message: 错误信息
    """
    name: str
    state: StationState
    input_buffer: Dict[str, int]
    output_count: int
    current_recipe: Optional[str]
    process_remaining: float
    available_recipes: List[str]
    total_processed: int = 0
    error_message: str = ""


class WorkStation(ABC):
    """
    工站基类
    
    所有工站都继承此类，实现统一的接口和状态机。
    
    状态转换:
    - IDLE → WAITING_INPUT: 接收到任务请求
    - WAITING_INPUT → PROCESSING: 物料齐全，开始加工
    - PROCESSING → DONE: 加工完成
    - DONE → IDLE: 产品被取走
    - * → ERROR: 发生错误
    
    Attributes:
        config: 工站配置
        state: 当前状态
        input_buffer: 输入缓冲区
        output_buffer: 输出缓冲区
        current_recipe: 当前执行的配方
        process_timer: 加工计时器
    """
    
    def __init__(
        self,
        config: StationConfig,
        recipe_registry: Optional[RecipeRegistry] = None,
        item_registry: Optional[ItemRegistry] = None,
    ):
        """
        初始化工站
        
        Args:
            config: 工站配置
            recipe_registry: 配方注册表
            item_registry: 物品注册表
        """
        self.config = config
        self.recipe_registry = recipe_registry or RecipeRegistry()
        self.item_registry = item_registry or ItemRegistry()
        
        # 状态
        self.state = StationState.IDLE
        
        # 缓冲区
        self.input_buffer: Dict[str, int] = {}
        self.output_buffer: List[Item] = []
        
        # 当前任务
        self.current_recipe: Optional[Recipe] = None
        self.process_timer: float = 0.0
        self.process_start_time: float = 0.0
        
        # 统计
        self.total_processed: int = 0
        self.total_processing_time: float = 0.0
        
        # 错误信息
        self.error_message: str = ""
        
        # 端口位姿
        self._input_port_pose: Optional[SE3] = None
        self._output_port_pose: Optional[SE3] = None
        
        # 仿真上下文
        self._sim_context: Optional[Any] = None
        self._is_built: bool = False
        
        # 可用配方 (根据工站类型筛选)
        self._available_recipes: List[Recipe] = []
        self._load_available_recipes()
    
    def _load_available_recipes(self) -> None:
        """加载适用于此工站类型的配方"""
        self._available_recipes = [
            recipe for recipe in self.recipe_registry.get_all_recipes()
            if recipe.station_type == self.config.station_type
        ]
    
    def build(self, sim_context: Any) -> None:
        """
        在仿真环境中构建工站
        
        Args:
            sim_context: 仿真上下文 (Isaac Sim 或 MuJoCo)
        """
        self._sim_context = sim_context
        
        # 计算端口位姿
        pos = self.config.position
        self._input_port_pose = SE3.from_translation(
            pos[0] + self.config.input_port_offset[0],
            pos[1] + self.config.input_port_offset[1],
            pos[2] + self.config.input_port_offset[2],
        )
        self._output_port_pose = SE3.from_translation(
            pos[0] + self.config.output_port_offset[0],
            pos[1] + self.config.output_port_offset[1],
            pos[2] + self.config.output_port_offset[2],
        )
        
        # 子类实现具体构建逻辑
        self._build_geometry(sim_context)
        
        self._is_built = True
    
    @abstractmethod
    def _build_geometry(self, sim_context: Any) -> None:
        """
        构建工站几何体 (子类实现)
        
        Args:
            sim_context: 仿真上下文
        """
        pass
    
    def receive_input(self, item_type: str, quantity: int = 1) -> bool:
        """
        接收投入的物料
        
        Args:
            item_type: 物品类型
            quantity: 数量
            
        Returns:
            是否成功接收
        """
        # 检查缓冲区容量
        total_input = sum(self.input_buffer.values()) + quantity
        if total_input > self.config.max_input_buffer:
            return False
        
        # 添加到缓冲区
        self.input_buffer[item_type] = self.input_buffer.get(item_type, 0) + quantity
        
        # 如果是空闲状态，切换到等待输入
        if self.state == StationState.IDLE:
            self.state = StationState.WAITING_INPUT
        
        # 检查是否可以开始加工
        self._check_recipe_ready()
        
        return True
    
    def _check_recipe_ready(self) -> bool:
        """
        检查是否有配方可以开始
        
        Returns:
            是否开始加工
        """
        if self.state not in [StationState.IDLE, StationState.WAITING_INPUT]:
            return False
        
        # 遍历可用配方，找到可以执行的
        for recipe in self._available_recipes:
            if self._can_execute_recipe(recipe):
                return self._start_recipe(recipe)
        
        return False
    
    def _can_execute_recipe(self, recipe: Recipe) -> bool:
        """
        检查是否可以执行配方
        
        Args:
            recipe: 配方
            
        Returns:
            是否可以执行
        """
        for item_type, required in recipe.inputs.items():
            if self.input_buffer.get(item_type, 0) < required:
                return False
        return True
    
    def _start_recipe(self, recipe: Recipe) -> bool:
        """
        开始执行配方
        
        Args:
            recipe: 配方
            
        Returns:
            是否成功开始
        """
        # 消耗输入物料
        for item_type, quantity in recipe.inputs.items():
            self.input_buffer[item_type] -= quantity
            if self.input_buffer[item_type] <= 0:
                del self.input_buffer[item_type]
        
        # 设置当前配方
        self.current_recipe = recipe
        self.process_timer = recipe.process_time
        self.process_start_time = time.time()
        self.state = StationState.PROCESSING
        
        return True
    
    def step(self, dt: float) -> None:
        """
        仿真步进
        
        Args:
            dt: 时间步长 (秒)
        """
        if self.state == StationState.PROCESSING:
            self.process_timer -= dt
            
            if self.process_timer <= 0:
                self._complete_processing()
    
    def _complete_processing(self) -> None:
        """完成加工"""
        if self.current_recipe is None:
            return
        
        # 生成产品
        for item_type, quantity in self.current_recipe.outputs.items():
            for _ in range(quantity):
                item = self.item_registry.create(item_type)
                if item:
                    self.output_buffer.append(item)
        
        # 更新统计
        self.total_processed += 1
        self.total_processing_time += self.current_recipe.process_time
        
        # 清除当前配方
        recipe_name = self.current_recipe.name
        self.current_recipe = None
        
        # 检查输出缓冲区
        if self.output_buffer:
            self.state = StationState.DONE
        else:
            self.state = StationState.IDLE
        
        # 尝试继续执行下一个配方
        if self.state == StationState.IDLE:
            self._check_recipe_ready()
    
    def collect_output(self) -> Optional[Item]:
        """
        取出一个产品
        
        Returns:
            产品物品，如果没有返回 None
        """
        if not self.output_buffer:
            return None
        
        item = self.output_buffer.pop(0)
        
        # 更新状态
        if not self.output_buffer:
            if self.state == StationState.DONE:
                self.state = StationState.IDLE
                # 尝试继续执行下一个配方
                self._check_recipe_ready()
        
        return item
    
    def collect_all_output(self) -> List[Item]:
        """
        取出所有产品
        
        Returns:
            产品列表
        """
        items = self.output_buffer.copy()
        self.output_buffer.clear()
        
        if self.state == StationState.DONE:
            self.state = StationState.IDLE
            self._check_recipe_ready()
        
        return items
    
    def get_status(self) -> StationStatus:
        """
        获取工站状态
        
        Returns:
            状态信息
        """
        return StationStatus(
            name=self.config.name,
            state=self.state,
            input_buffer=dict(self.input_buffer),
            output_count=len(self.output_buffer),
            current_recipe=self.current_recipe.name if self.current_recipe else None,
            process_remaining=max(0.0, self.process_timer),
            available_recipes=[r.name for r in self._available_recipes],
            total_processed=self.total_processed,
            error_message=self.error_message,
        )
    
    def get_input_port_pose(self) -> SE3:
        """获取入料口位姿"""
        if self._input_port_pose is None:
            pos = self.config.position
            offset = self.config.input_port_offset
            self._input_port_pose = SE3.from_translation(
                pos[0] + offset[0],
                pos[1] + offset[1],
                pos[2] + offset[2],
            )
        return self._input_port_pose
    
    def get_output_port_pose(self) -> SE3:
        """获取出料口位姿"""
        if self._output_port_pose is None:
            pos = self.config.position
            offset = self.config.output_port_offset
            self._output_port_pose = SE3.from_translation(
                pos[0] + offset[0],
                pos[1] + offset[1],
                pos[2] + offset[2],
            )
        return self._output_port_pose
    
    def get_available_recipes(self) -> List[str]:
        """获取可用配方名称列表"""
        return [r.name for r in self._available_recipes]
    
    def can_accept_input(self, item_type: str) -> bool:
        """
        检查是否可以接收指定类型的输入
        
        Args:
            item_type: 物品类型
            
        Returns:
            是否可以接收
        """
        # 检查缓冲区容量
        if sum(self.input_buffer.values()) >= self.config.max_input_buffer:
            return False
        
        # 检查是否有配方需要此物品
        for recipe in self._available_recipes:
            if item_type in recipe.inputs:
                return True
        
        return False
    
    def reset(self) -> None:
        """重置工站状态"""
        self.state = StationState.IDLE
        self.input_buffer.clear()
        self.output_buffer.clear()
        self.current_recipe = None
        self.process_timer = 0.0
        self.error_message = ""
    
    def set_error(self, message: str) -> None:
        """
        设置错误状态
        
        Args:
            message: 错误信息
        """
        self.state = StationState.ERROR
        self.error_message = message
        self.current_recipe = None
        self.process_timer = 0.0
    
    def clear_error(self) -> bool:
        """
        清除错误状态
        
        Returns:
            是否成功清除
        """
        if self.state != StationState.ERROR:
            return False
        
        self.state = StationState.IDLE
        self.error_message = ""
        
        # 尝试继续执行
        self._check_recipe_ready()
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "config": {
                "name": self.config.name,
                "station_type": self.config.station_type,
                "position": list(self.config.position),
                "size": list(self.config.size),
            },
            "state": {
                "current": self.state.value,
                "input_buffer": dict(self.input_buffer),
                "output_count": len(self.output_buffer),
                "current_recipe": self.current_recipe.name if self.current_recipe else None,
                "process_remaining": max(0.0, self.process_timer),
            },
            "statistics": {
                "total_processed": self.total_processed,
                "total_processing_time": self.total_processing_time,
            },
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.config.name}, state={self.state.value})"


__all__ = [
    "StationState",
    "StationConfig",
    "StationStatus",
    "WorkStation",
]
