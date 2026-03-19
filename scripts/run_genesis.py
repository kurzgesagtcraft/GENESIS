#!/usr/bin/env python3
"""
GENESIS - Generalized Embodied Neural Entity for Self-Iterating Synthesis

主程序入口 - P7 全链路集成

运行方式:
    python scripts/run_genesis.py --goal assembled_robot
    python scripts/run_genesis.py --goal assembled_arm --verbose
    python scripts/run_genesis.py --config configs/pipeline_config.yaml
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入 GENESIS 模块
from genesis import load_config, setup_logger
from genesis.world import (
    WorldManager,
    ItemRegistry,
    RecipeRegistry,
    PathNetwork,
    Warehouse,
    ChargingDock,
    MineZone,
    SolarArray,
)
from genesis.robot import GenesisBot, Battery, SensorSuite
from genesis.control import Navigator, NavigationStatus
from genesis.control.skills import (
    BaseSkill,
    SkillContext,
    SkillResult,
    SkillStatus,
    TopGraspSkill,
    PlaceSkill,
    FeedStationSkill,
    RetrieveStationSkill,
    ChargeSkill,
    WarehouseStoreSkill,
    WarehouseRetrieveSkill,
)
from perception import (
    ObjectDetector,
    PoseEstimator,
    DockDetector,
    SemanticMap,
    ResourceTracker,
)
from workstation import (
    StationManager,
    StationInterface,
    Smelter,
    Fabricator,
    Assembler,
)
from brain import (
    StrategicPlanner,
    TaskPlan,
    Task,
    LLMClient,
    LLMConfig,
    BehaviorTree,
    Blackboard,
    TaskExecutor,
    ErrorHandler,
    ErrorType,
    Dashboard,
    NodeStatus,
)


# ============================================================================
# 数据记录器
# ============================================================================

@dataclass
class LogEntry:
    """单条日志记录"""
    timestamp: float
    sim_time: float
    robot_pos: List[float]
    robot_yaw: float
    battery_soc: float
    current_task: str
    task_progress: float
    inventory: Dict[str, int]
    station_status: Dict[str, Any]
    energy_balance: float
    errors: List[str] = field(default_factory=list)


class DataLogger:
    """数据记录器 - 记录运行日志"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"run_{self.timestamp}.jsonl"
        self.entries: List[LogEntry] = []
        self.summary: Dict[str, Any] = {}
        
    def log(self, entry: LogEntry) -> None:
        """记录一条日志"""
        self.entries.append(entry)
        
        # 写入文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    
    def save_summary(self, summary: Dict[str, Any]) -> None:
        """保存运行摘要"""
        self.summary = summary
        summary_file = self.log_dir / f"summary_{self.timestamp}.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)


# ============================================================================
# 仿真上下文 (Mock 版本，用于无 Isaac Sim 环境测试)
# ============================================================================

class SimContext:
    """仿真上下文 - 管理仿真时间和物理步进"""
    
    def __init__(
        self,
        physics_dt: float = 0.002,
        render_dt: float = 0.033,
        time_scale: float = 1.0,
    ):
        self.physics_dt = physics_dt
        self.render_dt = render_dt
        self.time_scale = time_scale
        self.sim_time = 0.0
        self.frame_count = 0
        self.running = True
        
    def step(self) -> None:
        """执行一个仿真步"""
        self.sim_time += self.physics_dt * self.time_scale
        self.frame_count += 1
        
    def get_time(self) -> float:
        """获取当前仿真时间"""
        return self.sim_time
    
    def reset(self) -> None:
        """重置仿真"""
        self.sim_time = 0.0
        self.frame_count = 0
        self.running = True


# ============================================================================
# GENESIS 系统配置
# ============================================================================

@dataclass
class GenesisConfig:
    """GENESIS 系统配置"""
    # 世界配置
    world_config_path: str = "configs/world_config.yaml"
    
    # 机器人配置
    robot_config_path: str = "configs/robot_config.yaml"
    
    # LLM 配置
    llm_config_path: str = "configs/llm_config.yaml"
    
    # 仿真参数
    physics_dt: float = 0.002
    render_dt: float = 0.033
    time_scale: float = 100.0  # 100x 加速
    
    # 任务参数
    goal: str = "assembled_robot"
    max_sim_time: float = 7200.0  # 最大仿真时间 (2小时)
    
    # 日志参数
    log_dir: str = "logs"
    log_interval: float = 1.0  # 日志间隔 (仿真秒)
    
    # Dashboard 参数
    dashboard_port: int = 8501
    enable_dashboard: bool = True
    
    @classmethod
    def from_yaml(cls, path: str) -> "GenesisConfig":
        """从 YAML 文件加载配置"""
        if os.path.exists(path):
            config_dict = load_config(path)
            return cls(**config_dict.get("genesis", {}))
        return cls()


# ============================================================================
# GENESIS 系统类
# ============================================================================

class GenesisSystem:
    """GENESIS 全链路集成系统"""
    
    def __init__(self, config: GenesisConfig, verbose: bool = False):
        self.config = config
        self.verbose = verbose
        
        # 设置日志
        self.logger = setup_logger("genesis", level="DEBUG" if verbose else "INFO")
        self.logger.info("🚀 初始化 GENESIS 系统...")
        
        # 仿真上下文
        self.sim = SimContext(
            physics_dt=config.physics_dt,
            render_dt=config.render_dt,
            time_scale=config.time_scale,
        )
        
        # 初始化各模块 (延迟初始化)
        self.world_manager: Optional[WorldManager] = None
        self.robot: Optional[GenesisBot] = None
        self.navigator: Optional[Navigator] = None
        self.perception: Optional[Dict[str, Any]] = None
        self.station_manager: Optional[StationManager] = None
        self.station_interface: Optional[StationInterface] = None
        self.skill_library: Optional[Dict[str, BaseSkill]] = None
        
        # 大脑模块
        self.llm_client: Optional[LLMClient] = None
        self.planner: Optional[StrategicPlanner] = None
        self.behavior_tree: Optional[BehaviorTree] = None
        self.blackboard: Optional[Blackboard] = None
        self.task_executor: Optional[TaskExecutor] = None
        self.error_handler: Optional[ErrorHandler] = None
        self.dashboard: Optional[Dashboard] = None
        
        # 数据记录
        self.data_logger: Optional[DataLogger] = None
        
        # 运行状态
        self.running = False
        self.paused = False
        self.current_plan: Optional[TaskPlan] = None
        self.last_log_time = 0.0
        
    def initialize(self) -> None:
        """初始化所有模块"""
        self.logger.info("=" * 60)
        self.logger.info("📦 初始化模块...")
        self.logger.info("=" * 60)
        
        # 1. 初始化世界管理器
        self._init_world()
        
        # 2. 初始化机器人
        self._init_robot()
        
        # 3. 初始化感知系统
        self._init_perception()
        
        # 4. 初始化工站系统
        self._init_stations()
        
        # 5. 初始化技能库
        self._init_skills()
        
        # 6. 初始化大脑
        self._init_brain()
        
        # 7. 初始化数据记录
        self._init_logging()
        
        self.logger.info("=" * 60)
        self.logger.info("✅ 所有模块初始化完成")
        self.logger.info("=" * 60)
        
    def _init_world(self) -> None:
        """初始化世界"""
        self.logger.info("🌍 初始化世界管理器...")
        
        # 创建世界管理器
        self.world_manager = WorldManager(self.config.world_config_path)
        
        # 构建世界 (在仿真中)
        self.world_manager.build_world(self.sim)
        
        self.logger.info(f"  - 世界尺寸: {self.world_manager.config.get('size', [50, 50])}")
        self.logger.info(f"  - 矿区数量: {len(self.world_manager.mines)}")
        self.logger.info(f"  - 工站数量: {len(self.world_manager.stations)}")
        
    def _init_robot(self) -> None:
        """初始化机器人"""
        self.logger.info("🤖 初始化机器人...")
        
        # 创建机器人实例
        self.robot = GenesisBot(
            config_path=self.config.robot_config_path,
            sim_context=self.sim,
        )
        
        # 创建导航器
        self.navigator = Navigator(
            path_network=self.world_manager.path_network,
            robot=self.robot,
        )
        
        self.logger.info(f"  - 机器人位置: {self.robot.get_base_pose()}")
        self.logger.info(f"  - 电池电量: {self.robot.get_battery_soc():.1%}")
        
    def _init_perception(self) -> None:
        """初始化感知系统"""
        self.logger.info("👁️ 初始化感知系统...")
        
        # 创建感知模块
        self.perception = {
            "detector": ObjectDetector(),
            "pose_estimator": PoseEstimator(),
            "dock_detector": DockDetector(),
            "semantic_map": SemanticMap(
                width=500,  # 50m / 0.1m 分辨率
                height=500,
                resolution=0.1,
            ),
            "resource_tracker": ResourceTracker(
                world_manager=self.world_manager,
            ),
        }
        
        self.logger.info("  - 物体检测器: 已加载")
        self.logger.info("  - 位姿估计器: 已加载")
        self.logger.info("  - 语义地图: 500x500 @ 0.1m")
        
    def _init_stations(self) -> None:
        """初始化工站系统"""
        self.logger.info("🏭 初始化工站系统...")
        
        # 创建工站管理器
        self.station_manager = StationManager()
        
        # 注册工站 (从世界管理器获取)
        for name, station_config in self.world_manager.stations.items():
            station_type = station_config.get("type", "unknown")
            
            if station_type == "smelter":
                station = Smelter(station_config)
            elif station_type == "fabricator":
                station = Fabricator(station_config)
            elif station_type == "assembler":
                station = Assembler(station_config)
            else:
                self.logger.warning(f"  - 未知工站类型: {station_type}")
                continue
                
            self.station_manager.register_station(station)
            self.logger.info(f"  - 注册工站: {name} ({station_type})")
        
        # 创建工站接口
        self.station_interface = StationInterface(self.station_manager)
        
    def _init_skills(self) -> None:
        """初始化技能库"""
        self.logger.info("🎯 初始化技能库...")
        
        # 创建技能上下文
        skill_context = SkillContext(
            robot=self.robot,
            perception=self.perception,
            navigator=self.navigator,
            world_manager=self.world_manager,
            station_interface=self.station_interface,
        )
        
        # 创建技能库
        self.skill_library = {
            "top_grasp": TopGraspSkill(skill_context),
            "place": PlaceSkill(skill_context),
            "feed_station": FeedStationSkill(skill_context),
            "retrieve_station": RetrieveStationSkill(skill_context),
            "charge": ChargeSkill(skill_context),
            "warehouse_store": WarehouseStoreSkill(skill_context),
            "warehouse_retrieve": WarehouseRetrieveSkill(skill_context),
        }
        
        self.logger.info(f"  - 已加载 {len(self.skill_library)} 个技能")
        
    def _init_brain(self) -> None:
        """初始化大脑模块"""
        self.logger.info("🧠 初始化智能决策大脑...")
        
        # 加载 LLM 配置
        llm_config_dict = load_config(self.config.llm_config_path)
        llm_config = LLMConfig(**llm_config_dict.get("llm", {}))
        
        # 创建 LLM 客户端
        self.llm_client = LLMClient(llm_config)
        
        # 创建战略规划器
        self.planner = StrategicPlanner(
            llm_client=self.llm_client,
            recipe_graph=self.world_manager.recipe_graph,
            world_state_fn=self._get_world_state,
        )
        
        # 创建黑板
        self.blackboard = Blackboard()
        
        # 创建任务执行器
        self.task_executor = TaskExecutor(
            robot=self.robot,
            navigator=self.navigator,
            skill_library=self.skill_library,
            station_interface=self.station_interface,
            blackboard=self.blackboard,
        )
        
        # 创建异常处理器
        self.error_handler = ErrorHandler(planner=self.planner)
        
        # 创建 Dashboard
        self.dashboard = Dashboard(
            world_manager=self.world_manager,
            robot=self.robot,
        )
        
        self.logger.info(f"  - LLM 提供商: {llm_config.provider}")
        self.logger.info(f"  - LLM 模型: {llm_config.model}")
        
    def _init_logging(self) -> None:
        """初始化数据记录"""
        self.logger.info("📊 初始化数据记录...")
        
        self.data_logger = DataLogger(self.config.log_dir)
        self.logger.info(f"  - 日志目录: {self.config.log_dir}")
        
    def _get_world_state(self) -> Dict[str, Any]:
        """获取当前世界状态"""
        return {
            "sim_time": self.sim.get_time(),
            "robot_pos": list(self.robot.get_base_pose()[0]),
            "robot_yaw": self.robot.get_base_pose()[1],
            "battery_soc": self.robot.get_battery_soc(),
            "mine_remaining": {
                m.name: m.remaining for m in self.world_manager.mines
            },
            "warehouse_inventory": self.world_manager.warehouse.get_inventory(),
            "station_status": self.station_manager.get_all_status(),
            "energy_balance": self.world_manager.energy_balance,
        }
        
    async def generate_plan(self, goal: str) -> TaskPlan:
        """生成任务计划"""
        self.logger.info(f"📋 生成任务计划: {goal}")
        
        # 使用 LLM 规划器生成计划
        plan = await self.planner.generate_master_plan(goal=goal)
        
        self.logger.info(f"  - 任务数量: {len(plan.tasks)}")
        for i, task in enumerate(plan.tasks):
            self.logger.info(f"    {i+1}. {task.type}: {task.description}")
            
        return plan
        
    async def run(self) -> Dict[str, Any]:
        """运行 GENESIS 系统"""
        self.logger.info("=" * 60)
        self.logger.info("🚀 开始运行 GENESIS 系统")
        self.logger.info("=" * 60)
        
        self.running = True
        start_time = time.time()
        
        try:
            # 1. 生成主计划
            self.current_plan = await self.generate_plan(self.config.goal)
            self.blackboard.set("plan", self.current_plan)
            
            # 2. 构建行为树
            self.behavior_tree = self.task_executor.build_tree_from_plan(
                self.current_plan
            )
            
            # 3. 主循环
            while self.running and not self.current_plan.is_complete():
                # 检查仿真时间限制
                if self.sim.get_time() > self.config.max_sim_time:
                    self.logger.warning("⏰ 达到最大仿真时间限制")
                    break
                    
                # 暂停检查
                while self.paused:
                    await asyncio.sleep(0.1)
                    
                # 物理仿真步进
                self.sim.step()
                
                # 更新世界状态
                self.world_manager.step(self.sim.physics_dt)
                
                # 更新感知
                self._update_perception()
                
                # 行为树 tick
                status = self.behavior_tree.tick()
                
                # 处理失败
                if status == NodeStatus.FAILURE:
                    await self._handle_failure()
                    
                # 数据记录
                self._log_state()
                
                # Dashboard 更新
                if int(self.sim.get_time()) % 1 == 0:
                    self._update_dashboard()
                    
            # 4. 完成
            return self._create_summary(start_time)
            
        except Exception as e:
            self.logger.error(f"❌ 运行错误: {e}")
            raise
            
    def _update_perception(self) -> None:
        """更新感知系统"""
        # 获取机器人传感器数据
        rgb, depth = self.robot.get_head_image()
        
        # 更新语义地图
        self.perception["semantic_map"].update(
            robot_pose=self.robot.get_base_pose(),
            depth_image=depth,
        )
        
        # 更新资源追踪
        self.perception["resource_tracker"].update(
            world_state=self._get_world_state(),
        )
        
    async def _handle_failure(self) -> None:
        """处理执行失败"""
        # 获取失败信息
        failure_info = self.blackboard.get("last_failure", {})
        error_type = failure_info.get("type", ErrorType.UNKNOWN)
        
        self.logger.warning(f"⚠️ 任务失败: {error_type}")
        
        # 使用异常处理器
        recovery = self.error_handler.handle_error(
            error_type=error_type,
            context=failure_info,
        )
        
        if recovery and "replan" in recovery.actions:
            # 重新规划
            self.current_plan = await self.planner.replan(
                current_plan=self.current_plan,
                failure_info=failure_info,
            )
            self.blackboard.set("plan", self.current_plan)
            
            # 重建行为树
            self.behavior_tree = self.task_executor.build_tree_from_plan(
                self.current_plan
            )
            
    def _log_state(self) -> None:
        """记录当前状态"""
        current_time = self.sim.get_time()
        
        # 按间隔记录
        if current_time - self.last_log_time < self.config.log_interval:
            return
            
        self.last_log_time = current_time
        
        # 创建日志条目
        entry = LogEntry(
            timestamp=time.time(),
            sim_time=current_time,
            robot_pos=list(self.robot.get_base_pose()[0]),
            robot_yaw=self.robot.get_base_pose()[1],
            battery_soc=self.robot.get_battery_soc(),
            current_task=self.blackboard.get("current_task", "idle"),
            task_progress=self.blackboard.get("task_progress", 0.0),
            inventory=self.world_manager.warehouse.get_inventory(),
            station_status=self.station_manager.get_all_status(),
            energy_balance=self.world_manager.energy_balance,
            errors=self.error_handler.get_error_summary(),
        )
        
        self.data_logger.log(entry)
        
    def _update_dashboard(self) -> None:
        """更新 Dashboard"""
        self.dashboard.update(
            robot_position=self.robot.get_base_pose()[0],
            robot_battery=self.robot.get_battery_soc(),
            current_task=self.blackboard.get("current_task", "idle"),
            task_progress=self.blackboard.get("task_progress", 0.0),
            inventory=self.world_manager.warehouse.get_inventory(),
            station_status=self.station_manager.get_all_status(),
            energy_balance=self.world_manager.energy_balance,
        )
        
    def _create_summary(self, start_time: float) -> Dict[str, Any]:
        """创建运行摘要"""
        end_time = time.time()
        
        summary = {
            "goal": self.config.goal,
            "success": self.current_plan.is_complete() if self.current_plan else False,
            "total_sim_time": self.sim.get_time(),
            "total_real_time": end_time - start_time,
            "time_scale": self.config.time_scale,
            "energy_balance": self.world_manager.energy_balance,
            "final_inventory": self.world_manager.warehouse.get_inventory(),
            "replan_count": self.error_handler.replan_count,
            "errors": self.error_handler.get_error_summary(),
        }
        
        # 保存摘要
        self.data_logger.save_summary(summary)
        
        return summary
        
    def stop(self) -> None:
        """停止系统"""
        self.running = False
        
    def pause(self) -> None:
        """暂停系统"""
        self.paused = True
        
    def resume(self) -> None:
        """恢复系统"""
        self.paused = False


# ============================================================================
# 主函数
# ============================================================================

async def main_async(args: argparse.Namespace) -> None:
    """异步主函数"""
    # 创建配置
    if args.config:
        config = GenesisConfig.from_yaml(args.config)
    else:
        config = GenesisConfig(
            goal=args.goal,
            time_scale=args.time_scale,
            max_sim_time=args.max_time,
            verbose=args.verbose,
        )
    
    # 创建系统
    system = GenesisSystem(config, verbose=args.verbose)
    
    try:
        # 初始化
        system.initialize()
        
        # 运行
        summary = await system.run()
        
        # 输出结果
        print("\n" + "=" * 60)
        print("🎉 GENESIS 运行完成!")
        print("=" * 60)
        print(f"目标: {summary['goal']}")
        print(f"成功: {'✅' if summary['success'] else '❌'}")
        print(f"总仿真时间: {summary['total_sim_time']:.1f}s")
        print(f"总实际时间: {summary['total_real_time']:.1f}s")
        print(f"能量平衡: {summary['energy_balance']:.1f} Wh")
        print(f"重规划次数: {summary['replan_count']}")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断")
        system.stop()
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        raise


def main() -> None:
    """主函数入口"""
    parser = argparse.ArgumentParser(
        description="GENESIS - 机器人自复制最小闭环模拟系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/run_genesis.py --goal assembled_robot
  python scripts/run_genesis.py --goal assembled_arm --verbose
  python scripts/run_genesis.py --config configs/pipeline_config.yaml
        """,
    )
    
    parser.add_argument(
        "--goal",
        type=str,
        default="assembled_robot",
        help="制造目标 (default: assembled_robot)",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="配置文件路径",
    )
    parser.add_argument(
        "--time-scale",
        type=float,
        default=100.0,
        help="仿真时间缩放因子 (default: 100.0)",
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=7200.0,
        help="最大仿真时间 (秒, default: 7200.0)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细输出",
    )
    
    args = parser.parse_args()
    
    # 运行异步主函数
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
