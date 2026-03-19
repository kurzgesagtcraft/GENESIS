# Changelog

All notable changes to the GENESIS project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-03-19

### Added

#### P0 - 基础设施搭建
- 开发环境配置 (RTX 4090 Laptop, WSL2, Python 3.10, PyTorch 2.5.1, MuJoCo 3.6.0)
- Git 仓库初始化，目录结构设计
- Makefile 构建系统
- 知识预研笔记 (Isaac Sim, MuJoCo, LeRobot, robosuite, SayCan)

#### P1 - 仿真世界构建
- 世界地图设计 (world_layout.drawio, world_config.yaml)
- MineZone 矿区模块 (铁矿/硅矿)
- SolarArray 太阳能发电系统
- ChargingDock 充电站
- Warehouse 仓库存储系统
- PathNetwork A* 路径规划网络
- ItemRegistry 物品注册表 (11 种物品)
- Recipe 配方系统 (9 种配方)
- RecipeGraph 制造依赖关系图
- WorldManager 统一管理器

#### P2 - 机器人本体建模
- 机器人规格设计 (docs/robot_spec.md)
- URDF/USD 模型文件
- Sensors 传感器配置 (RGB-D 相机, IMU, 力/力矩传感器)
- Battery 电池系统模拟
- RobotInterface 统一控制接口

#### P3 - 感知系统开发
- Segmentation 语义分割模块
- PoseEstimation 6D 位姿估计 (PCA/ICP 算法)
- DockDetection 工站对接检测
- SemanticMap 实时语义地图
- ResourceTracker 资源状态感知

#### P4 - 运动与操作能力
- BaseController 差速底盘控制 (PID 控制器)
- PathFollower Pure Pursuit 路径跟踪
- Navigator 全局导航接口
- IKSolver 阻尼最小二乘法逆运动学
- TrajectoryPlanner 五次多项式轨迹规划
- ImpedanceController 笛卡尔阻抗控制
- 7 种操作技能:
  - TopGraspSkill 顶抓
  - PlaceSkill 放置
  - SideGraspSkill 侧抓
  - FeedStationSkill 投料
  - RetrieveStationSkill 取料
  - ChargeSkill 充电
  - WarehouseOpsSkill 仓储操作

#### P5 - 工站系统仿真
- WorkStation 基类与状态机
- Smelter 冶炼站
- Fabricator 加工站
- Assembler 装配站
- StationInterface 统一交互接口
- StationManager 工站管理器

#### P6 - 智能决策大脑
- LLMClient 多后端客户端 (OpenAI/vLLM/Ollama/Mock)
- StrategicPlanner LLM 驱动战略规划器
- BehaviorTree 行为树框架 (6 种节点类型)
- TaskExecutor 任务执行器
- ErrorHandler 异常处理器 (5 种错误类型)
- Dashboard 实时状态监控

#### P7 - 全链路集成
- run_genesis.py 主程序入口
- GenesisSystem 全链路集成系统
- DataLogger 数据记录器
- Level 1-6 分级集成测试:
  - test_single_recipe.py 单配方闭环
  - test_chain_recipe.py 双配方链式
  - test_make_arm.py 制造 arm
  - test_full_genesis.py 完整机器人
  - test_energy_fault.py 能量/故障

#### P8 - 评估与优化
- TimeAnalyzer 时间分析模块
- EnergyAnalyzer 能量分析模块
- ReliabilityAnalyzer 可靠性分析模块
- PathOptimizer TSP 路径优化 (最近邻/2-opt/模拟退火)
- ParallelScheduler 并行调度器
- SkillOptimizer 技能参数优化
- EnergyOptimizer 充电策略优化
- P8_evaluation_report.md 分析报告

#### P9 - 展示与开源
- README.md 项目文档更新
- docs/architecture.md 架构设计文档
- docs/lessons_learned.md 经验总结文档
- docs/CONTRIBUTING.md 贡献指南
- LICENSE MIT 许可证
- CHANGELOG.md 变更日志

### Changed
- N/A (Initial release)

### Deprecated
- N/A (Initial release)

### Removed
- N/A (Initial release)

### Fixed
- N/A (Initial release)

### Security
- N/A (Initial release)

---

## [Unreleased]

### Planned (P10 - 拓展)

#### 待添加
- 多机器人协作 (2+ 机器人并行工作)
- 更真实的能源系统 (日夜循环、天气影响、电池退化)
- 更真实的制造 (螺栓拧紧、质量检测、工具更换)
- 芯片制造极简模拟 (半导体工艺)
- 自我修复 (零件磨损检测与更换)
- Sim-to-Real 桥接 (策略迁移到真实机器人)

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2026-03-19 | Initial release (P0-P8 complete) |

---

## Statistics

- **总代码行数**: ~15,000 行
- **测试用例数**: ~100 个
- **文档页数**: ~50 页
- **开发周期**: ~20 周
- **模块数量**: 50+ 个

---

*This changelog is automatically generated. Do not edit manually.*
