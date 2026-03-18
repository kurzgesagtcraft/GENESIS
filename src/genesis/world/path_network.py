"""
GENESIS Path Network Module
道路网络与路径规划

实现:
- 路径节点 (waypoints) 定义
- 节点间连边 (路网图)
- A* 路径规划
- 可视化路径
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List, Set
import numpy as np
import heapq
from collections import defaultdict

from genesis.utils.types import Position3D
from genesis.utils.config import Configurable


@dataclass
class PathNode:
  """路径节点"""
  id: str
  position: Tuple[float, float]  # 2D position (x, y)
  zone_name: Optional[str] = None  # 关联的区域名称
  connections: List[str] = field(default_factory=list)  # 连接的节点ID
  
  def __hash__(self):
    return hash(self.id)
  
  def __eq__(self, other):
    if isinstance(other, PathNode):
      return self.id == other.id
    return False


@dataclass
class PathEdge:
  """路径边"""
  from_node: str
  to_node: str
  distance: float  # 距离 (m)
  width: float = 1.5  # 道路宽度 (m)
  speed_limit: float = 1.5  # 速度限制 (m/s)
  is_bidirectional: bool = True  # 是否双向
  
  def __hash__(self):
    return hash((self.from_node, self.to_node))


@dataclass
class PathNetworkConfig:
  """道路网络配置"""
  name: str = "path_network"
  type: str = "grid"  # grid / custom
  width: float = 1.5  # 默认道路宽度
  nodes: List[Dict[str, Any]] = field(default_factory=list)
  edges: List[Tuple[str, str]] = field(default_factory=list)


class PathNetwork(Configurable):
  """
  道路网络类 - 管理路径规划
  
  功能:
  - 维护路网图 (NetworkX 风格)
  - A* 最短路径规划
  - 路径可视化
  - 距离计算
  
  Attributes:
    config: 网络配置
    nodes: 节点字典
    edges: 边字典
  """
  
  def __init__(self, config: PathNetworkConfig):
    self.config = config
    self._sim_context: Optional[Any] = None
    
    # 节点和边存储
    self.nodes: Dict[str, PathNode] = {}
    self.edges: Dict[Tuple[str, str], PathEdge] = {}
    
    # 邻接表 (用于快速查找)
    self._adjacency: Dict[str, Set[str]] = defaultdict(set)
    
    # 初始化网络
    self._init_network()
  
  def _init_network(self) -> None:
    """初始化网络结构"""
    # 添加节点
    for node_data in self.config.nodes:
      node = PathNode(
        id=node_data.get("id", ""),
        position=tuple(node_data.get("position", [0, 0])),
        zone_name=node_data.get("zone_name"),
      )
      self.nodes[node.id] = node
    
    # 添加边
    for edge_tuple in self.config.edges:
      from_id, to_id = edge_tuple
      self.add_edge(from_id, to_id)
  
  def add_node(self, node: PathNode) -> None:
    """
    添加节点
    
    Args:
      node: 路径节点
    """
    self.nodes[node.id] = node
  
  def add_edge(
    self,
    from_id: str,
    to_id: str,
    bidirectional: bool = True
  ) -> None:
    """
    添加边
    
    Args:
      from_id: 起点节点ID
      to_id: 终点节点ID
      bidirectional: 是否双向
    """
    if from_id not in self.nodes or to_id not in self.nodes:
      return
    
    # 计算距离
    from_pos = self.nodes[from_id].position
    to_pos = self.nodes[to_id].position
    distance = np.sqrt(
      (to_pos[0] - from_pos[0])**2 +
      (to_pos[1] - from_pos[1])**2
    )
    
    # 创建边
    edge = PathEdge(
      from_node=from_id,
      to_node=to_id,
      distance=distance,
      width=self.config.width,
      is_bidirectional=bidirectional
    )
    
    self.edges[(from_id, to_id)] = edge
    self._adjacency[from_id].add(to_id)
    
    # 更新节点连接
    self.nodes[from_id].connections.append(to_id)
    
    if bidirectional:
      reverse_edge = PathEdge(
        from_node=to_id,
        to_node=from_id,
        distance=distance,
        width=self.config.width,
        is_bidirectional=True
      )
      self.edges[(to_id, from_id)] = reverse_edge
      self._adjacency[to_id].add(from_id)
      self.nodes[to_id].connections.append(from_id)
  
  def build(self, sim_context: Any) -> None:
    """
    在仿真环境中构建道路网络
    
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
      # 创建道路可视化
      # TODO: 添加道路几何体
      pass
    except ImportError:
      self._build_abstract()
  
  def _build_mujoco(self) -> None:
    """MuJoCo 构建"""
    self._build_abstract()
  
  def _build_abstract(self) -> None:
    """抽象构建"""
    pass
  
  def get_node_by_zone(self, zone_name: str) -> Optional[PathNode]:
    """
    根据区域名称获取节点
    
    Args:
      zone_name: 区域名称
      
    Returns:
      路径节点, 如果不存在返回 None
    """
    for node in self.nodes.values():
      if node.zone_name == zone_name:
        return node
    return None
  
  def get_nearest_node(
    self,
    position: Tuple[float, float]
  ) -> Optional[PathNode]:
    """
    获取最近的节点
    
    Args:
      position: 2D位置
      
    Returns:
      最近的节点
    """
    nearest = None
    min_dist = float('inf')
    
    for node in self.nodes.values():
      dist = np.sqrt(
        (node.position[0] - position[0])**2 +
        (node.position[1] - position[1])**2
      )
      if dist < min_dist:
        min_dist = dist
        nearest = node
    
    return nearest
  
  def plan_path(
    self,
    start_zone: str,
    end_zone: str
  ) -> List[PathNode]:
    """
    A* 路径规划 (区域到区域)
    
    Args:
      start_zone: 起点区域名称
      end_zone: 终点区域名称
      
    Returns:
      路径节点列表
    """
    start_node = self.get_node_by_zone(start_zone)
    end_node = self.get_node_by_zone(end_zone)
    
    if start_node is None or end_node is None:
      return []
    
    return self.plan_path_nodes(start_node.id, end_node.id)
  
  def plan_path_nodes(
    self,
    start_id: str,
    end_id: str
  ) -> List[PathNode]:
    """
    A* 路径规划 (节点到节点)
    
    Args:
      start_id: 起点节点ID
      end_id: 终点节点ID
      
    Returns:
      路径节点列表
    """
    if start_id not in self.nodes or end_id not in self.nodes:
      return []
    
    if start_id == end_id:
      return [self.nodes[start_id]]
    
    # A* 算法
    end_pos = self.nodes[end_id].position
    
    # 优先队列: (f_score, node_id)
    open_set = [(0, start_id)]
    
    # g_score: 从起点到当前节点的实际距离
    g_score = {start_id: 0}
    
    # f_score: g_score + 启发式估计
    f_score = {
      start_id: self._heuristic(start_id, end_id)
    }
    
    # 记录路径
    came_from: Dict[str, str] = {}
    
    # 已访问集合
    closed_set: Set[str] = set()
    
    while open_set:
      _, current_id = heapq.heappop(open_set)
      
      if current_id == end_id:
        # 重建路径
        return self._reconstruct_path(came_from, current_id)
      
      if current_id in closed_set:
        continue
      
      closed_set.add(current_id)
      
      # 遍历邻居
      for neighbor_id in self._adjacency[current_id]:
        if neighbor_id in closed_set:
          continue
        
        # 计算新的 g_score
        edge = self.edges.get((current_id, neighbor_id))
        if edge is None:
          continue
        
        tentative_g = g_score[current_id] + edge.distance
        
        if neighbor_id not in g_score or tentative_g < g_score[neighbor_id]:
          came_from[neighbor_id] = current_id
          g_score[neighbor_id] = tentative_g
          f_score[neighbor_id] = tentative_g + self._heuristic(neighbor_id, end_id)
          heapq.heappush(open_set, (f_score[neighbor_id], neighbor_id))
    
    # 没有找到路径
    return []
  
  def _heuristic(self, node_id: str, end_id: str) -> float:
    """
    启发式函数 (欧几里得距离)
    
    Args:
      node_id: 当前节点ID
      end_id: 目标节点ID
      
    Returns:
      估计距离
    """
    node_pos = self.nodes[node_id].position
    end_pos = self.nodes[end_id].position
    
    return np.sqrt(
      (end_pos[0] - node_pos[0])**2 +
      (end_pos[1] - node_pos[1])**2
    )
  
  def _reconstruct_path(
    self,
    came_from: Dict[str, str],
    current_id: str
  ) -> List[PathNode]:
    """
    重建路径
    
    Args:
      came_from: 路径记录
      current_id: 当前节点ID
      
    Returns:
      路径节点列表
    """
    path = [self.nodes[current_id]]
    
    while current_id in came_from:
      current_id = came_from[current_id]
      path.append(self.nodes[current_id])
    
    path.reverse()
    return path
  
  def get_path_length(self, path: List[PathNode]) -> float:
    """
    计算路径总长度
    
    Args:
      path: 路径节点列表
      
    Returns:
      总长度 (m)
    """
    if len(path) < 2:
      return 0.0
    
    total_length = 0.0
    for i in range(len(path) - 1):
      edge = self.edges.get((path[i].id, path[i+1].id))
      if edge:
        total_length += edge.distance
      else:
        # 直接计算距离
        dx = path[i+1].position[0] - path[i].position[0]
        dy = path[i+1].position[1] - path[i].position[1]
        total_length += np.sqrt(dx*dx + dy*dy)
    
    return total_length
  
  def get_path_positions(self, path: List[PathNode]) -> List[Tuple[float, float]]:
    """
    获取路径的位置序列
    
    Args:
      path: 路径节点列表
      
    Returns:
      位置列表
    """
    return [node.position for node in path]
  
  def get_all_zones(self) -> List[str]:
    """获取所有区域名称"""
    zones = []
    for node in self.nodes.values():
      if node.zone_name:
        zones.append(node.zone_name)
    return zones
  
  def get_status(self) -> Dict[str, Any]:
    """获取状态"""
    return {
      "name": self.config.name,
      "num_nodes": len(self.nodes),
      "num_edges": len(self.edges) // 2,  # 双向边计数
      "zones": self.get_all_zones(),
    }
  
  def to_dict(self) -> Dict[str, Any]:
    """序列化为字典"""
    return {
      "config": {
        "name": self.config.name,
        "type": self.config.type,
        "width": self.config.width,
      },
      "nodes": {
        node_id: {
          "position": list(node.position),
          "zone_name": node.zone_name,
          "connections": node.connections,
        }
        for node_id, node in self.nodes.items()
      },
      "status": self.get_status(),
    }
  
  @classmethod
  def from_config(cls, config_dict: Dict[str, Any]) -> "PathNetwork":
    """从配置字典创建"""
    network_config = PathNetworkConfig(
      name=config_dict.get("name", "path_network"),
      type=config_dict.get("type", "grid"),
      width=config_dict.get("width", 1.5),
      nodes=config_dict.get("nodes", []),
      edges=[tuple(e) for e in config_dict.get("edges", [])],
    )
    
    return cls(network_config)
