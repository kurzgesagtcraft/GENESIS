"""
行为树框架模块 (L2)

提供基础的节点类型和黑板机制，用于技能编排。
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Callable
import time


class NodeStatus(Enum):
    """节点状态"""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class Blackboard:
    """黑板 (共享数据)"""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        
    def set(self, key: str, value: Any):
        self._data[key] = value
        
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
        
    def has(self, key: str) -> bool:
        return key in self._data
        
    def clear(self):
        self._data.clear()


class TreeNode:
    """行为树节点基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.status = NodeStatus.IDLE
        self.blackboard: Optional[Blackboard] = None
        
    def tick(self) -> NodeStatus:
        """执行一个 tick"""
        if self.status != NodeStatus.RUNNING:
            self.on_start()
            
        self.status = self.update()
        
        if self.status != NodeStatus.RUNNING:
            self.on_stop()
            
        return self.status
        
    def on_start(self):
        """节点开始执行时的回调"""
        pass
        
    def update(self) -> NodeStatus:
        """节点执行逻辑，需子类实现"""
        return NodeStatus.SUCCESS
        
    def on_stop(self):
        """节点停止执行时的回调"""
        pass
        
    def reset(self):
        """重置节点状态"""
        self.status = NodeStatus.IDLE


class CompositeNode(TreeNode):
    """复合节点基类"""
    
    def __init__(self, name: str, children: List[TreeNode] = None):
        super().__init__(name)
        self.children = children or []
        
    def add_child(self, child: TreeNode):
        self.children.append(child)
        
    def reset(self):
        super().reset()
        for child in self.children:
            child.reset()


class SequenceNode(CompositeNode):
    """顺序节点: 依次执行子节点，直到一个失败或全部成功"""
    
    def __init__(self, name: str, children: List[TreeNode] = None):
        super().__init__(name, children)
        self.current_child_index = 0
        
    def update(self) -> NodeStatus:
        if not self.children:
            return NodeStatus.SUCCESS
            
        while self.current_child_index < len(self.children):
            child = self.children[self.current_child_index]
            status = child.tick()
            
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            elif status == NodeStatus.FAILURE:
                return NodeStatus.FAILURE
            
            self.current_child_index += 1
            
        return NodeStatus.SUCCESS
        
    def on_stop(self):
        self.current_child_index = 0


class SelectorNode(CompositeNode):
    """选择节点: 依次执行子节点，直到一个成功或全部失败"""
    
    def __init__(self, name: str, children: List[TreeNode] = None):
        super().__init__(name, children)
        self.current_child_index = 0
        
    def update(self) -> NodeStatus:
        if not self.children:
            return NodeStatus.FAILURE
            
        while self.current_child_index < len(self.children):
            child = self.children[self.current_child_index]
            status = child.tick()
            
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            elif status == NodeStatus.SUCCESS:
                return NodeStatus.SUCCESS
            
            self.current_child_index += 1
            
        return NodeStatus.FAILURE
        
    def on_stop(self):
        self.current_child_index = 0


class ActionNode(TreeNode):
    """动作节点: 执行具体的原子动作"""
    
    def __init__(self, name: str, action_fn: Callable[..., NodeStatus]):
        super().__init__(name)
        self.action_fn = action_fn
        
    def update(self) -> NodeStatus:
        return self.action_fn(self.blackboard)


class ConditionNode(TreeNode):
    """条件节点: 检查条件是否满足"""
    
    def __init__(self, name: str, condition_fn: Callable[..., bool]):
        super().__init__(name)
        self.condition_fn = condition_fn
        
    def update(self) -> NodeStatus:
        return NodeStatus.SUCCESS if self.condition_fn(self.blackboard) else NodeStatus.FAILURE


class ParallelNode(CompositeNode):
    """并行节点: 同时执行所有子节点"""
    
    def __init__(self, name: str, children: List[TreeNode] = None, success_threshold: int = None):
        super().__init__(name, children)
        self.success_threshold = success_threshold or len(self.children)
        
    def update(self) -> NodeStatus:
        success_count = 0
        failure_count = 0
        
        for child in self.children:
            if child.status == NodeStatus.SUCCESS:
                success_count += 1
                continue
            if child.status == NodeStatus.FAILURE:
                failure_count += 1
                continue
                
            status = child.tick()
            if status == NodeStatus.SUCCESS:
                success_count += 1
            elif status == NodeStatus.FAILURE:
                failure_count += 1
                
        if success_count >= self.success_threshold:
            return NodeStatus.SUCCESS
        if failure_count > (len(self.children) - self.success_threshold):
            return NodeStatus.FAILURE
            
        return NodeStatus.RUNNING


class RepeatNode(TreeNode):
    """重复节点: 重复执行子节点"""
    
    def __init__(self, name: str, child: TreeNode, count: int = -1):
        super().__init__(name)
        self.child = child
        self.count = count  # -1 表示无限循环
        self.current_count = 0
        
    def update(self) -> NodeStatus:
        status = self.child.tick()
        
        if status == NodeStatus.RUNNING:
            return NodeStatus.RUNNING
            
        self.current_count += 1
        self.child.reset()
        
        if self.count != -1 and self.current_count >= self.count:
            return NodeStatus.SUCCESS
            
        return NodeStatus.RUNNING
        
    def on_stop(self):
        self.current_count = 0
        self.child.reset()


class BehaviorTree:
    """行为树管理器"""
    
    def __init__(self, root: TreeNode, blackboard: Blackboard = None):
        self.root = root
        self.blackboard = blackboard or Blackboard()
        self._inject_blackboard(self.root)
        
    def _inject_blackboard(self, node: TreeNode):
        node.blackboard = self.blackboard
        if isinstance(node, CompositeNode):
            for child in node.children:
                self._inject_blackboard(child)
        elif isinstance(node, RepeatNode):
            self._inject_blackboard(node.child)
            
    def tick(self) -> NodeStatus:
        return self.root.tick()
        
    def reset(self):
        self.root.reset()
