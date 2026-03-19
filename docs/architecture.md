# GENESIS 系统架构设计文档

## 概述

本文档详细描述 GENESIS (Generalized Embodied Neural Entity for Self-Iterating Synthesis) 系统的架构设计决策。GENESIS 是一个机器人自复制最小闭环仿真系统，旨在探索自复制系统的可行性。

---

## 设计哲学

### 核心原则

1. **模块化设计**: 每个功能模块独立可测试，通过清晰定义的接口交互
2. **分层架构**: L3 规划 / L2 编排 / L1 控制三层决策架构
3. **仿真优先**: 在仿真环境中验证完整流程，为后续 sim-to-real 打基础
4. **可扩展性**: 支持添加新工站、新配方、新技能

### 设计决策记录

#### 决策 1: 为什么选择三层决策架构？

**背景**: 机器人需要从高层目标（"制造一个机器人"）分解到底层控制（"关节角度指令"）

**备选方案**:
- A: 端到端 RL 策略
- B: 传统 FSM + 硬编码规则
- C: LLM 规划 + 行为树编排 + 技能执行

**选择**: 方案 C

**理由**:
1. LLM 具备常识推理能力，可处理未预见情况
2. 行为树提供结构化的任务编排，易于调试
3. 底层技能可独立开发和测试
4. 各层可独立替换（如 LLM 可换为更优模型）

**权衡**:
- 优点: 可解释性强、易于调试、灵活
- 缺点: 层间通信开销、需要精心设计接口

---

#### 决策 2: 为什么选择行为树而非 FSM？

**背景**: L2 层需要编排多个技能完成复杂任务

**备选方案**:
- A: 有限状态机 (FSM)
- B: 行为树 (Behavior Tree)
- C: Petri 网

**选择**: 方案 B

**理由**:
1. 行为树天然支持层次化任务结构
2. 每个节点独立可测试
3. 支持并行执行（ParallelNode）
4. 更容易添加新任务类型
5. 广泛应用于游戏 AI 和机器人领域

**行为树节点类型**:
```python
SequenceNode  # 顺序执行，任一失败则失败
SelectorNode  # 选择执行，任一成功则成功
ParallelNode  # 并行执行，可配置成功条件
RepeatNode    # 重复执行
ActionNode    # 原子动作
ConditionNode # 条件检查
```

---

#### 决策 3: 为什么选择阻尼最小二乘法 IK？

**背景**: 手臂需要从目标位姿计算关节角度

**备选方案**:
- A: 解析 IK（如 IKFast）
- B: 雅可比转置法
- C: 阻尼最小二乘法 (DLS)
- D: 优化求解器（如 IPOPT）

**选择**: 方案 C

**理由**:
1. 处理奇异点能力强（通过阻尼因子）
2. 计算效率高（迭代次数少）
3. 易于添加关节限位约束
4. 广泛验证的算法

**实现细节**:
```python
# 阻尼最小二乘法核心公式
Δq = J^T (J J^T + λ²I)^{-1} Δx

# 其中:
# J: 雅可比矩阵
# λ: 阻尼因子（处理奇异点）
# Δx: 末端位姿误差
# Δq: 关节角度增量
```

---

#### 决策 4: 为什么使用五次多项式轨迹？

**背景**: 手臂运动需要平滑轨迹

**备选方案**:
- A: 三次多项式（位置、速度连续）
- B: 五次多项式（位置、速度、加速度连续）
- C: 样条插值
- D: 最小 jerk 轨迹

**选择**: 方案 B

**理由**:
1. 保证位置、速度、加速度连续
2. 计算简单，解析解
3. 加速度连续减少机械振动
4. 适合大多数操作场景

**五次多项式公式**:
```python
# 位置
q(t) = a0 + a1*t + a2*t² + a3*t³ + a4*t⁴ + a5*t⁵

# 速度
qd(t) = a1 + 2*a2*t + 3*a3*t² + 4*a4*t³ + 5*a5*t⁴

# 加速度
qdd(t) = 2*a2 + 6*a3*t + 12*a4*t² + 20*a5*t³
```

---

## 模块架构

### 1. 世界构建模块 (P1)

```
WorldManager
├── MineZone (铁矿/硅矿)
├── SolarArray (太阳能发电)
├── ChargingDock (充电站)
├── Warehouse (仓库)
├── PathNetwork (路径网络)
└── ItemRegistry (物品注册表)
```

**关键设计**:
- **配置驱动**: 所有世界元素通过 YAML 配置文件定义
- **统一接口**: WorldManager.get_world_state() 提供全局状态
- **配方系统**: Recipe 定义输入/输出/时间/能耗

### 2. 机器人控制模块 (P4)

```
GenesisBot (统一接口)
├── BaseController (底盘)
│   ├── PIDController
│   └── OdometryEstimator
├── ArmController (手臂)
│   ├── IKSolver
│   ├── TrajectoryPlanner
│   └── ImpedanceController
├── GripperController (夹爪)
└── SensorSuite (传感器)
```

**关键设计**:
- **统一接口**: 上层模块只通过 GenesisBot 交互
- **异步执行**: 所有技能支持异步执行和取消
- **阻抗控制**: 支持柔顺操作，用于精细装配

### 3. 工站系统模块 (P5)

```
StationManager
├── Smelter (冶炼站)
├── Fabricator (加工站)
└── Assembler (装配站)
```

**状态机设计**:
```
IDLE → WAITING_INPUT → PROCESSING → DONE → IDLE
                          ↓
                        ERROR
```

**关键设计**:
- **自动配方匹配**: 输入足够时自动开始加工
- **统一接口**: StationInterface 提供机器人交互接口
- **状态查询**: 支持查询工站状态和任务进度

### 4. 智能决策模块 (P6)

```
Brain Stack
├── L3: StrategicPlanner (LLM 驱动)
│   └── generate_master_plan()
├── L2: TaskExecutor (行为树)
│   └── build_tree_from_plan()
└── L1: SkillExecutor
    └── execute_skill()
```

**关键设计**:
- **多后端 LLM**: 支持 OpenAI/vLLM/Ollama/Mock
- **智能缓存**: LLM 响应缓存，减少重复调用
- **异常恢复**: 5 种错误类型 + 恢复策略

### 5. 评估优化模块 (P8)

```
Analysis
├── TimeAnalyzer (时间分析)
├── EnergyAnalyzer (能量分析)
└── ReliabilityAnalyzer (可靠性分析)

Optimization
├── PathOptimizer (TSP 路径优化)
├── ParallelScheduler (并行调度)
├── SkillOptimizer (技能优化)
└── EnergyOptimizer (能源优化)
```

**关键设计**:
- **多算法支持**: 最近邻、2-opt、模拟退火
- **智能充电**: 5 种能源策略、5 级充电优先级
- **物体特定参数**: 8 种物体的默认抓取参数

---

## 数据流

### 主循环数据流

```
┌─────────────────────────────────────────────────────────────┐
│ 主循环                                                       │
│                                                             │
│ 1. 物理仿真步进                                              │
│    sim.step() → world_manager.step(dt)                     │
│                                                             │
│ 2. 感知更新                                                  │
│    perception.update() → semantic_map, detected_objects    │
│                                                             │
│ 3. 行为树执行                                                │
│    behavior_tree.tick() → skill_commands                   │
│                                                             │
│ 4. 技能执行                                                  │
│    skill_executor.execute(commands) → robot_actions        │
│                                                             │
│ 5. 数据记录                                                  │
│    logger.log(state) → logs/run_xxx.jsonl                  │
│                                                             │
│ 6. Dashboard 更新                                            │
│    dashboard.update() → WebSocket → UI                     │
│                                                             │
│ 7. 循环检查                                                  │
│    if plan.is_complete(): break                            │
│    if error: planner.replan()                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 技能执行数据流

```
TaskPlan (from LLM)
    │
    ▼
┌─────────────────┐
│ TaskExecutor    │
│ build_tree()    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BehaviorTree    │
│ tick()          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ SkillExecutor   │
│ execute(skill)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GenesisBot      │
│ move_arm()      │
│ grasp()         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Physics Sim     │
│ (Isaac/MuJoCo)  │
└─────────────────┘
```

---

## 配置系统

### 配置文件结构

```yaml
# configs/world_config.yaml
world:
  size: [50.0, 50.0]
  gravity: [0, 0, -9.81]
  time_step: 0.002

zones:
  mine_iron:
    position: [5, 35, 0]
    size: [8, 8, 0.5]
    resource_type: "iron_ore"
    total_units: 500

# configs/robot_config.yaml
robot:
  chassis:
    max_linear_speed: 1.5  # m/s
    max_angular_speed: 1.0 # rad/s
  arm:
    dof: 6
    max_reach: 0.7  # m
    max_payload: 5.0 # kg
  battery:
    capacity_wh: 500

# configs/llm_config.yaml
llm:
  provider: "openai"  # openai/vllm/ollama/mock
  model: "gpt-4"
  temperature: 0.3
  max_tokens: 2000
  retry_count: 3
  enable_cache: true
```

---

## 测试策略

### 测试层级

```
Level 1: 单配方闭环
└── test_single_recipe.py
    └── 采矿 → 投料 → 冶炼 → 取料 → 存储

Level 2: 双配方链式
└── test_chain_recipe.py
    └── 铁矿 → 铁锭 → 电机

Level 3: 制造 arm
└── test_make_arm.py
    └── 完整 arm 装配链

Level 4: 完整机器人 ★
└── test_full_genesis.py
    └── 从 0 到完整机器人

Level 5-6: 能量/故障
└── test_energy_fault.py
    └── 充电调度 + 故障恢复
```

### 测试覆盖率

- 单元测试: 每个模块独立测试
- 集成测试: 模块间交互测试
- 端到端测试: 完整流程测试
- 性能基准: 时间/能量/可靠性指标

---

## 扩展点

### 添加新工站

1. 继承 WorkStation 基类
2. 定义 station_type
3. 添加配方到 recipes.py
4. 配置工站位置到 world_config.yaml

### 添加新技能

1. 继承 BaseSkill 基类
2. 实现 execute() 方法
3. 注册到 SkillLibrary
4. 添加测试用例

### 添加新 LLM 后端

1. 实现 LLMClient 接口
2. 添加配置到 llm_config.yaml
3. 测试规划器兼容性

---

## 性能优化

### 已实现优化

1. **路径优化**: TSP 求解器减少空跑
2. **并行调度**: 利用等待时间执行其他任务
3. **智能充电**: 在任务间隙充电
4. **LLM 缓存**: 减少重复 API 调用

### 性能指标

| 指标 | 目标 | 当前 |
|------|------|------|
| 抓取成功率 | >95% | 95%+ |
| 导航成功率 | >99% | 99%+ |
| 完整闭环时间 | <2h | ~1.5h |
| 能量比 (发电/耗电) | >1.0 | 1.2+ |

---

## 未来规划

### P10 拓展方向

1. **多机器人协作**: 2+ 机器人并行工作
2. **更真实的能源**: 日夜循环、天气影响
3. **更真实的制造**: 螺栓拧紧、质量检测
4. **芯片制造**: 极简半导体工艺模拟
5. **自我修复**: 零件磨损检测与更换
6. **Sim-to-Real**: 策略迁移到真实机器人

---

## 参考资料

- [NVIDIA Isaac Sim Documentation](https://docs.omniverse.nvidia.com/isaacsim/latest/)
- [MuJoCo Documentation](https://mujoco.readthedocs.io/)
- [Behavior Trees in Robotics and AI](https://arxiv.org/abs/1709.00084)
- [SayCan: Grounding Language in Robotic Affordances](https://say-can.github.io/)

---

*文档版本: 1.0*
*最后更新: 2026-03-19*
