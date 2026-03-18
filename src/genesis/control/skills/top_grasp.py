"""
GENESIS Top Grasp Skill - 顶抓技能

实现从上方抓取物体的技能。

流程:
1. 移动到预抓取位姿 (物体正上方)
2. 下降到抓取位姿
3. 闭合夹爪
4. 提起物体
5. 验证抓取成功
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
import numpy as np

from genesis.control.skills.base_skill import (
    BaseSkill,
    SkillContext,
    SkillResult,
    SkillStatus,
)
from genesis.utils.geometry import SE3, SO3
from genesis.robot.robot_interface import ArmSide


@dataclass
class TopGraspParams:
    """顶抓参数"""
    # 物体信息
    object_position: np.ndarray = None  # 物体位置 [x, y, z]
    object_size: np.ndarray = None  # 物体尺寸 [lx, ly, lz]
    object_type: str = ""  # 物体类型

    # 抓取参数
    approach_height: float = 0.15  # 预抓取高度 (m)
    grasp_height: float = 0.02  # 抓取高度偏移 (m)
    grasp_force: float = 30.0  # 抓取力 (N)
    grasp_width: float = 0.0  # 抓取宽度 (0 = 自动)

    # 运动参数
    approach_speed: float = 0.5  # 接近速度 (m/s)
    descent_speed: float = 0.1  # 下降速度 (m/s)
    lift_speed: float = 0.3  # 提起速度 (m/s)
    lift_height: float = 0.15  # 提起高度 (m)

    # 验证参数
    force_threshold: float = 5.0  # 力阈值 (N)
    verify_timeout: float = 2.0  # 验证超时 (s)


class TopGraspSkill(BaseSkill):
    """
    顶抓技能

    从上方抓取物体。
    """

    def __init__(
        self,
        context: SkillContext = None,
        arm: ArmSide = ArmSide.LEFT,
        params: TopGraspParams = None,
    ):
        """
        初始化顶抓技能

        Args:
            context: 执行上下文
            arm: 使用的手臂
            params: 抓取参数
        """
        super().__init__("top_grasp", context)
        self.arm = arm
        self.params = params or TopGraspParams()

    async def execute(self, **kwargs) -> SkillResult:
        """
        执行顶抓

        Args:
            **kwargs: 可覆盖参数

        Returns:
            执行结果
        """
        self._set_status(SkillStatus.RUNNING)
        self._result = None

        try:
            # 更新参数
            for key, value in kwargs.items():
                if hasattr(self.params, key):
                    setattr(self.params, key, value)

            # 验证参数
            if self.params.object_position is None:
                return self._fail("Object position not specified")

            # 阶段 1: 移动到预抓取位姿
            self._update_progress(0.1)
            if not await self._move_to_pre_grasp():
                return self._fail("Failed to move to pre-grasp pose")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 2: 下降到抓取位姿
            self._update_progress(0.3)
            if not await self._descend_to_grasp():
                return self._fail("Failed to descend to grasp pose")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 3: 闭合夹爪
            self._update_progress(0.5)
            if not await self._close_gripper():
                return self._fail("Failed to close gripper")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 4: 提起物体
            self._update_progress(0.7)
            if not await self._lift_object():
                return self._fail("Failed to lift object")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 5: 验证抓取
            self._update_progress(0.9)
            if not await self._verify_grasp():
                return self._fail("Grasp verification failed")

            # 成功
            self._update_progress(1.0)
            self._set_status(SkillStatus.COMPLETED)

            self._result = SkillResult(
                success=True,
                status=SkillStatus.COMPLETED,
                message="Top grasp completed successfully",
                data={"arm": self.arm.value}
            )

            return self._result

        except Exception as e:
            return self._fail(f"Exception during grasp: {str(e)}", e)

    async def _move_to_pre_grasp(self) -> bool:
        """移动到预抓取位姿"""
        robot = self.context.robot
        if robot is None:
            return False

        # 计算预抓取位姿
        obj_pos = self.params.object_position
        pre_grasp_pose = SE3(
            position=(obj_pos[0], obj_pos[1], obj_pos[2] + self.params.approach_height),
            rotation=SO3.from_euler_angles(np.pi, 0, 0)  # 朝下
        )

        # 移动手臂
        robot.move_arm_to_pose(self.arm, pre_grasp_pose, duration=2.0)

        # 等待运动完成
        return await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=10.0
        )

    async def _descend_to_grasp(self) -> bool:
        """下降到抓取位姿"""
        robot = self.context.robot
        if robot is None:
            return False

        # 计算抓取位姿
        obj_pos = self.params.object_position
        grasp_pose = SE3(
            position=(obj_pos[0], obj_pos[1], obj_pos[2] + self.params.grasp_height),
            rotation=SO3.from_euler_angles(np.pi, 0, 0)
        )

        # 慢速下降
        robot.move_arm_to_pose(self.arm, grasp_pose, duration=3.0)

        return await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=10.0
        )

    async def _close_gripper(self) -> bool:
        """闭合夹爪"""
        robot = self.context.robot
        if robot is None:
            return False

        # 计算抓取宽度
        width = self.params.grasp_width
        if width <= 0 and self.params.object_size is not None:
            # 使用物体尺寸
            width = min(self.params.object_size[0], self.params.object_size[1]) * 0.9

        # 闭合夹爪
        robot.grasp(self.arm, width=width, force=self.params.grasp_force)

        # 等待夹爪闭合
        await asyncio.sleep(1.0)

        return True

    async def _lift_object(self) -> bool:
        """提起物体"""
        robot = self.context.robot
        if robot is None:
            return False

        # 获取当前位姿
        current_state = robot.get_arm_state(self.arm)
        current_pose = current_state.end_effector_pose

        # 计算提起位姿
        lift_pose = SE3(
            position=(
                current_pose.x,
                current_pose.y,
                current_pose.z + self.params.lift_height
            ),
            rotation=current_pose.rotation
        )

        # 提起
        robot.move_arm_to_pose(self.arm, lift_pose, duration=2.0)

        return await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=5.0
        )

    async def _verify_grasp(self) -> bool:
        """验证抓取"""
        robot = self.context.robot
        if robot is None:
            return False

        # 检查夹爪状态
        gripper_state = robot.get_gripper_state(self.arm)

        # 检查力传感器
        wrench = robot.get_wrist_force(self.arm)
        force_magnitude = np.linalg.norm(wrench[:3])

        # 如果有足够的力，说明抓取成功
        if force_magnitude > self.params.force_threshold:
            return True

        # 如果夹爪没有完全闭合，可能抓住了物体
        if gripper_state.value != "open":
            return True

        return False

    async def cancel(self) -> bool:
        """取消抓取"""
        self._cancel_flag = True

        # 停止手臂运动
        if self.context.robot:
            self.context.robot.stop_arm(self.arm)

        self._set_status(SkillStatus.CANCELLED)
        return True

    def _fail(self, message: str, error: Exception = None) -> SkillResult:
        """返回失败结果"""
        self._set_status(SkillStatus.FAILED)
        self._result = SkillResult(
            success=False,
            status=SkillStatus.FAILED,
            message=message,
            error=error
        )
        return self._result

    def _cancel(self) -> SkillResult:
        """返回取消结果"""
        self._result = SkillResult(
            success=False,
            status=SkillStatus.CANCELLED,
            message="Grasp cancelled"
        )
        return self._result


__all__ = ["TopGraspParams", "TopGraspSkill"]
