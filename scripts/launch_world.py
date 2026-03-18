#!/usr/bin/env python3
"""
GENESIS World Launcher
启动仿真世界

Usage:
  python scripts/launch_world.py [--config CONFIG_PATH] [--headless] [--verbose]
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from genesis.world import WorldManager
from genesis.world.recipe_graph import calculate_robot_requirements


def parse_args():
  """解析命令行参数"""
  parser = argparse.ArgumentParser(
    description="GENESIS World Launcher",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  python scripts/launch_world.py
  python scripts/launch_world.py --config configs/world_config.yaml
  python scripts/launch_world.py --headless --verbose
  python scripts/launch_world.py --analyze-requirements
    """
  )
  
  parser.add_argument(
    "--config", "-c",
    default="configs/world_config.yaml",
    help="世界配置文件路径 (默认: configs/world_config.yaml)"
  )
  
  parser.add_argument(
    "--headless",
    action="store_true",
    help="无头模式运行 (不显示GUI)"
  )
  
  parser.add_argument(
    "--verbose", "-v",
    action="store_true",
    help="详细输出"
  )
  
  parser.add_argument(
    "--analyze-requirements",
    action="store_true",
    help="分析制造一个机器人的原材料需求"
  )
  
  parser.add_argument(
    "--simulate",
    type=float,
    default=0.0,
    help="运行仿真指定秒数 (0表示不运行)"
  )
  
  return parser.parse_args()


def print_world_state(world: WorldManager, verbose: bool = False) -> None:
  """打印世界状态"""
  print("\n" + "=" * 60)
  print("🌍 GENESIS World State")
  print("=" * 60)
  
  state = world.get_world_state()
  
  print(f"\n⏱️  Simulation Time: {state['sim_time']:.2f}s")
  print(f"⚡ Energy Balance: {state['energy_balance_wh']:.2f} Wh")
  
  # 矿区状态
  print("\n⛏️  Mines:")
  for name, mine_status in state.get("mines", {}).items():
    remaining = mine_status.get("remaining", 0)
    total = mine_status.get("total_units", 0)
    ore_type = mine_status.get("ore_type", "unknown")
    print(f"  - {name}: {remaining}/{total} {ore_type}")
  
  # 太阳能状态
  if state.get("solar_array"):
    solar = state["solar_array"]
    print(f"\n☀️  Solar Array:")
    print(f"  - Current Output: {solar.get('current_output_watts', 0):.1f} W")
    print(f"  - Total Generated: {solar.get('total_generated_wh', 0):.1f} Wh")
  
  # 充电站状态
  if state.get("charging_dock"):
    dock = state["charging_dock"]
    print(f"\n🔋 Charging Dock:")
    print(f"  - Status: {'Occupied' if dock.get('is_occupied') else 'Available'}")
    print(f"  - Total Charged: {dock.get('total_energy_charged_wh', 0):.1f} Wh")
  
  # 仓库状态
  if state.get("warehouse"):
    warehouse = state["warehouse"]
    print(f"\n📦 Warehouse:")
    print(f"  - Occupancy: {warehouse.get('occupancy', 0) * 100:.1f}%")
    print(f"  - Available Slots: {warehouse.get('available', 0)}")
    
    if verbose and warehouse.get("inventory"):
      print("  - Inventory:")
      for item_type, count in warehouse["inventory"].items():
        print(f"    • {item_type}: {count}")
  
  # 道路网络
  if state.get("path_network"):
    path = state["path_network"]
    print(f"\n🛤️  Path Network:")
    print(f"  - Nodes: {path.get('num_nodes', 0)}")
    print(f"  - Zones: {', '.join(path.get('zones', []))}")
  
  if verbose:
    print("\n" + "=" * 60)
    print("📊 Detailed World State")
    print("=" * 60)
    
    import json
    print(json.dumps(state, indent=2, default=str))


def run_simulation(world: WorldManager, duration: float, verbose: bool = False) -> None:
  """
  运行仿真
  
  Args:
    world: 世界管理器
    duration: 仿真时长 (秒)
    verbose: 是否详细输出
  """
  import time
  
  print(f"\n🚀 Running simulation for {duration:.1f} seconds...")
  
  dt = world.config.time_step
  steps = int(duration / dt)
  
  start_time = time.time()
  
  for i in range(steps):
    world.step(dt)
    
    # 每秒打印一次进度
    if verbose and i % int(1.0 / dt) == 0:
      sim_time = world.sim_time
      energy = world.energy_balance
      print(f"  t={sim_time:.1f}s, energy={energy:.2f} Wh")
  
  elapsed = time.time() - start_time
  print(f"\n✅ Simulation completed in {elapsed:.2f}s (real time)")
  print(f"   Simulated time: {world.sim_time:.2f}s")


def analyze_requirements() -> None:
  """分析制造一个机器人的原材料需求"""
  print("\n" + "=" * 60)
  print("🔬 Manufacturing Requirements Analysis")
  print("=" * 60)
  
  result = calculate_robot_requirements()
  
  print(f"\n🎯 Target: {result['target']}")
  
  print(f"\n📦 Raw Materials Required:")
  for item, qty in result["raw_materials"].items():
    print(f"  - {item}: {qty}")
  
  print(f"\n⏱️  Total Manufacturing Time: {result['total_time_minutes']:.1f} minutes")
  print(f"⚡ Total Energy Required: {result['total_energy_wh']:.1f} Wh")
  print(f"📝 Manufacturing Steps: {result['manufacturing_steps']}")
  
  print(f"\n🌲 Dependency Tree:")
  print(result["dependency_tree"])
  
  print(f"\n📊 Mermaid Graph:")
  print(result["mermaid_graph"])


def main():
  """主函数"""
  args = parse_args()
  
  # 分析需求模式
  if args.analyze_requirements:
    analyze_requirements()
    return 0
  
  # 检查配置文件
  config_path = Path(args.config)
  if not config_path.exists():
    print(f"❌ Error: Config file not found: {config_path}")
    print(f"   Please ensure the config file exists.")
    return 1
  
  print("=" * 60)
  print("🌍 GENESIS World Launcher")
  print("=" * 60)
  print(f"\n📁 Config: {config_path}")
  
  # 创建世界管理器
  print("\n🔧 Initializing World Manager...")
  world = WorldManager(config_path=str(config_path))
  
  # 构建世界 (使用抽象仿真上下文)
  print("🏗️  Building world...")
  
  class AbstractSimContext:
    """抽象仿真上下文 (用于测试)"""
    engine_type = "abstract"
    sim_time = 0.0
  
  world.build_world(AbstractSimContext())
  
  print("✅ World built successfully!")
  
  # 打印初始状态
  print_world_state(world, args.verbose)
  
  # 运行仿真
  if args.simulate > 0:
    run_simulation(world, args.simulate, args.verbose)
    print_world_state(world, args.verbose)
  
  print("\n" + "=" * 60)
  print("🎉 GENESIS World Launcher completed!")
  print("=" * 60)
  
  return 0


if __name__ == "__main__":
  sys.exit(main())
