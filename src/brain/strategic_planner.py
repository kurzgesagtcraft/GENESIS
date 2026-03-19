"""
战略规划器模块 (L3)

负责根据全局目标、世界状态和制造配方生成高层任务计划。
利用 LLM 进行逻辑推理和长程规划。
"""

import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from .llm_client import LLMClient


@dataclass
class Task:
    """原子任务定义"""
    task_id: int
    type: str  # mine, deliver_to_station, start_processing, collect, wait_or_parallel, charge, store, retrieve
    description: str = ""
    target: Optional[str] = None # 目标物品类型或区域
    quantity: int = 1
    station: Optional[str] = None # 目标工站
    recipe: Optional[str] = None # 目标配方
    items: List[str] = field(default_factory=list) # 携带的物品列表
    status: str = "pending" # pending, running, completed, failed
    expected_output: Optional[str] = None  # 预期产出
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class TaskPlan:
    """任务计划"""
    goal: str
    tasks: List[Task] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: 0.0)
    
    def is_complete(self) -> bool:
        return all(t.status == "completed" for t in self.tasks)
    
    def get_next_task(self) -> Optional[Task]:
        for t in self.tasks:
            if t.status == "pending":
                return t
        return None

    @classmethod
    def parse(cls, goal: str, data: List[Dict[str, Any]]) -> 'TaskPlan':
        tasks = []
        for item in data:
            tasks.append(Task(**item))
        return cls(goal=goal, tasks=tasks)

    def to_text(self) -> str:
        lines = [f"Goal: {self.goal}"]
        for t in self.tasks:
            lines.append(f"- [{t.status}] Task {t.task_id}: {t.type} {t.description}")
        return "\n".join(lines)


class StrategicPlanner:
    """
    战略规划器
    
    使用 LLM 根据当前世界状态和目标生成 TaskPlan。
    """
    
    def __init__(self, llm_client: LLMClient, recipe_graph: Any, world_state_fn: Callable[[], Dict[str, Any]]):
        """
        Args:
            llm_client: LLM 客户端
            recipe_graph: 制造依赖图对象 (需支持 to_text() 或类似方法)
            world_state_fn: 获取当前世界状态的回调函数
        """
        self.llm = llm_client
        self.recipe_graph = recipe_graph
        self.get_world_state = world_state_fn
        
    def generate_master_plan(self, goal: str = "assembled_robot") -> TaskPlan:
        """
        生成完成目标所需的完整任务计划
        """
        world_state = self.get_world_state()
        
        # 构建 Prompt
        recipe_text = self.recipe_graph.to_text() if hasattr(self.recipe_graph, "to_text") else str(self.recipe_graph)
        
        prompt = f"""
你是一个 GENESIS 自动化工厂的战略规划 AI。你的任务是为机器人生成一个最优的行动序列来达成目标。

## 目标
制造一个 {goal}

## 制造配方 (依赖关系)
{recipe_text}

## 当前世界状态
- 仿真时间: {world_state.get('sim_time', 0)}s
- 机器人电量: {world_state.get('battery_soc', 1.0) * 100:.1f}%
- 矿区剩余: {world_state.get('mine_remaining', {})}
- 仓库库存: {world_state.get('warehouse_inventory', {})}
- 工站状态: {world_state.get('station_status', {})}

## 约束与规则
1. 机器人一次最多携带 2 个物品。
2. 电量低于 15% 必须去充电 (type: "charge")。
3. 工站同时只能执行一个配方。
4. 尽量减少总耗时，可以在工站加工时并行执行采矿或运输任务。
5. 任务类型必须是以下之一: 
   - "mine": 采矿 (target, quantity)
   - "deliver_to_station": 送货到工站 (items, station)
   - "start_processing": 开始加工 (station, recipe)
   - "collect": 从工站收集产物 (station, target, quantity)
   - "charge": 充电
   - "store": 存入仓库 (target)
   - "retrieve": 从仓库取出 (target)
   - "wait_or_parallel": 等待或并行描述

## 输出格式
必须返回一个 JSON 数组，每个元素是一个任务对象。示例:
[
  {{"task_id": 1, "type": "mine", "target": "iron_ore", "quantity": 2, "description": "采集铁矿石"}},
  {{"task_id": 2, "type": "deliver_to_station", "items": ["iron_ore", "iron_ore"], "station": "smelter", "description": "送往冶炼站"}},
  ...
]

请给出逻辑严密且最高效的计划。
"""
        
        # 调用 LLM
        # 使用 chat_json 确保输出格式
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "target": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "station": {"type": "string"},
                    "recipe": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["task_id", "type"]
            }
        }
        
        response_data = self.llm.chat_json(prompt, schema, system_prompt="你是一个专业的工业机器人调度专家。")
        
        # 如果返回的是字典且包含 tasks 键（有些 LLM 喜欢包一层），处理一下
        if isinstance(response_data, dict) and "tasks" in response_data:
            response_data = response_data["tasks"]
        elif not isinstance(response_data, list):
            # 容错处理
            print(f"Warning: LLM returned unexpected format: {type(response_data)}")
            if isinstance(response_data, dict):
                response_data = [response_data]
            else:
                response_data = []

        plan = TaskPlan.parse(goal, response_data)
        return plan
        
    def replan(self, current_plan: TaskPlan, failure_info: str) -> TaskPlan:
        """
        当执行失败时重新规划
        """
        world_state = self.get_world_state()
        
        prompt = f"""
当前计划执行失败。需要根据错误信息和当前状态重新规划。

## 目标
{current_plan.goal}

## 错误信息
{failure_info}

## 原计划进度
{current_plan.to_text()}

## 当前世界状态
- 机器人电量: {world_state.get('battery_soc', 1.0) * 100:.1f}%
- 仓库库存: {world_state.get('warehouse_inventory', {})}
- 工站状态: {world_state.get('station_status', {})}

请分析失败原因并给出修正后的完整后续计划（JSON 数组）。
"""
        
        schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "type": {"type": "string"},
                    "description": {"type": "string"},
                    "target": {"type": "string"},
                    "quantity": {"type": "integer"},
                    "station": {"type": "string"},
                    "recipe": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["task_id", "type"]
            }
        }
        
        response_data = self.llm.chat_json(prompt, schema)
        
        if isinstance(response_data, dict) and "tasks" in response_data:
            response_data = response_data["tasks"]
            
        return TaskPlan.parse(current_plan.goal, response_data)
