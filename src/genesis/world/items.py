"""
GENESIS Items Module
物品数据模型与注册表

实现:
- Item 数据类
- ItemRegistry 全局注册表
- 物品属性定义
- 物品创建工厂
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
import uuid
from enum import Enum

from genesis.utils.types import Position3D, Color
from genesis.utils.config import Configurable


class ItemType(Enum):
  """物品类型枚举"""
  # 原材料
  IRON_ORE = "iron_ore"
  SILICON_ORE = "silicon_ore"
  
  # 中间产品
  IRON_BAR = "iron_bar"
  CIRCUIT_BOARD = "circuit_board"
  MOTOR = "motor"
  JOINT_MODULE = "joint_module"
  FRAME_SEGMENT = "frame_segment"
  CONTROLLER_BOARD = "controller_board"
  GRIPPER_FINGER = "gripper_finger"
  
  # 最终产品
  ASSEMBLED_ARM = "assembled_arm"
  ASSEMBLED_ROBOT = "assembled_robot"


@dataclass
class ItemProperties:
  """物品属性"""
  item_type: ItemType
  mass: float  # kg
  size: Tuple[float, float, float]  # bounding box (m)
  color: Color
  mesh_path: Optional[str] = None  # USD/URDF path
  friction: float = 0.6
  restitution: float = 0.2
  is_graspable: bool = True
  is_assembly_component: bool = False
  value: float = 1.0  # 基础价值
  
  def to_dict(self) -> Dict[str, Any]:
    return {
      "item_type": self.item_type.value,
      "mass": self.mass,
      "size": list(self.size),
      "color": [self.color.r, self.color.g, self.color.b, self.color.a],
      "mesh_path": self.mesh_path,
      "friction": self.friction,
      "restitution": self.restitution,
      "is_graspable": self.is_graspable,
      "is_assembly_component": self.is_assembly_component,
      "value": self.value,
    }


@dataclass
class Item:
  """
  物品数据类
  
  Attributes:
    item_id: 唯一标识符
    item_type: 物品类型
    mass: 质量 (kg)
    size: 包围盒尺寸 (m)
    mesh_path: 网格路径
    properties: 可扩展属性
    position: 当前位置 (可选)
    rigid_body_id: 物理体ID (仿真引擎返回)
  """
  item_id: str
  item_type: str
  mass: float
  size: Tuple[float, float, float]
  mesh_path: Optional[str] = None
  properties: Dict[str, Any] = field(default_factory=dict)
  position: Optional[Position3D] = None
  rigid_body_id: Optional[int] = None
  is_held: bool = False  # 是否被机器人持有
  holder_robot_id: Optional[str] = None  # 持有者ID
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "item_id": self.item_id,
      "item_type": self.item_type,
      "mass": self.mass,
      "size": list(self.size),
      "mesh_path": self.mesh_path,
      "properties": self.properties,
      "position": [self.position.x, self.position.y, self.position.z] if self.position else None,
      "is_held": self.is_held,
      "holder_robot_id": self.holder_robot_id,
    }
  
  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> "Item":
    """从字典创建"""
    position = None
    if data.get("position"):
      pos = data["position"]
      position = Position3D(pos[0], pos[1], pos[2])
    
    return cls(
      item_id=data.get("item_id", str(uuid.uuid4())),
      item_type=data.get("item_type", "unknown"),
      mass=data.get("mass", 1.0),
      size=tuple(data.get("size", [0.1, 0.1, 0.1])),
      mesh_path=data.get("mesh_path"),
      properties=data.get("properties", {}),
      position=position,
      is_held=data.get("is_held", False),
      holder_robot_id=data.get("holder_robot_id"),
    )


class ItemRegistry:
  """
  物品注册表 - 全局物品定义和工厂
  
  功能:
  - 存储所有物品类型的默认属性
  - 创建物品实例
  - 查询物品属性
  
  Usage:
    registry = ItemRegistry()
    item = registry.create("iron_ore")
  """
  
  # 默认物品属性定义
  DEFAULT_PROPERTIES: Dict[ItemType, ItemProperties] = {
    # 原材料
    ItemType.IRON_ORE: ItemProperties(
      item_type=ItemType.IRON_ORE,
      mass=2.0,
      size=(0.1, 0.1, 0.1),
      color=Color(0.6, 0.3, 0.2, 1.0),  # 棕红色
      friction=0.8,
      restitution=0.2,
      value=1.0,
    ),
    ItemType.SILICON_ORE: ItemProperties(
      item_type=ItemType.SILICON_ORE,
      mass=1.5,
      size=(0.08, 0.08, 0.08),
      color=Color(0.5, 0.5, 0.55, 1.0),  # 灰色
      friction=0.7,
      restitution=0.15,
      value=1.5,
    ),
    
    # 中间产品
    ItemType.IRON_BAR: ItemProperties(
      item_type=ItemType.IRON_BAR,
      mass=1.0,
      size=(0.3, 0.03, 0.03),
      color=Color(0.7, 0.7, 0.75, 1.0),  # 银灰色
      friction=0.5,
      restitution=0.1,
      is_assembly_component=True,
      value=3.0,
    ),
    ItemType.CIRCUIT_BOARD: ItemProperties(
      item_type=ItemType.CIRCUIT_BOARD,
      mass=0.1,
      size=(0.1, 0.08, 0.01),
      color=Color(0.1, 0.5, 0.2, 1.0),  # 绿色
      friction=0.4,
      restitution=0.05,
      is_assembly_component=True,
      value=5.0,
    ),
    ItemType.MOTOR: ItemProperties(
      item_type=ItemType.MOTOR,
      mass=0.5,
      size=(0.05, 0.05, 0.08),
      color=Color(0.3, 0.3, 0.35, 1.0),  # 深灰色
      friction=0.6,
      restitution=0.1,
      is_assembly_component=True,
      value=10.0,
    ),
    ItemType.JOINT_MODULE: ItemProperties(
      item_type=ItemType.JOINT_MODULE,
      mass=0.8,
      size=(0.08, 0.08, 0.1),
      color=Color(0.4, 0.4, 0.45, 1.0),
      friction=0.6,
      restitution=0.1,
      is_assembly_component=True,
      value=15.0,
    ),
    ItemType.FRAME_SEGMENT: ItemProperties(
      item_type=ItemType.FRAME_SEGMENT,
      mass=1.5,
      size=(0.4, 0.05, 0.05),
      color=Color(0.6, 0.6, 0.65, 1.0),
      friction=0.5,
      restitution=0.1,
      is_assembly_component=True,
      value=8.0,
    ),
    ItemType.CONTROLLER_BOARD: ItemProperties(
      item_type=ItemType.CONTROLLER_BOARD,
      mass=0.2,
      size=(0.12, 0.1, 0.02),
      color=Color(0.2, 0.2, 0.6, 1.0),  # 蓝色
      friction=0.4,
      restitution=0.05,
      is_assembly_component=True,
      value=20.0,
    ),
    ItemType.GRIPPER_FINGER: ItemProperties(
      item_type=ItemType.GRIPPER_FINGER,
      mass=0.3,
      size=(0.02, 0.02, 0.15),
      color=Color(0.5, 0.5, 0.55, 1.0),
      friction=0.7,
      restitution=0.15,
      is_assembly_component=True,
      value=5.0,
    ),
    
    # 最终产品
    ItemType.ASSEMBLED_ARM: ItemProperties(
      item_type=ItemType.ASSEMBLED_ARM,
      mass=5.0,
      size=(0.6, 0.1, 0.1),
      color=Color(0.55, 0.55, 0.6, 1.0),
      friction=0.5,
      restitution=0.1,
      is_graspable=False,  # 太大,不能直接抓取
      is_assembly_component=True,
      value=100.0,
    ),
    ItemType.ASSEMBLED_ROBOT: ItemProperties(
      item_type=ItemType.ASSEMBLED_ROBOT,
      mass=25.0,
      size=(0.5, 0.5, 1.2),
      color=Color(0.6, 0.6, 0.65, 1.0),
      friction=0.5,
      restitution=0.1,
      is_graspable=False,  # 最终产品
      is_assembly_component=False,
      value=500.0,
    ),
  }
  
  def __init__(self):
    """初始化注册表"""
    self._items: Dict[str, Item] = {}  # item_id -> Item
    self._type_counts: Dict[str, int] = {}  # item_type -> count
  
  def create(
    self,
    item_type: str,
    item_id: Optional[str] = None,
    position: Optional[Position3D] = None,
    **kwargs
  ) -> Item:
    """
    创建物品实例
    
    Args:
      item_type: 物品类型字符串
      item_id: 可选的物品ID (默认自动生成)
      position: 可选的初始位置
      **kwargs: 额外属性
      
    Returns:
      物品实例
    """
    # 获取默认属性
    try:
      item_type_enum = ItemType(item_type)
      props = self.DEFAULT_PROPERTIES.get(item_type_enum)
    except ValueError:
      # 未知类型,使用默认值
      props = None
    
    # 生成ID
    if item_id is None:
      item_id = f"{item_type}_{uuid.uuid4().hex[:8]}"
    
    # 创建物品
    if props:
      item = Item(
        item_id=item_id,
        item_type=item_type,
        mass=props.mass,
        size=props.size,
        mesh_path=props.mesh_path,
        properties={
          "color": [props.color.r, props.color.g, props.color.b, props.color.a],
          "friction": props.friction,
          "restitution": props.restitution,
          "is_graspable": props.is_graspable,
          "is_assembly_component": props.is_assembly_component,
          "value": props.value,
        },
        position=position,
      )
    else:
      # 使用默认值
      item = Item(
        item_id=item_id,
        item_type=item_type,
        mass=kwargs.get("mass", 1.0),
        size=kwargs.get("size", (0.1, 0.1, 0.1)),
        mesh_path=kwargs.get("mesh_path"),
        properties=kwargs.get("properties", {}),
        position=position,
      )
    
    # 注册物品
    self._items[item_id] = item
    self._type_counts[item_type] = self._type_counts.get(item_type, 0) + 1
    
    return item
  
  def get(self, item_id: str) -> Optional[Item]:
    """
    获取物品
    
    Args:
      item_id: 物品ID
      
    Returns:
      物品实例, 如果不存在返回 None
    """
    return self._items.get(item_id)
  
  def remove(self, item_id: str) -> Optional[Item]:
    """
    移除物品
    
    Args:
      item_id: 物品ID
      
    Returns:
      被移除的物品, 如果不存在返回 None
    """
    item = self._items.pop(item_id, None)
    if item:
      self._type_counts[item.item_type] = max(
        0, self._type_counts.get(item.item_type, 0) - 1
      )
    return item
  
  def get_by_type(self, item_type: str) -> List[Item]:
    """
    获取指定类型的所有物品
    
    Args:
      item_type: 物品类型
      
    Returns:
      物品列表
    """
    return [item for item in self._items.values() if item.item_type == item_type]
  
  def get_properties(self, item_type: str) -> Optional[ItemProperties]:
    """
    获取物品类型的默认属性
    
    Args:
      item_type: 物品类型字符串
      
    Returns:
      物品属性, 如果不存在返回 None
    """
    try:
      item_type_enum = ItemType(item_type)
      return self.DEFAULT_PROPERTIES.get(item_type_enum)
    except ValueError:
      return None
  
  def get_all_types(self) -> List[str]:
    """获取所有物品类型"""
    return [t.value for t in ItemType]
  
  def get_type_counts(self) -> Dict[str, int]:
    """获取各类型物品数量"""
    return dict(self._type_counts)
  
  def get_total_count(self) -> int:
    """获取物品总数"""
    return len(self._items)
  
  def clear(self) -> None:
    """清空所有物品"""
    self._items.clear()
    self._type_counts.clear()
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "items": {
        item_id: item.to_dict()
        for item_id, item in self._items.items()
      },
      "type_counts": self._type_counts,
      "total_count": len(self._items),
    }
