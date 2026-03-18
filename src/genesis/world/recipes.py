"""
GENESIS Recipes Module
制造配方系统

实现:
- Recipe 数据类
- RecipeRegistry 配方注册表
- 配方依赖关系
- 制造时间与能量成本
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set
from enum import Enum
import json

from genesis.utils.config import Configurable


class StationType(Enum):
  """工站类型"""
  SMELTER = "smelter"
  CNC_3DPRINT = "cnc_3dprint"
  ASSEMBLY = "assembly"


@dataclass
class Recipe:
  """
  配方数据类
  
  定义从输入物品到输出物品的转换规则
  
  Attributes:
    name: 配方名称
    station_type: 所需工站类型
    inputs: 输入物品 {item_type: quantity}
    outputs: 输出物品 {item_type: quantity}
    process_time: 加工时间 (秒)
    energy_cost: 能量消耗 (焦耳)
  """
  name: str
  station_type: str
  inputs: Dict[str, int]
  outputs: Dict[str, int]
  process_time: float  # seconds
  energy_cost: float  # Joules
  
  def get_input_count(self) -> int:
    """获取输入物品总数"""
    return sum(self.inputs.values())
  
  def get_output_count(self) -> int:
    """获取输出物品总数"""
    return sum(self.outputs.values())
  
  def can_produce(self, item_type: str) -> bool:
    """检查是否能生产指定物品"""
    return item_type in self.outputs
  
  def get_output_quantity(self, item_type: str) -> int:
    """获取指定物品的产出数量"""
    return self.outputs.get(item_type, 0)
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "name": self.name,
      "station_type": self.station_type,
      "inputs": self.inputs,
      "outputs": self.outputs,
      "process_time": self.process_time,
      "energy_cost": self.energy_cost,
    }
  
  @classmethod
  def from_dict(cls, data: Dict[str, Any]) -> "Recipe":
    """从字典创建"""
    return cls(
      name=data.get("name", ""),
      station_type=data.get("station_type", ""),
      inputs=data.get("inputs", {}),
      outputs=data.get("outputs", {}),
      process_time=data.get("process_time", 30.0),
      energy_cost=data.get("energy_cost", 500.0),
    )


class RecipeRegistry:
  """
  配方注册表 - 管理所有制造配方
  
  功能:
  - 存储所有配方
  - 查询配方
  - 计算依赖关系
  - 计算原材料需求
  
  Usage:
    registry = RecipeRegistry()
    recipe = registry.get_recipe("smelt_iron")
  """
  
  # 默认配方定义
  DEFAULT_RECIPES: List[Recipe] = [
    # 冶炼配方
    Recipe(
      name="smelt_iron",
      station_type="smelter",
      inputs={"iron_ore": 3},
      outputs={"iron_bar": 2},
      process_time=30.0,
      energy_cost=500.0,
    ),
    
    # 制造配方 (CNC/3D打印)
    Recipe(
      name="make_circuit_board",
      station_type="cnc_3dprint",
      inputs={"silicon_ore": 2, "iron_bar": 1},
      outputs={"circuit_board": 1},
      process_time=45.0,
      energy_cost=800.0,
    ),
    Recipe(
      name="make_motor",
      station_type="cnc_3dprint",
      inputs={"iron_bar": 2, "circuit_board": 1},
      outputs={"motor": 1},
      process_time=60.0,
      energy_cost=1000.0,
    ),
    Recipe(
      name="make_joint_module",
      station_type="cnc_3dprint",
      inputs={"motor": 1, "iron_bar": 1},
      outputs={"joint_module": 1},
      process_time=40.0,
      energy_cost=600.0,
    ),
    Recipe(
      name="make_frame",
      station_type="cnc_3dprint",
      inputs={"iron_bar": 4},
      outputs={"frame_segment": 1},
      process_time=50.0,
      energy_cost=700.0,
    ),
    Recipe(
      name="make_controller",
      station_type="cnc_3dprint",
      inputs={"circuit_board": 2, "silicon_ore": 1},
      outputs={"controller_board": 1},
      process_time=90.0,
      energy_cost=1500.0,
    ),
    Recipe(
      name="make_gripper_finger",
      station_type="cnc_3dprint",
      inputs={"iron_bar": 1},
      outputs={"gripper_finger": 2},
      process_time=20.0,
      energy_cost=300.0,
    ),
    
    # 装配方
    Recipe(
      name="assemble_arm",
      station_type="assembly",
      inputs={"joint_module": 3, "frame_segment": 2, "gripper_finger": 2},
      outputs={"assembled_arm": 1},
      process_time=120.0,
      energy_cost=200.0,
    ),
    Recipe(
      name="assemble_robot",
      station_type="assembly",
      inputs={
        "assembled_arm": 2,
        "frame_segment": 4,
        "joint_module": 4,
        "controller_board": 1,
        "motor": 4,
      },
      outputs={"assembled_robot": 1},
      process_time=300.0,
      energy_cost=500.0,
    ),
  ]
  
  def __init__(self):
    """初始化注册表"""
    self._recipes: Dict[str, Recipe] = {}
    self._by_output: Dict[str, List[str]] = {}  # output_type -> recipe_names
    self._by_station: Dict[str, List[str]] = {}  # station_type -> recipe_names
    
    # 加载默认配方
    for recipe in self.DEFAULT_RECIPES:
      self.register(recipe)
  
  def register(self, recipe: Recipe) -> None:
    """
    注册配方
    
    Args:
      recipe: 配方对象
    """
    self._recipes[recipe.name] = recipe
    
    # 按输出索引
    for output_type in recipe.outputs:
      if output_type not in self._by_output:
        self._by_output[output_type] = []
      self._by_output[output_type].append(recipe.name)
    
    # 按工站索引
    if recipe.station_type not in self._by_station:
      self._by_station[recipe.station_type] = []
    self._by_station[recipe.station_type].append(recipe.name)
  
  def get_recipe(self, name: str) -> Optional[Recipe]:
    """
    获取配方
    
    Args:
      name: 配方名称
      
    Returns:
      配方对象, 如果不存在返回 None
    """
    return self._recipes.get(name)
  
  def get_recipes_for_output(self, item_type: str) -> List[Recipe]:
    """
    获取能生产指定物品的所有配方
    
    Args:
      item_type: 物品类型
      
    Returns:
      配方列表
    """
    recipe_names = self._by_output.get(item_type, [])
    return [self._recipes[name] for name in recipe_names]
  
  def get_recipes_for_station(self, station_type: str) -> List[Recipe]:
    """
    获取指定工站可执行的所有配方
    
    Args:
      station_type: 工站类型
      
    Returns:
      配方列表
    """
    recipe_names = self._by_station.get(station_type, [])
    return [self._recipes[name] for name in recipe_names]
  
  def get_all_recipes(self) -> List[Recipe]:
    """获取所有配方"""
    return list(self._recipes.values())
  
  def get_all_recipe_names(self) -> List[str]:
    """获取所有配方名称"""
    return list(self._recipes.keys())
  
  def can_craft(
    self,
    recipe_name: str,
    available_items: Dict[str, int]
  ) -> bool:
    """
    检查是否有足够材料执行配方
    
    Args:
      recipe_name: 配方名称
      available_items: 可用物品 {item_type: quantity}
      
    Returns:
      是否可以执行
    """
    recipe = self.get_recipe(recipe_name)
    if recipe is None:
      return False
    
    for item_type, quantity in recipe.inputs.items():
      if available_items.get(item_type, 0) < quantity:
        return False
    
    return True
  
  def calculate_raw_materials(
    self,
    target_item: str,
    target_quantity: int = 1,
    available_items: Optional[Dict[str, int]] = None
  ) -> Dict[str, int]:
    """
    计算制造目标物品所需的原材料
    
    递归计算所有依赖项的原材料需求
    
    Args:
      target_item: 目标物品类型
      target_quantity: 目标数量
      available_items: 已有物品 (可选)
      
    Returns:
      原材料需求 {item_type: quantity}
    """
    if available_items is None:
      available_items = {}
    
    raw_materials: Dict[str, int] = {}
    
    def _recurse(item: str, quantity: int) -> None:
      # 检查是否已有
      available = available_items.get(item, 0)
      if available >= quantity:
        # 已有足够,不需要额外制造
        available_items[item] = available - quantity
        return
      
      # 需要制造的额外数量
      needed = quantity - available
      if available > 0:
        available_items[item] = 0
      
      # 查找配方
      recipes = self.get_recipes_for_output(item)
      if not recipes:
        # 是原材料,直接记录
        raw_materials[item] = raw_materials.get(item, 0) + needed
        return
      
      # 使用第一个配方 (简化)
      recipe = recipes[0]
      
      # 计算需要执行的次数
      output_per_recipe = recipe.get_output_quantity(item)
      recipe_runs = (needed + output_per_recipe - 1) // output_per_recipe
      
      # 递归计算输入
      for input_type, input_qty in recipe.inputs.items():
        _recurse(input_type, input_qty * recipe_runs)
    
    _recurse(target_item, target_quantity)
    
    return raw_materials
  
  def get_dependency_tree(
    self,
    target_item: str,
    target_quantity: int = 1
  ) -> Dict[str, Any]:
    """
    获取依赖树
    
    Args:
      target_item: 目标物品
      target_quantity: 目标数量
      
    Returns:
      依赖树结构
    """
    def _build_tree(item: str, quantity: int) -> Dict[str, Any]:
      recipes = self.get_recipes_for_output(item)
      
      if not recipes:
        # 原材料
        return {
          "item": item,
          "quantity": quantity,
          "type": "raw_material",
        }
      
      recipe = recipes[0]
      output_per_recipe = recipe.get_output_quantity(item)
      recipe_runs = (quantity + output_per_recipe - 1) // output_per_recipe
      
      children = []
      for input_type, input_qty in recipe.inputs.items():
        child = _build_tree(input_type, input_qty * recipe_runs)
        children.append(child)
      
      return {
        "item": item,
        "quantity": quantity,
        "type": "crafted",
        "recipe": recipe.name,
        "recipe_runs": recipe_runs,
        "children": children,
      }
    
    return _build_tree(target_item, target_quantity)
  
  def get_total_time(
    self,
    target_item: str,
    target_quantity: int = 1
  ) -> float:
    """
    计算总制造时间 (串行)
    
    Args:
      target_item: 目标物品
      target_quantity: 目标数量
      
    Returns:
      总时间 (秒)
    """
    tree = self.get_dependency_tree(target_item, target_quantity)
    
    def _sum_time(node: Dict[str, Any]) -> float:
      if node.get("type") == "raw_material":
        return 0.0
      
      recipe = self.get_recipe(node["recipe"])
      if recipe is None:
        return 0.0
      
      time = recipe.process_time * node.get("recipe_runs", 1)
      
      for child in node.get("children", []):
        time += _sum_time(child)
      
      return time
    
    return _sum_time(tree)
  
  def get_total_energy(
    self,
    target_item: str,
    target_quantity: int = 1
  ) -> float:
    """
    计算总能量消耗
    
    Args:
      target_item: 目标物品
      target_quantity: 目标数量
      
    Returns:
      总能量 (焦耳)
    """
    tree = self.get_dependency_tree(target_item, target_quantity)
    
    def _sum_energy(node: Dict[str, Any]) -> float:
      if node.get("type") == "raw_material":
        return 0.0
      
      recipe = self.get_recipe(node["recipe"])
      if recipe is None:
        return 0.0
      
      energy = recipe.energy_cost * node.get("recipe_runs", 1)
      
      for child in node.get("children", []):
        energy += _sum_energy(child)
      
      return energy
    
    return _sum_energy(tree)
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "recipes": {
        name: recipe.to_dict()
        for name, recipe in self._recipes.items()
      },
      "by_output": self._by_output,
      "by_station": self._by_station,
    }
  
  def to_json(self) -> str:
    """序列化为JSON"""
    return json.dumps(self.to_dict(), indent=2)
