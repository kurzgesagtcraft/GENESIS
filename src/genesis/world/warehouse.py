"""
GENESIS Warehouse Module
仓库/存储区构建与管理

实现:
- 货架模型 (简单立方体组合)
- 存储槽位 (grid)
- Warehouse 类 (存取管理)
- 库存跟踪
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
import numpy as np

from genesis.utils.types import Position3D
from genesis.utils.config import Configurable


@dataclass
class StorageSlot:
  """存储槽位"""
  slot_id: str
  position: Tuple[float, float, float]  # 世界坐标
  size: Tuple[float, float, float]  # 槽位尺寸
  item_id: Optional[str] = None  # 存放的物品ID
  item_type: Optional[str] = None  # 物品类型
  
  def is_empty(self) -> bool:
    return self.item_id is None
  
  def to_dict(self) -> Dict[str, Any]:
    return {
      "slot_id": self.slot_id,
      "position": list(self.position),
      "item_id": self.item_id,
      "item_type": self.item_type,
    }


@dataclass
class WarehouseConfig:
  """仓库配置"""
  name: str = "warehouse"
  position: Tuple[float, float, float] = (0, 0, 0)
  size: Tuple[float, float, float] = (8, 6, 4)
  capacity: int = 200  # 最大物品数
  slot_grid: Tuple[int, int, int] = (4, 3, 2)  # 槽位网格 (x, y, z)
  slot_size: Tuple[float, float, float] = (0.5, 0.5, 0.5)  # 单个槽位尺寸


class Warehouse(Configurable):
  """
  仓库类 - 管理物品存储
  
  功能:
  - 管理存储槽位
  - 物品存取操作
  - 库存查询
  - 空槽位查找
  
  Attributes:
    config: 仓库配置
    slots: 槽位字典
    inventory: 库存统计
  """
  
  def __init__(self, config: WarehouseConfig):
    self.config = config
    self._sim_context: Optional[Any] = None
    
    # 槽位存储
    self.slots: Dict[str, StorageSlot] = {}
    
    # 库存统计 (item_type -> count)
    self.inventory: Dict[str, int] = {}
    
    # 物品ID到槽位的映射
    self._item_to_slot: Dict[str, str] = {}
    
    # 操作统计
    self.total_stored: int = 0
    self.total_retrieved: int = 0
    
    # 初始化槽位
    self._init_slots()
  
  def _init_slots(self) -> None:
    """初始化存储槽位"""
    grid_x, grid_y, grid_z = self.config.slot_grid
    
    # 计算槽位间距
    spacing_x = self.config.size[0] / grid_x
    spacing_y = self.config.size[1] / grid_y
    spacing_z = self.config.size[2] / grid_z
    
    # 创建槽位网格
    for ix in range(grid_x):
      for iy in range(grid_y):
        for iz in range(grid_z):
          slot_id = f"slot_{ix}_{iy}_{iz}"
          
          # 计算世界坐标
          pos_x = self.config.position[0] + (ix + 0.5) * spacing_x - self.config.size[0] / 2
          pos_y = self.config.position[1] + (iy + 0.5) * spacing_y - self.config.size[1] / 2
          pos_z = self.config.position[2] + (iz + 0.5) * spacing_z
          
          slot = StorageSlot(
            slot_id=slot_id,
            position=(pos_x, pos_y, pos_z),
            size=self.config.slot_size,
          )
          
          self.slots[slot_id] = slot
  
  def build(self, sim_context: Any) -> None:
    """
    在仿真环境中构建仓库
    
    Args:
      sim_context: 仿真上下文
    """
    self._sim_context = sim_context
    
    engine_type = getattr(sim_context, 'engine_type', 'unknown')
    
    if engine_type == 'isaac_sim':
      self._build_isaac_sim()
    elif engine_type == 'mujoco':
      self._build_mujoco()
    else:
      self._build_abstract()
  
  def _build_isaac_sim(self) -> None:
    """Isaac Sim 构建"""
    try:
      # 创建货架几何体
      # TODO: 添加详细模型
      pass
    except ImportError:
      self._build_abstract()
  
  def _build_mujoco(self) -> None:
    """MuJoCo 构建"""
    self._build_abstract()
  
  def _build_abstract(self) -> None:
    """抽象构建"""
    pass
  
  def find_empty_slot(self) -> Optional[StorageSlot]:
    """
    查找空槽位
    
    Returns:
      空槽位, 如果没有返回 None
    """
    for slot in self.slots.values():
      if slot.is_empty():
        return slot
    return None
  
  def find_slot_with_item(self, item_type: str) -> Optional[StorageSlot]:
    """
    查找包含指定类型物品的槽位
    
    Args:
      item_type: 物品类型
      
    Returns:
      包含该物品的槽位, 如果没有返回 None
    """
    for slot in self.slots.values():
      if slot.item_type == item_type:
        return slot
    return None
  
  def store_item(
    self,
    item_id: str,
    item_type: str,
    slot_id: Optional[str] = None
  ) -> bool:
    """
    存储物品
    
    Args:
      item_id: 物品ID
      item_type: 物品类型
      slot_id: 指定槽位ID (可选)
      
    Returns:
      是否成功存储
    """
    # 查找槽位
    if slot_id:
      slot = self.slots.get(slot_id)
      if slot is None or not slot.is_empty():
        return False
    else:
      slot = self.find_empty_slot()
      if slot is None:
        return False
    
    # 存储物品
    slot.item_id = item_id
    slot.item_type = item_type
    
    # 更新映射
    self._item_to_slot[item_id] = slot.slot_id
    
    # 更新库存
    self.inventory[item_type] = self.inventory.get(item_type, 0) + 1
    
    # 更新统计
    self.total_stored += 1
    
    return True
  
  def retrieve_item(
    self,
    slot_id: str
  ) -> Optional[Tuple[str, str]]:
    """
    取出物品
    
    Args:
      slot_id: 槽位ID
      
    Returns:
      (item_id, item_type) 元组, 如果槽位为空返回 None
    """
    slot = self.slots.get(slot_id)
    if slot is None or slot.is_empty():
      return None
    
    # 取出物品
    item_id = slot.item_id
    item_type = slot.item_type
    
    # 清空槽位
    slot.item_id = None
    slot.item_type = None
    
    # 更新映射
    if item_id in self._item_to_slot:
      del self._item_to_slot[item_id]
    
    # 更新库存
    if item_type in self.inventory:
      self.inventory[item_type] -= 1
      if self.inventory[item_type] <= 0:
        del self.inventory[item_type]
    
    # 更新统计
    self.total_retrieved += 1
    
    return (item_id, item_type)
  
  def retrieve_item_by_type(
    self,
    item_type: str
  ) -> Optional[Tuple[str, str, str]]:
    """
    按类型取出物品
    
    Args:
      item_type: 物品类型
      
    Returns:
      (item_id, item_type, slot_id) 元组, 如果没有返回 None
    """
    slot = self.find_slot_with_item(item_type)
    if slot is None:
      return None
    
    result = self.retrieve_item(slot.slot_id)
    if result is None:
      return None
    
    return (result[0], result[1], slot.slot_id)
  
  def get_inventory(self) -> Dict[str, int]:
    """
    获取库存统计
    
    Returns:
      物品类型到数量的映射
    """
    return dict(self.inventory)
  
  def get_slot_position(self, slot_id: str) -> Optional[Tuple[float, float, float]]:
    """
    获取槽位位置
    
    Args:
      slot_id: 槽位ID
      
    Returns:
      槽位位置, 如果不存在返回 None
    """
    slot = self.slots.get(slot_id)
    if slot:
      return slot.position
    return None
  
  def get_item_slot(self, item_id: str) -> Optional[str]:
    """
    获取物品所在的槽位ID
    
    Args:
      item_id: 物品ID
      
    Returns:
      槽位ID, 如果不存在返回 None
    """
    return self._item_to_slot.get(item_id)
  
  def get_occupancy(self) -> float:
    """
    获取占用率
    
    Returns:
      占用率 (0-1)
    """
    occupied = sum(1 for slot in self.slots.values() if not slot.is_empty())
    return occupied / len(self.slots) if self.slots else 0.0
  
  def get_available_capacity(self) -> int:
    """
    获取剩余容量
    
    Returns:
      剩余可存储物品数
    """
    return sum(1 for slot in self.slots.values() if slot.is_empty())
  
  def step(self, dt: float) -> None:
    """
    仿真步进
    
    Args:
      dt: 时间步长
    """
    pass
  
  def get_status(self) -> Dict[str, Any]:
    """获取状态"""
    return {
      "name": self.config.name,
      "capacity": self.config.capacity,
      "occupied": sum(1 for s in self.slots.values() if not s.is_empty()),
      "available": self.get_available_capacity(),
      "occupancy": self.get_occupancy(),
      "inventory": self.get_inventory(),
      "total_stored": self.total_stored,
      "total_retrieved": self.total_retrieved,
    }
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "config": {
        "name": self.config.name,
        "position": list(self.config.position),
        "size": list(self.config.size),
        "capacity": self.config.capacity,
        "slot_grid": list(self.config.slot_grid),
      },
      "slots": {
        slot_id: slot.to_dict()
        for slot_id, slot in self.slots.items()
      },
      "status": self.get_status(),
    }
  
  @classmethod
  def from_config(cls, config_dict: Dict[str, Any]) -> "Warehouse":
    """从配置字典创建"""
    warehouse_config = WarehouseConfig(
      name=config_dict.get("name", "warehouse"),
      position=tuple(config_dict.get("position", [0, 0, 0])),
      size=tuple(config_dict.get("size", [8, 6, 4])),
      capacity=config_dict.get("capacity", 200),
      slot_grid=tuple(config_dict.get("slot_grid", [4, 3, 2])),
    )
    
    return cls(warehouse_config)
