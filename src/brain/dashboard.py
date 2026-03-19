"""
Dashboard 模块

提供实时状态监控和数据可视化。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import json
import time


@dataclass
class DashboardState:
    """Dashboard 状态快照"""
    timestamp: float
    robot_position: Dict[str, float]
    robot_battery: float
    current_task: str
    task_progress: float
    inventory: Dict[str, int]
    station_status: Dict[str, Any]
    energy_balance: float
    errors: List[str] = field(default_factory=list)


class Dashboard:
    """
    实时监控 Dashboard
    
    收集并展示系统运行状态。
    """
    
    def __init__(self, world_manager: Any, robot: Any):
        self.world_manager = world_manager
        self.robot = robot
        self.history: List[DashboardState] = []
        self.max_history = 1000
        self._last_update = 0.0
        self._update_interval = 1.0  # 秒
        
    def update(self) -> DashboardState:
        """更新 Dashboard 状态"""
        current_time = time.time()
        
        # 获取世界状态
        world_state = self.world_manager.get_world_state() if hasattr(self.world_manager, 'get_world_state') else {}
        
        # 获取机器人状态
        robot_pos = self.robot.get_base_pose() if hasattr(self.robot, 'get_base_pose') else (0.0, 0.0)
        robot_battery = self.robot.get_battery_soc() if hasattr(self.robot, 'get_battery_soc') else 1.0
        
        state = DashboardState(
            timestamp=current_time,
            robot_position={"x": robot_pos[0], "y": robot_pos[1]} if isinstance(robot_pos, tuple) else robot_pos,
            robot_battery=robot_battery,
            current_task=getattr(self.robot, 'current_task', 'idle'),
            task_progress=getattr(self.robot, 'task_progress', 0.0),
            inventory=world_state.get('warehouse_inventory', {}),
            station_status=world_state.get('station_status', {}),
            energy_balance=world_state.get('energy_balance', 0.0),
        )
        
        # 保存历史
        self.history.append(state)
        if len(self.history) > self.max_history:
            self.history.pop(0)
            
        self._last_update = current_time
        return state
        
    def get_current_state(self) -> Optional[DashboardState]:
        """获取最新状态"""
        return self.history[-1] if self.history else None
        
    def get_summary(self) -> Dict[str, Any]:
        """获取摘要信息"""
        if not self.history:
            return {}
            
        latest = self.history[-1]
        return {
            "timestamp": latest.timestamp,
            "robot": {
                "position": latest.robot_position,
                "battery": f"{latest.robot_battery * 100:.1f}%",
                "current_task": latest.current_task,
            },
            "inventory": latest.inventory,
            "stations": latest.station_status,
            "energy_balance": f"{latest.energy_balance:.1f} Wh",
        }
        
    def export_history(self, filepath: str):
        """导出历史数据"""
        data = []
        for state in self.history:
            data.append({
                "timestamp": state.timestamp,
                "robot_position": state.robot_position,
                "robot_battery": state.robot_battery,
                "current_task": state.current_task,
                "task_progress": state.task_progress,
                "inventory": state.inventory,
                "station_status": state.station_status,
                "energy_balance": state.energy_balance,
                "errors": state.errors,
            })
            
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    def render_text(self) -> str:
        """渲染文本格式"""
        state = self.get_current_state()
        if not state:
            return "No data available"
            
        lines = [
            "=" * 50,
            "GENESIS Dashboard",
            "=" * 50,
            f"Time: {time.strftime('%H:%M:%S', time.localtime(state.timestamp))}",
            "",
            "Robot Status:",
            f"  Position: ({state.robot_position.get('x', 0):.2f}, {state.robot_position.get('y', 0):.2f})",
            f"  Battery: {state.robot_battery * 100:.1f}%",
            f"  Task: {state.current_task}",
            "",
            "Inventory:",
        ]
        
        for item, count in state.inventory.items():
            lines.append(f"  {item}: {count}")
            
        lines.append("")
        lines.append("Stations:")
        for name, status in state.station_status.items():
            lines.append(f"  {name}: {status}")
            
        lines.append("")
        lines.append(f"Energy Balance: {state.energy_balance:.1f} Wh")
        lines.append("=" * 50)
        
        return "\n".join(lines)
