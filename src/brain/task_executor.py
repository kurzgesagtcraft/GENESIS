"""
任务执行器模块 (L2)

负责将 TaskPlan 转化为行为树并执行。
"""

from typing import List, Dict, Any, Optional
from .behavior_tree import (
    BehaviorTree, 
    Blackboard, 
    SequenceNode, 
    SelectorNode, 
    ActionNode, 
    ConditionNode, 
    NodeStatus,
    TreeNode
)
from .strategic_planner import TaskPlan, Task


class TaskExecutor:
    """
    任务执行器
    
    负责将高层任务计划转化为具体的行为树节点序列。
    """
    
    def __init__(self, robot: Any, perception: Any, navigator: Any, skill_library: Any, world_manager: Any):
        self.robot = robot
        self.perception = perception
        self.navigator = navigator
        self.skill_library = skill_library
        self.world_manager = world_manager
        self.blackboard = Blackboard()
        self.current_tree: Optional[BehaviorTree] = None
        
    def build_tree_from_plan(self, plan: TaskPlan) -> BehaviorTree:
        """
        根据任务计划构建主行为树
        """
        root = SequenceNode("MainPlanSequence")
        
        # 1. 安全检查子树
        safety_selector = SelectorNode("SafetyCheck")
        battery_ok = ConditionNode("BatteryOK", lambda bb: self.robot.get_battery_soc() > 0.15)
        # 充电任务节点 (这里需要具体的实现类，先用 ActionNode 占位)
        charge_task = ActionNode("EmergencyCharge", self._execute_charge_task)
        safety_selector.add_child(battery_ok)
        safety_selector.add_child(charge_task)
        
        root.add_child(safety_selector)
        
        # 2. 任务分发子树
        task_sequence = SequenceNode("TaskExecutionSequence")
        for task in plan.tasks:
            task_node = self._create_node_for_task(task)
            task_sequence.add_child(task_node)
            
        root.add_child(task_sequence)
        
        self.current_tree = BehaviorTree(root, self.blackboard)
        return self.current_tree
        
    def _create_node_for_task(self, task: Task) -> TreeNode:
        """
        根据任务类型创建对应的行为树节点或子树
        """
        # 这里可以根据任务类型分发到具体的子树构建逻辑
        # 实际项目中，每个任务类型应该有专门的类
        if task.type == "mine":
            return ActionNode(f"Mine_{task.target}", lambda bb: self._execute_mine_task(task))
        elif task.type == "deliver_to_station":
            return ActionNode(f"DeliverTo_{task.station}", lambda bb: self._execute_deliver_task(task))
        elif task.type == "start_processing":
            return ActionNode(f"Process_{task.recipe}", lambda bb: self._execute_process_task(task))
        elif task.type == "collect":
            return ActionNode(f"Collect_{task.target}", lambda bb: self._execute_collect_task(task))
        elif task.type == "charge":
            return ActionNode("Charge", self._execute_charge_task)
        else:
            return ActionNode(f"Generic_{task.type}", lambda bb: NodeStatus.SUCCESS)

    # --- 具体的任务执行逻辑 (原子动作封装) ---
    # 实际项目中，这些逻辑应该在 src/brain/behavior_tree/tasks/ 下定义

    def _execute_mine_task(self, task: Task) -> NodeStatus:
        # 1. 导航到矿区
        # 2. 感知矿石
        # 3. 抓取矿石
        # 4. 存入手持
        print(f"Executing Mine Task: {task.target} x {task.quantity}")
        return NodeStatus.SUCCESS

    def _execute_deliver_task(self, task: Task) -> NodeStatus:
        # 1. 导航到工站
        # 2. 对准入料口
        # 3. 投料
        print(f"Executing Deliver Task: {task.items} to {task.station}")
        return NodeStatus.SUCCESS

    def _execute_process_task(self, task: Task) -> NodeStatus:
        # 1. 触发工站加工
        # 2. 等待或返回运行中
        print(f"Executing Process Task: {task.recipe} at {task.station}")
        return NodeStatus.SUCCESS

    def _execute_collect_task(self, task: Task) -> NodeStatus:
        # 1. 导航到工站出料口
        # 2. 抓取产物
        print(f"Executing Collect Task: {task.target} from {task.station}")
        return NodeStatus.SUCCESS

    def _execute_charge_task(self, blackboard: Blackboard) -> NodeStatus:
        # 1. 导航到充电桩
        # 2. 对接
        # 3. 充电
        print("Executing Charge Task")
        return NodeStatus.SUCCESS
