"""
GENESIS Fabricator Station - 加工站

加工站用于制造各种零件和组件。
支持多种配方: 电路板、电机、关节模块、框架、控制器、夹爪手指

特点:
- CNC/3D打印复合工艺
- 支持多种配方
- 精密加工
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .base_station import WorkStation, StationConfig, StationState
from genesis.world.recipes import Recipe, RecipeRegistry


@dataclass
class FabricatorConfig(StationConfig):
    """
    加工站配置
    
    Attributes:
        precision: 加工精度 (米)
        max_power: 最大功率 (瓦)
        queue_mode: 队列模式 (FIFO, PRIORITY)
        auto_start: 是否自动开始加工
    """
    precision: float = 0.001  # 1mm
    max_power: float = 2000.0  # 瓦
    queue_mode: str = "FIFO"  # FIFO 或 PRIORITY
    auto_start: bool = True
    
    def __post_init__(self):
        """初始化后设置默认值"""
        self.name = self.name or "fabricator"
        self.station_type = "cnc_3dprint"
        self.size = self.size or (2.5, 2.0, 1.8)


class Fabricator(WorkStation):
    """
    加工站
    
    制造各种零件和组件的工站。
    
    支持配方:
    - make_circuit_board: 2 silicon_ore + 1 iron_bar → 1 circuit_board (45秒)
    - make_motor: 2 iron_bar + 1 circuit_board → 1 motor (60秒)
    - make_joint_module: 1 motor + 1 iron_bar → 1 joint_module (40秒)
    - make_frame: 4 iron_bar → 1 frame_segment (50秒)
    - make_controller: 2 circuit_board + 1 silicon_ore → 1 controller_board (90秒)
    - make_gripper_finger: 1 iron_bar → 2 gripper_finger (20秒)
    
    特点:
    - 同一时间只能执行一个配方
    - 支持 FIFO 队列模式
    - 精密加工，需要精确的输入
    
    Attributes:
        config: 加工站配置
        recipe_queue: 配方队列
        current_precision: 当前加工精度
    """
    
    def __init__(
        self,
        config: Optional[FabricatorConfig] = None,
        recipe_registry: Optional[RecipeRegistry] = None,
    ):
        """
        初始化加工站
        
        Args:
            config: 加工站配置
            recipe_registry: 配方注册表
        """
        config = config or FabricatorConfig()
        super().__init__(config, recipe_registry)
        
        # 加工特有属性
        self.recipe_queue: List[str] = []  # 等待执行的配方名称
        self.current_precision: float = config.precision
        
        # 加工状态
        self._tool_active: bool = False
        self._print_progress: float = 0.0
    
    def _build_geometry(self, sim_context: Any) -> None:
        """
        构建加工站几何体
        
        Args:
            sim_context: 仿真上下文
        """
        # 简化实现
        self._geometry_info = {
            "type": "fabricator",
            "base": {
                "shape": "box",
                "size": list(self.config.size),
                "color": [0.2, 0.25, 0.3],  # 深蓝灰色
            },
            "work_chamber": {
                "shape": "box",
                "size": [1.5, 1.5, 1.2],
                "position_offset": [0, 0, 0.3],
                "color": [0.15, 0.15, 0.2],  # 深色工作腔
            },
            "control_panel": {
                "shape": "box",
                "size": [0.4, 0.1, 0.3],
                "position_offset": [1.0, 0, 0.8],
                "color": [0.1, 0.1, 0.1],  # 黑色控制面板
            },
        }
    
    def queue_recipe(self, recipe_name: str) -> bool:
        """
        将配方加入队列
        
        Args:
            recipe_name: 配方名称
            
        Returns:
            是否成功加入队列
        """
        # 检查配方是否可用
        available = [r.name for r in self._available_recipes]
        if recipe_name not in available:
            return False
        
        # 加入队列
        self.recipe_queue.append(recipe_name)
        
        # 如果空闲且自动开始，尝试开始
        if self.config.auto_start and self.state == StationState.IDLE:
            self._try_start_queued_recipe()
        
        return True
    
    def _try_start_queued_recipe(self) -> bool:
        """
        尝试开始队列中的配方
        
        Returns:
            是否成功开始
        """
        if not self.recipe_queue:
            return False
        
        # FIFO 模式
        if self.config.queue_mode == "FIFO":
            recipe_name = self.recipe_queue[0]
            recipe = self._find_recipe_by_name(recipe_name)
            if recipe and self._can_execute_recipe(recipe):
                self.recipe_queue.pop(0)
                return self._start_recipe(recipe)
        
        return False
    
    def _find_recipe_by_name(self, name: str) -> Optional[Recipe]:
        """
        根据名称查找配方
        
        Args:
            name: 配方名称
            
        Returns:
            配方对象，如果不存在返回 None
        """
        for recipe in self._available_recipes:
            if recipe.name == name:
                return recipe
        return None
    
    def step(self, dt: float) -> None:
        """
        仿真步进
        
        Args:
            dt: 时间步长 (秒)
        """
        # 调用父类步进
        super().step(dt)
        
        # 更新加工状态
        self._update_fabrication_state(dt)
    
    def _update_fabrication_state(self, dt: float) -> None:
        """
        更新加工状态
        
        Args:
            dt: 时间步长 (秒)
        """
        if self.state == StationState.PROCESSING and self.current_recipe:
            self._tool_active = True
            # 计算打印进度
            total_time = self.current_recipe.process_time
            elapsed = total_time - self.process_timer
            self._print_progress = min(1.0, elapsed / total_time)
        else:
            self._tool_active = False
            self._print_progress = 0.0
    
    def _complete_processing(self) -> None:
        """完成加工"""
        super()._complete_processing()
        
        # 尝试开始队列中的下一个配方
        if self.state == StationState.IDLE and self.recipe_queue:
            self._try_start_queued_recipe()
    
    def get_queue(self) -> List[str]:
        """获取配方队列"""
        return self.recipe_queue.copy()
    
    def get_print_progress(self) -> float:
        """获取打印进度 (0-1)"""
        return self._print_progress
    
    def is_tool_active(self) -> bool:
        """工具是否激活"""
        return self._tool_active
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取加工站状态
        
        Returns:
            状态字典
        """
        status = super().get_status()
        # 添加加工站特有信息
        status.queue_length = len(self.recipe_queue)
        status.print_progress = self._print_progress
        status.tool_active = self._tool_active
        return status
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data = super().to_dict()
        data["fabricator"] = {
            "recipe_queue": self.recipe_queue,
            "print_progress": self._print_progress,
            "tool_active": self._tool_active,
        }
        return data
    
    def reset(self) -> None:
        """重置加工站状态"""
        super().reset()
        self.recipe_queue.clear()
        self._tool_active = False
        self._print_progress = 0.0


__all__ = [
    "FabricatorConfig",
    "Fabricator",
]
