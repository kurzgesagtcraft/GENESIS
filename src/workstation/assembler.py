"""
GENESIS Assembler Station - 装配站

装配站用于组装复杂的组件和最终产品。
支持配方: assemble_arm, assemble_robot

特点:
- 需要机器人参与装配动作 (高级版)
- 支持简化版自动装配
- 复杂的多零件组装
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from .base_station import WorkStation, StationConfig, StationState
from genesis.world.recipes import RecipeRegistry


@dataclass
class AssemblerConfig(StationConfig):
    """
    装配站配置
    
    Attributes:
        assembly_mode: 装配模式 (auto, manual, hybrid)
        fixture_count: 夹具数量
        require_robot: 是否需要机器人参与
        quality_check: 是否进行质量检查
    """
    assembly_mode: str = "auto"  # auto, manual, hybrid
    fixture_count: int = 2
    require_robot: bool = False  # 简化版默认不需要
    quality_check: bool = True
    
    def __post_init__(self):
        """初始化后设置默认值"""
        self.name = self.name or "assembler"
        self.station_type = "assembly"
        self.size = self.size or (3.0, 2.5, 1.5)


class Assembler(WorkStation):
    """
    装配站
    
    组装复杂组件和最终产品的工站。
    
    支持配方:
    - assemble_arm: 3 joint_module + 2 frame_segment + 2 gripper_finger → 1 assembled_arm (120秒)
    - assemble_robot: 2 assembled_arm + 4 frame_segment + 4 joint_module + 1 controller_board + 4 motor → 1 assembled_robot (300秒)
    
    装配模式:
    - auto: 简化版，自动完成装配
    - manual: 需要机器人执行装配动作
    - hybrid: 混合模式
    
    Attributes:
        config: 装配站配置
        assembly_progress: 装配进度
        quality_score: 质量评分
    """
    
    def __init__(
        self,
        config: Optional[AssemblerConfig] = None,
        recipe_registry: Optional[RecipeRegistry] = None,
    ):
        """
        初始化装配站
        
        Args:
            config: 装配站配置
            recipe_registry: 配方注册表
        """
        config = config or AssemblerConfig()
        super().__init__(config, recipe_registry)
        
        # 装配特有属性
        self.assembly_progress: float = 0.0
        self.quality_score: float = 1.0
        
        # 装配状态
        self._assembly_stage: int = 0
        self._total_stages: int = 1
        self._fixture_occupied: List[bool] = [False] * config.fixture_count
        
        # 质量检查结果
        self._quality_checked: bool = False
        self._quality_issues: List[str] = []
    
    def _build_geometry(self, sim_context: Any) -> None:
        """
        构建装配站几何体
        
        Args:
            sim_context: 仿真上下文
        """
        # 简化实现
        self._geometry_info = {
            "type": "assembler",
            "base": {
                "shape": "box",
                "size": list(self.config.size),
                "color": [0.25, 0.3, 0.25],  # 深绿色
            },
            "work_table": {
                "shape": "box",
                "size": [2.0, 1.5, 0.1],
                "position_offset": [0, 0, 0.7],
                "color": [0.4, 0.35, 0.3],  # 工作台木色
            },
            "fixtures": [
                {
                    "shape": "cylinder",
                    "radius": 0.15,
                    "height": 0.1,
                    "position_offset": [0.5 * i - 0.5, 0, 0.75],
                    "color": [0.3, 0.3, 0.35],
                }
                for i in range(self.config.fixture_count)
            ],
        }
    
    def _start_recipe(self, recipe) -> bool:
        """
        开始执行配方
        
        Args:
            recipe: 配方
            
        Returns:
            是否成功开始
        """
        result = super()._start_recipe(recipe)
        
        if result:
            # 设置装配阶段
            self._assembly_stage = 0
            self._total_stages = self._calculate_total_stages(recipe)
            self._quality_checked = False
            self._quality_issues.clear()
        
        return result
    
    def _calculate_total_stages(self, recipe) -> int:
        """
        计算装配总阶段数
        
        Args:
            recipe: 配方
            
        Returns:
            阶段数
        """
        # 简化实现：基于输入物品数量
        total_inputs = sum(recipe.inputs.values())
        return max(1, total_inputs // 2)
    
    def step(self, dt: float) -> None:
        """
        仿真步进
        
        Args:
            dt: 时间步长 (秒)
        """
        # 调用父类步进
        super().step(dt)
        
        # 更新装配状态
        self._update_assembly_state(dt)
    
    def _update_assembly_state(self, dt: float) -> None:
        """
        更新装配状态
        
        Args:
            dt: 时间步长 (秒)
        """
        if self.state == StationState.PROCESSING and self.current_recipe:
            # 计算装配进度
            total_time = self.current_recipe.process_time
            elapsed = total_time - self.process_timer
            self.assembly_progress = min(1.0, elapsed / total_time)
            
            # 更新装配阶段
            self._assembly_stage = int(
                self.assembly_progress * self._total_stages
            )
        else:
            self.assembly_progress = 0.0
            self._assembly_stage = 0
    
    def _complete_processing(self) -> None:
        """完成装配"""
        if self.current_recipe is None:
            return
        
        # 质量检查
        if self.config.quality_check:
            self._perform_quality_check()
        
        # 调用父类完成
        super()._complete_processing()
        
        # 重置装配状态
        self.assembly_progress = 0.0
        self._assembly_stage = 0
    
    def _perform_quality_check(self) -> None:
        """执行质量检查"""
        self._quality_checked = True
        self._quality_issues.clear()
        
        # 简化实现：随机质量评分
        # 实际项目中会有更复杂的质量检测逻辑
        import random
        self.quality_score = 0.85 + random.random() * 0.15
        
        # 检查是否有质量问题
        if self.quality_score < 0.9:
            self._quality_issues.append("Minor alignment deviation")
        
        if self.quality_score < 0.85:
            self._quality_issues.append("Assembly tolerance exceeded")
    
    def get_assembly_progress(self) -> float:
        """获取装配进度 (0-1)"""
        return self.assembly_progress
    
    def get_assembly_stage(self) -> Tuple[int, int]:
        """
        获取装配阶段
        
        Returns:
            (当前阶段, 总阶段数)
        """
        return (self._assembly_stage, self._total_stages)
    
    def get_quality_score(self) -> float:
        """获取质量评分"""
        return self.quality_score
    
    def get_quality_issues(self) -> List[str]:
        """获取质量问题列表"""
        return self._quality_issues.copy()
    
    def is_quality_checked(self) -> bool:
        """是否已进行质量检查"""
        return self._quality_checked
    
    def occupy_fixture(self, fixture_id: int) -> bool:
        """
        占用夹具
        
        Args:
            fixture_id: 夹具ID
            
        Returns:
            是否成功占用
        """
        if 0 <= fixture_id < len(self._fixture_occupied):
            if not self._fixture_occupied[fixture_id]:
                self._fixture_occupied[fixture_id] = True
                return True
        return False
    
    def release_fixture(self, fixture_id: int) -> bool:
        """
        释放夹具
        
        Args:
            fixture_id: 夹具ID
            
        Returns:
            是否成功释放
        """
        if 0 <= fixture_id < len(self._fixture_occupied):
            self._fixture_occupied[fixture_id] = False
            return True
        return False
    
    def get_available_fixture(self) -> Optional[int]:
        """
        获取可用夹具ID
        
        Returns:
            夹具ID，如果没有可用返回 None
        """
        for i, occupied in enumerate(self._fixture_occupied):
            if not occupied:
                return i
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取装配站状态
        
        Returns:
            状态字典
        """
        status = super().get_status()
        # 添加装配站特有信息
        status.assembly_progress = self.assembly_progress
        status.assembly_stage = self._assembly_stage
        status.total_stages = self._total_stages
        status.quality_score = self.quality_score
        status.quality_checked = self._quality_checked
        return status
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        data = super().to_dict()
        data["assembler"] = {
            "assembly_progress": self.assembly_progress,
            "assembly_stage": self._assembly_stage,
            "total_stages": self._total_stages,
            "quality_score": self.quality_score,
            "quality_checked": self._quality_checked,
            "quality_issues": self._quality_issues,
        }
        return data
    
    def reset(self) -> None:
        """重置装配站状态"""
        super().reset()
        self.assembly_progress = 0.0
        self.quality_score = 1.0
        self._assembly_stage = 0
        self._total_stages = 1
        self._fixture_occupied = [False] * self.config.fixture_count
        self._quality_checked = False
        self._quality_issues.clear()


__all__ = [
    "AssemblerConfig",
    "Assembler",
]
