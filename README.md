# 🏭 Project GENESIS

## Generalized Embodied Neural Entity for Self-Iterating Synthesis

**机器人自复制最小闭环模拟系统**

---

## 项目简介

GENESIS 是一个完整的机器人自复制仿真框架，旨在探索自复制系统的最小闭环实现。项目基于 NVIDIA Isaac Sim 和 MuJoCo 构建物理仿真环境，结合 LLM/VLM 实现智能决策，最终实现从原材料到完整机器人的自主制造流程。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ GENESIS 系统架构                                                     │
│                                                                     │
│ ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐          │
│ │ 🌍 World │───→│ 🤖 Robot │───→│ 🏭 Mfg   │───→│ 🧩 Assy  │          │
│ │ Sim Env  │   │ Agent    │   │ Station  │   │ Station  │          │
│ └──────────┘   └────┬─────┘   └──────────┘   └──────────┘          │
│                     │                                              │
│            ┌────────┴────────┐                                     │
│            │ 🧠 Brain Stack  │                                     │
│            │ ┌────────────┐  │                                     │
│            │ │ L3: LLM/VLM│  │  ← 任务规划 / 异常处理              │
│            │ │ Planner    │  │                                     │
│            │ ├────────────┤  │                                     │
│            │ │ L2: Skill  │  │  ← 技能编排 / 状态机                │
│            │ │ Library    │  │                                     │
│            │ ├────────────┤  │                                     │
│            │ │ L1: Motor  │  │  ← RL策略 / 阻抗控制                │
│            │ │ Control    │  │                                     │
│            │ └────────────┘  │                                     │
│            └─────────────────┘                                     │
│                                                                     │
│            ┌──────────────────────────────────────────────────┐    │
│            │ 📊 Metrics: 闭环完成率 / 零件精度 / 能量收支     │    │
│            └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

## 项目阶段

| 阶段 | 描述 | 状态 |
|------|------|------|
| P0 | 基础设施搭建 | 🔄 进行中 |
| P1 | 仿真世界构建 | ⏳ 待开始 |
| P2 | 机器人本体建模 | ⏳ 待开始 |
| P3 | 感知系统开发 | ⏳ 待开始 |
| P4 | 运动与操作能力 | ⏳ 待开始 |
| P5 | 工站系统仿真 | ⏳ 待开始 |
| P6 | 智能决策大脑 | ⏳ 待开始 |
| P7 | 全链路集成 | ⏳ 待开始 |
| P8 | 评估与优化 | ⏳ 待开始 |
| P9 | 展示与开源 | ⏳ 待开始 |
| P10 | 拓展（能源/芯片环节）| ⏳ 待开始 |

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

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/your-org/genesis-sim.git
cd genesis-sim

# 创建虚拟环境
conda env create -f environment.yml
conda activate genesis_env

# 安装依赖
pip install -e .

# 运行测试
make test

# 启动仿真
python scripts/launch_world.py
```

## 目录结构

```
genesis-sim/
├── assets/           # 3D模型, URDF/MJCF, 纹理
│   ├── robot/        # 机器人模型
│   ├── environment/  # 环境资产
│   ├── workstations/ # 工站模型
│   └── parts/        # 零件模型
├── configs/          # YAML配置文件
│   ├── robot_config.yaml
│   ├── world_config.yaml
│   ├── training_config.yaml
│   └── pipeline_config.yaml
├── src/              # 源代码
│   ├── world/        # P1: 世界构建
│   ├── robot/        # P2: 机器人本体
│   ├── perception/   # P3: 感知
│   ├── control/      # P4: 控制
│   ├── workstation/  # P5: 工站
│   ├── brain/        # P6: 决策大脑
│   ├── pipeline/     # P7: 全链路集成
│   └── utils/        # 公共工具
├── scripts/          # 启动/训练/评估脚本
├── tests/            # 单元测试 & 集成测试
├── docs/             # 文档
├── notebooks/        # Jupyter 实验
├── docker/           # Dockerfile
└── pyproject.toml    # 项目依赖管理
```

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

## 许可证

MIT License

## 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](docs/CONTRIBUTING.md) 了解详情。

## 联系方式

- 项目主页: https://github.com/kurzgesagtcraft/GENESIS
- 文档: https://github.com/kurzgesagtcraft/GENESIS.readthedocs.io
- 问题反馈: https://github.com/kurzgesagtcraft/GENESIS/issues
