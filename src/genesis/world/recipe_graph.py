"""
GENESIS Recipe Graph Module
制造依赖关系图

实现:
- 从 RECIPES 自动构建 DAG
- 计算原材料总量
- 可视化依赖图
- 拓扑排序
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Set, Tuple
from collections import defaultdict, deque
import json

from genesis.world.recipes import Recipe, RecipeRegistry


@dataclass
class RecipeNode:
  """配方图节点"""
  item_type: str
  is_raw_material: bool = False
  recipes: List[str] = field(default_factory=list)  # 可生产此物品的配方
  
  def __hash__(self):
    return hash(self.item_type)
  
  def __eq__(self, other):
    if isinstance(other, RecipeNode):
      return self.item_type == other.item_type
    return False


@dataclass
class RecipeEdge:
  """配方图边"""
  from_item: str  # 输入物品
  to_item: str    # 输出物品
  recipe_name: str  # 关联的配方
  quantity_ratio: float  # 输入/输出比例


class RecipeGraph:
  """
  制造依赖关系图
  
  功能:
  - 构建 DAG (有向无环图)
  - 拓扑排序
  - 计算原材料需求
  - 生成可视化文本
  
  Attributes:
    registry: 配方注册表
    nodes: 节点字典
    edges: 边列表
    adjacency: 邻接表
  """
  
  def __init__(self, registry: Optional[RecipeRegistry] = None):
    """
    初始化依赖图
    
    Args:
      registry: 配方注册表 (可选, 默认创建新的)
    """
    self.registry = registry or RecipeRegistry()
    
    # 图结构
    self.nodes: Dict[str, RecipeNode] = {}
    self.edges: List[RecipeEdge] = []
    self._adjacency: Dict[str, List[str]] = defaultdict(list)  # item -> outputs
    self._reverse_adjacency: Dict[str, List[str]] = defaultdict(list)  # item -> inputs
    
    # 构建图
    self._build_graph()
  
  def _build_graph(self) -> None:
    """从配方注册表构建依赖图"""
    # 收集所有物品类型
    all_items: Set[str] = set()
    input_items: Set[str] = set()
    output_items: Set[str] = set()
    
    for recipe in self.registry.get_all_recipes():
      for item in recipe.inputs:
        input_items.add(item)
        all_items.add(item)
      for item in recipe.outputs:
        output_items.add(item)
        all_items.add(item)
    
    # 创建节点
    for item in all_items:
      is_raw = item not in output_items  # 只作为输入的是原材料
      recipes = [r.name for r in self.registry.get_recipes_for_output(item)]
      
      self.nodes[item] = RecipeNode(
        item_type=item,
        is_raw_material=is_raw,
        recipes=recipes,
      )
    
    # 创建边
    for recipe in self.registry.get_all_recipes():
      for input_item in recipe.inputs:
        for output_item in recipe.outputs:
          edge = RecipeEdge(
            from_item=input_item,
            to_item=output_item,
            recipe_name=recipe.name,
            quantity_ratio=recipe.inputs[input_item] / recipe.outputs[output_item],
          )
          self.edges.append(edge)
          self._adjacency[input_item].append(output_item)
          self._reverse_adjacency[output_item].append(input_item)
  
  def get_raw_materials(self) -> List[str]:
    """获取所有原材料类型"""
    return [
      node.item_type
      for node in self.nodes.values()
      if node.is_raw_material
    ]
  
  def get_final_products(self) -> List[str]:
    """获取所有最终产品 (没有后续配方的物品)"""
    return [
      node.item_type
      for node in self.nodes.values()
      if not self._adjacency.get(node.item_type) and not node.is_raw_material
    ]
  
  def topological_sort(self) -> List[str]:
    """
    拓扑排序 (从原材料到最终产品)
    
    Returns:
      排序后的物品类型列表
    """
    # Kahn 算法
    in_degree: Dict[str, int] = defaultdict(int)
    
    # 计算入度
    for node in self.nodes:
      in_degree[node] = len(self._reverse_adjacency.get(node, []))
    
    # 初始化队列 (入度为0的节点)
    queue = deque([
      node for node in self.nodes
      if in_degree[node] == 0
    ])
    
    result = []
    
    while queue:
      current = queue.popleft()
      result.append(current)
      
      for neighbor in self._adjacency.get(current, []):
        in_degree[neighbor] -= 1
        if in_degree[neighbor] == 0:
          queue.append(neighbor)
    
    return result
  
  def calculate_total_requirements(
    self,
    target_item: str,
    target_quantity: int = 1
  ) -> Dict[str, int]:
    """
    计算制造目标物品所需的原材料总量
    
    Args:
      target_item: 目标物品
      target_quantity: 目标数量
      
    Returns:
      原材料需求 {item_type: quantity}
    """
    return self.registry.calculate_raw_materials(target_item, target_quantity)
  
  def get_manufacturing_sequence(
    self,
    target_item: str
  ) -> List[Tuple[str, Recipe]]:
    """
    获取制造序列 (按拓扑顺序)
    
    Args:
      target_item: 目标物品
      
    Returns:
      制造序列 [(item_type, recipe), ...]
    """
    # 获取依赖树
    tree = self.registry.get_dependency_tree(target_item)
    
    # 后序遍历获取制造顺序
    sequence: List[Tuple[str, Recipe]] = []
    
    def _postorder(node: Dict[str, Any]) -> None:
      for child in node.get("children", []):
        _postorder(child)
      
      if node.get("type") == "crafted":
        recipe = self.registry.get_recipe(node["recipe"])
        if recipe:
          sequence.append((node["item"], recipe))
    
    _postorder(tree)
    
    return sequence
  
  def to_text_tree(
    self,
    target_item: str,
    target_quantity: int = 1,
    indent: int = 0
  ) -> str:
    """
    生成文本格式的依赖树
    
    Args:
      target_item: 目标物品
      target_quantity: 目标数量
      indent: 缩进级别
      
    Returns:
      文本格式的依赖树
    """
    tree = self.registry.get_dependency_tree(target_item, target_quantity)
    
    def _render(node: Dict[str, Any], level: int) -> List[str]:
      prefix = "  " * level
      lines = []
      
      item = node["item"]
      qty = node["quantity"]
      
      if node.get("type") == "raw_material":
        lines.append(f"{prefix}{item} ({qty})")
      else:
        recipe_name = node.get("recipe", "unknown")
        lines.append(f"{prefix}{item} ({qty}) ← {recipe_name}")
        
        for child in node.get("children", []):
          lines.extend(_render(child, level + 1))
      
      return lines
    
    return "\n".join(_render(tree, 0))
  
  def to_mermaid(self) -> str:
    """
    生成 Mermaid 格式的依赖图
    
    Returns:
      Mermaid 图定义字符串
    """
    lines = ["graph TD"]
    
    # 添加节点
    for node in self.nodes.values():
      shape = "[Raw]" if node.is_raw_material else ""
      lines.append(f"    {node.item_type}{shape}")
    
    # 添加边
    for edge in self.edges:
      lines.append(f"    {edge.from_item} -->|{edge.recipe_name}| {edge.to_item}")
    
    return "\n".join(lines)
  
  def to_dot(self) -> str:
    """
    生成 Graphviz DOT 格式的依赖图
    
    Returns:
      DOT 格式字符串
    """
    lines = ["digraph RecipeGraph {"]
    lines.append("    rankdir=LR;")
    lines.append("    node [shape=box];")
    
    # 原材料节点样式
    raw_materials = self.get_raw_materials()
    if raw_materials:
      raw_style = " [style=filled, fillcolor=lightgreen]"
      for item in raw_materials:
        lines.append(f'    "{item}"{raw_style};')
    
    # 最终产品节点样式
    final_products = self.get_final_products()
    if final_products:
      final_style = " [style=filled, fillcolor=lightcoral]"
      for item in final_products:
        lines.append(f'    "{item}"{final_style};')
    
    # 添加边
    for edge in self.edges:
      label = f' [label="{edge.recipe_name}"]'
      lines.append(f'    "{edge.from_item}" -> "{edge.to_item}"{label};')
    
    lines.append("}")
    return "\n".join(lines)
  
  def get_summary(self) -> Dict[str, Any]:
    """获取图摘要"""
    return {
      "total_items": len(self.nodes),
      "raw_materials": len(self.get_raw_materials()),
      "final_products": len(self.get_final_products()),
      "total_recipes": len(self.edges),
      "raw_material_types": self.get_raw_materials(),
      "final_product_types": self.get_final_products(),
    }
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "nodes": {
        item: {
          "item_type": node.item_type,
          "is_raw_material": node.is_raw_material,
          "recipes": node.recipes,
        }
        for item, node in self.nodes.items()
      },
      "edges": [
        {
          "from_item": edge.from_item,
          "to_item": edge.to_item,
          "recipe_name": edge.recipe_name,
          "quantity_ratio": edge.quantity_ratio,
        }
        for edge in self.edges
      ],
      "summary": self.get_summary(),
    }
  
  def to_json(self) -> str:
    """序列化为JSON"""
    return json.dumps(self.to_dict(), indent=2)


def calculate_robot_requirements() -> Dict[str, Any]:
  """
  计算制造一个 assembled_robot 的完整需求
  
  Returns:
    需求分析结果
  """
  registry = RecipeRegistry()
  graph = RecipeGraph(registry)
  
  target = "assembled_robot"
  
  # 计算原材料需求
  raw_materials = graph.calculate_total_requirements(target)
  
  # 计算总时间和能量
  total_time = registry.get_total_time(target)
  total_energy = registry.get_total_energy(target)
  
  # 获取制造序列
  sequence = graph.get_manufacturing_sequence(target)
  
  return {
    "target": target,
    "raw_materials": raw_materials,
    "total_time_seconds": total_time,
    "total_time_minutes": total_time / 60,
    "total_energy_joules": total_energy,
    "total_energy_wh": total_energy / 3600,
    "manufacturing_steps": len(sequence),
    "dependency_tree": graph.to_text_tree(target),
    "mermaid_graph": graph.to_mermaid(),
  }


if __name__ == "__main__":
  # 测试
  result = calculate_robot_requirements()
  print("=" * 60)
  print("制造一个 assembled_robot 的需求分析")
  print("=" * 60)
  print(f"\n原材料需求:")
  for item, qty in result["raw_materials"].items():
    print(f"  - {item}: {qty}")
  print(f"\n总时间: {result['total_time_minutes']:.1f} 分钟")
  print(f"总能量: {result['total_energy_wh']:.1f} Wh")
  print(f"\n依赖树:")
  print(result["dependency_tree"])
