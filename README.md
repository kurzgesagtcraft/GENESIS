# 🏭 Project GENESIS

## Generalized Embodied Neural Entity for Self-Iterating Synthesis

**机器人自复制最小闭环模拟系统**

---

## 项目简介

GENESIS 是一个完整的机器人自复制仿真框架，旨在探索自复制系统的最小闭环实现。项目基于 NVIDIA Isaac Sim 和 MuJoCo 构建物理仿真环境，结合 LLM/VLM 实现智能决策，最终实现从原材料到完整机器人的自主制造流程。

### 核心特性

- 🌍 **完整仿真世界**: 矿区、工站、仓库、充电站、太阳能发电
- 🤖 **双臂移动机器人**: 差速底盘 + 6-DOF 双臂 + 平行夹爪
- 🧠 **LLM 驱动决策**: 三层架构 (L3 规划 / L2 编排 / L1 控制)
- 🏭 **完整制造链**: 9 种配方，从矿石到完整机器人
- 📊 **全面评估系统**: 时间/能量/可靠性分析 + 优化模块

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ GENESIS 系统架构                                                    │
│                                                                     │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │
│ │ 🌍 World │───→│ 🤖 Robot │───→│ 🏭 Mfg  │───→│ 🧩 Assy │               │
│ │ Sim Env │ │ Agent │ │ Station │ │ Station │               │
│ └──────────┘ └────┬─────┘ └──────────┘ └──────────┘               │
│ │ │
│ ┌────────┴────────┐ │
│ │ 🧠 Brain Stack │ │
│ │ ┌────────────┐ │ │
│ │ │ L3: LLM/VLM│ │ ← 任务规划 / 异常处理 │
│ │ │ Planner │ │ │
│ │ ├────────────┤ │ │
│ │ │ L2: Skill │ │ ← 技能编排 / 状态机 │
│ │ │ Library │ │ │
│ │ ├────────────┤ │ │
│ │ │ L1: Motor │ │ ← RL策略 / 阻抗控制 │
│ │ │ Control │ │ │
│ │ └────────────┘ │ │
│ └─────────────────┘ │
│ │
│ ┌──────────────────────────────────────────────────┐ │
│ │ 📊 Metrics: 闭环完成率 / 零件精度 / 能量收支 │ │
│ └──────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 项目阶段

| 阶段 | 描述 | 状态 |
|------|------|------|
| P0 | 基础设施搭建 | ✅ 已完成 |
| P1 | 仿真世界构建 | ✅ 已完成 |
| P2 | 机器人本体建模 | ✅ 已完成 |
| P3 | 感知系统开发 | ✅ 已完成 |
| P4 | 运动与操作能力 | ✅ 已完成 |
| P5 | 工站系统仿真 | ✅ 已完成 |
| P6 | 智能决策大脑 | ✅ 已完成 |
| P7 | 全链路集成 | ✅ 已完成 |
| P8 | 评估与优化 | ✅ 已完成 |
| P9 | 展示与开源 | 🔄 进行中 |
| P10 | 拓展（能源/芯片环节）| ⏳ 待开始 |

---

## 环境要求

### 硬件
- GPU: NVIDIA RTX 3060+ (推荐 RTX 4090/A100)
- VRAM: 8GB+
- RAM: 32GB+
- Storage: 100GB+ SSD

### 软件
- OS: Ubuntu 22.04 LTS / WSL2
- Python: 3.10
- CUDA: 12.x
- NVIDIA Driver: 535+

---

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/kurzgesagtcraft/GENESIS.git
cd GENESIS

# 创建虚拟环境
conda env create -f environment.yml
conda activate genesis_env

# 安装依赖
pip install -e .

# 运行测试
make test

# 启动仿真
python scripts/launch_world.py

# 运行完整流程
python scripts/run_genesis.py --goal assembled_robot
```

---

## 目录结构

```
GENESIS/
├── assets/ # 3D模型, URDF/MJCF, 纹理
│ └── robot/ # 机器人模型
├── configs/ # YAML配置文件
│ ├── robot_config.yaml
│ ├── world_config.yaml
│ └── llm_config.yaml
├── src/
│ ├── world/ # P1: 世界构建
│ │ ├── world_manager.py
│ │ ├── mine_zone.py
│ │ ├── charging_dock.py
│ │ ├── solar_array.py
│ │ ├── warehouse.py
│ │ ├── path_network.py
│ │ ├── items.py
│ │ ├── recipes.py
│ │ └── recipe_graph.py
│ ├── robot/ # P2: 机器人本体
│ │ ├── robot_interface.py
│ │ ├── sensors.py
│ │ └── battery.py
│ ├── perception/ # P3: 感知
│ │ ├── segmentation.py
│ │ ├── pose_estimation.py
│ │ ├── dock_detection.py
│ │ ├── semantic_map.py
│ │ └── resource_tracker.py
│ ├── genesis/control/ # P4: 控制
│ │ ├── base_controller.py
│ │ ├── path_follower.py
│ │ ├── navigator.py
│ │ ├── ik_solver.py
│ │ ├── trajectory_planner.py
│ │ ├── impedance_controller.py
│ │ └── skills/
│ │ ├── top_grasp.py
│ │ ├── place.py
│ │ ├── side_grasp.py
│ │ ├── feed_station.py
│ │ ├── retrieve_station.py
│ │ ├── charge.py
│ │ └── warehouse_ops.py
│ ├── workstation/ # P5: 工站
│ │ ├── base_station.py
│ │ ├── smelter.py
│ │ ├── fabricator.py
│ │ ├── assembler.py
│ │ ├── station_interface.py
│ │ └── station_manager.py
│ ├── brain/ # P6: 决策大脑
│ │ ├── llm_client.py
│ │ ├── strategic_planner.py
│ │ ├── behavior_tree.py
│ │ ├── task_executor.py
│ │ ├── error_handler.py
│ │ └── dashboard.py
│ ├── analysis/ # P8: 分析
│ │ ├── time_analysis.py
│ │ ├── energy_analysis.py
│ │ └── reliability_analysis.py
│ └── optimization/ # P8: 优化
│ ├── path_optimizer.py
│ ├── parallel_scheduler.py
│ ├── skill_optimizer.py
│ └── energy_optimizer.py
├── scripts/ # 启动/测试脚本
│ ├── launch_world.py
│ ├── run_genesis.py
│ ├── test_brain.py
│ ├── test_evaluation.py
│ ├── test_perception.py
│ ├── test_robot.py
│ ├── test_skills.py
│ └── test_stations.py
├── tests/ # 测试
│ ├── integration/
│ │ ├── test_single_recipe.py
│ │ ├── test_chain_recipe.py
│ │ ├── test_make_arm.py
│ │ ├── test_full_genesis.py
│ │ └── test_energy_fault.py
│ └── benchmark/
│ └── test_performance.py
├── docs/ # 文档
│ ├── robot_spec.md
│ ├── P0.3_知识预研笔记.md
│ └── analysis/
│ └── P8_evaluation_report.md
├── Makefile
└── pyproject.toml
```

---

## 核心模块

### 世界构建 (P1)
- **WorldManager**: 统一管理所有世界元素
- **MineZone**: 铁矿/硅矿区
- **SolarArray**: 太阳能发电系统
- **ChargingDock**: 充电站
- **Warehouse**: 仓库存储系统
- **PathNetwork**: A* 路径规划网络

### 机器人系统 (P2-P4)
- **GenesisBot**: 统一控制接口
- **DifferentialDriveController**: 差速底盘控制
- **IKSolver**: 阻尼最小二乘 IK 求解器
- **TrajectoryPlanner**: 五次多项式轨迹规划
- **ImpedanceController**: 笛卡尔阻抗控制
- **7 种操作技能**: TopGrasp, Place, SideGrasp, FeedStation, RetrieveStation, Charge, WarehouseOps

### 工站系统 (P5)
- **Smelter**: 冶炼站 (铁矿石 → 铁锭)
- **Fabricator**: 加工站 (电路板/电机/关节模块)
- **Assembler**: 装配站 (机械臂/完整机器人)
- **StationInterface**: 统一交互接口

### 智能决策 (P6)
- **StrategicPlanner**: LLM 驱动的任务规划
- **BehaviorTree**: 行为树框架
- **ErrorHandler**: 5 种错误类型恢复策略
- **Dashboard**: 实时状态监控

### 评估优化 (P8)
- **TimeAnalyzer**: 时间瓶颈识别
- **EnergyAnalyzer**: 能量平衡分析
- **ReliabilityAnalyzer**: 可靠性统计
- **PathOptimizer**: TSP 路径优化
- **ParallelScheduler**: 并行任务调度
- **SkillOptimizer**: 技能参数优化
- **EnergyOptimizer**: 充电策略优化

---

## 测试

```bash
# 运行所有测试
make test

# 测试特定模块
python scripts/test_skills.py --test all
python scripts/test_stations.py --test all
python scripts/test_brain.py --test all
python scripts/test_evaluation.py --test all

# 运行集成测试
python tests/integration/test_full_genesis.py

# 运行性能基准测试
python tests/benchmark/test_performance.py
```

---

## 制造配方

项目支持 9 种制造配方，形成完整的依赖链：

```
assembled_robot (1)
├── assembled_arm (2)
│ ├── joint_module (6) → motor(6) + iron_bar(6)
│ ├── frame_segment (4) → iron_bar(16)
│ └── gripper_finger (4) → iron_bar(2)
├── frame_segment (4)
├── joint_module (4)
├── controller_board (1) → circuit_board(2) + silicon_ore(1)
└── motor (4) → iron_bar(8) + circuit_board(4)
```

---

## 开发指南

### 代码风格
- 使用 2 空格缩进
- 变量和函数使用 camelCase 命名
- 类名使用 PascalCase 命名
- 常量使用 UPPER_SNAKE_CASE 命名
- 行长度不超过 100 字符

### 提交规范
使用 Conventional Commits 格式：
- `feat: add new feature`
- `fix: resolve bug`
- `docs: update documentation`
- `test: add tests`

---

## 文档

- [架构设计](docs/architecture.md) - 系统设计决策
- [经验总结](docs/lessons_learned.md) - 开发过程中的经验
- [机器人规格](docs/robot_spec.md) - 机器人详细规格
- [评估报告](docs/analysis/P8_evaluation_report.md) - 性能评估报告

---

## 许可证

MIT License

---

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](docs/CONTRIBUTING.md) 了解详情。

---

## 联系方式

- 项目主页: https://github.com/kurzgesagtcraft/GENESIS
- 问题反馈: https://github.com/kurzgesagtcraft/GENESIS/issues
