# 贡献指南

感谢您对 GENESIS 项目的关注！本文档介绍如何为项目做出贡献。

---

## 行为准则

- 尊重所有贡献者
- 保持建设性的讨论
- 接受不同观点和批评
- 关注项目利益最大化

---

## 如何贡献

### 报告问题

如果您发现 bug 或有功能建议：

1. 在 [Issues](https://github.com/kurzgesagtcraft/GENESIS/issues) 中搜索是否已有相关问题
2. 如果没有，创建新 Issue，包含：
   - 清晰的标题
   - 问题描述
   - 复现步骤（如果是 bug）
   - 期望行为
   - 环境信息（OS、Python 版本等）

### 提交代码

1. **Fork 仓库**
   ```bash
   git clone https://github.com/your-username/GENESIS.git
   cd GENESIS
   ```

2. **创建分支**
   ```bash
   git checkout -b feature/your-feature-name
   # 或
   git checkout -b fix/your-bug-fix
   ```

3. **进行修改**
   - 遵循代码风格指南
   - 添加必要的测试
   - 更新相关文档

4. **提交更改**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

5. **推送到 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```

6. **创建 Pull Request**
   - 在 GitHub 上创建 PR
   - 填写 PR 模板
   - 等待审查

---

## 代码风格

### Python 代码规范

- **缩进**: 2 空格
- **行长度**: 不超过 100 字符
- **命名约定**:
  - 变量和函数: `camelCase`
  - 类名: `PascalCase`
  - 常量: `UPPER_SNAKE_CASE`
- **导入顺序**: 标准库 → 第三方库 → 本地模块

### 示例

```python
# 标准库
import os
import sys
from typing import Dict, List, Optional

# 第三方库
import numpy as np
import torch

# 本地模块
from genesis.utils.types import SE3
from genesis.control.skills.base_skill import BaseSkill


class TopGraspSkill(BaseSkill):
    """顶抓技能实现"""
    
    MAX_GRASP_FORCE = 50.0  # N
    
    def __init__(self, config):
        super().__init__(config)
        self.graspForce = config.get('grasp_force', 30.0)
    
    def execute(self, targetPose: SE3) -> SkillResult:
        """执行顶抓
        
        Args:
            targetPose: 目标位姿
        
        Returns:
            SkillResult: 执行结果
        """
        # 实现代码...
        pass
```

---

## 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型 (type)

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式（不影响功能）
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具相关

### 示例

```
feat(control): add impedance controller for compliant manipulation

- Implement Cartesian impedance control
- Add configurable stiffness and damping
- Support position, force, and admittance modes

Closes #123
```

---

## 测试规范

### 单元测试

- 每个新模块需要单元测试
- 测试文件放在 `tests/` 目录
- 使用 `pytest` 框架

```python
# tests/test_utils.py
import pytest
from genesis.utils.geometry import SE3


class TestSE3:
    def test_composition(self):
        """测试 SE3 组合"""
        a = SE3.from_translation(1, 0, 0)
        b = SE3.from_translation(0, 1, 0)
        c = a * b
        assert c.x == pytest.approx(1.0)
        assert c.y == pytest.approx(1.0)
```

### 运行测试

```bash
# 运行所有测试
make test

# 运行特定测试
pytest tests/test_utils.py -v

# 运行带覆盖率的测试
pytest --cov=src tests/
```

---

## 文档规范

### 代码文档

- 使用 docstring 描述模块、类和方法
- 使用 Google 风格的 docstring

```python
def compute_ik(self, targetPose: SE3, seed: Optional[np.ndarray] = None) -> IKResult:
    """计算逆运动学
    
    Args:
        targetPose: 目标末端位姿
        seed: 初始关节角度（可选）
    
    Returns:
        IKResult: 包含求解状态和关节角度
    
    Raises:
        ValueError: 如果目标位姿超出工作空间
    
    Example:
        >>> solver = IKSolver(robot_kinematics)
        >>> result = solver.compute_ik(target_pose)
        >>> if result.status == IKStatus.SUCCESS:
        ...     print(f"Joint angles: {result.jointPositions}")
    """
    pass
```

### Markdown 文档

- 使用清晰的标题层级
- 添加代码示例
- 包含必要的图表

---

## 开发环境设置

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/GENESIS.git
cd GENESIS
```

### 2. 创建虚拟环境

```bash
conda env create -f environment.yml
conda activate genesis_env
```

### 3. 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 4. 安装 pre-commit hooks

```bash
pre-commit install
```

---

## 项目结构

```
GENESIS/
├── src/
│   ├── world/          # 世界构建
│   ├── robot/          # 机器人本体
│   ├── perception/     # 感知系统
│   ├── genesis/        # 控制系统
│   │   └── control/
│   ├── workstation/    # 工站系统
│   ├── brain/          # 智能决策
│   ├── analysis/       # 分析模块
│   └── optimization/   # 优化模块
├── tests/
│   ├── integration/    # 集成测试
│   └── benchmark/      # 性能测试
├── docs/               # 文档
├── scripts/            # 脚本
└── configs/            # 配置文件
```

---

## 添加新功能

### 添加新技能

1. 在 `src/genesis/control/skills/` 创建新文件
2. 继承 `BaseSkill` 基类
3. 实现 `execute()` 方法
4. 在 `src/genesis/control/skills/__init__.py` 导出
5. 添加测试用例

### 添加新工站

1. 在 `src/workstation/` 创建新文件
2. 继承 `WorkStation` 基类
3. 定义 `station_type`
4. 添加配方到 `src/world/recipes.py`
5. 配置工站位置到 `configs/world_config.yaml`

### 添加新分析模块

1. 在 `src/analysis/` 创建新文件
2. 实现分析器类
3. 添加 `analyze()` 和 `get_report()` 方法
4. 在 `src/analysis/__init__.py` 导出

---

## 发布流程

1. 更新版本号 (`pyproject.toml`)
2. 更新 `CHANGELOG.md`
3. 创建 Git tag
4. 构建 Docker 镜像
5. 发布到 GitHub Releases

---

## 获取帮助

- **文档**: 查看 `docs/` 目录
- **Issues**: 在 GitHub Issues 中提问
- **讨论**: 使用 GitHub Discussions

---

## 许可证

贡献的代码将按照 MIT 许可证发布。

---

*感谢您的贡献！*
