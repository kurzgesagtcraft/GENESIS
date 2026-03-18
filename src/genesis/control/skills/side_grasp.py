"""
GENESIS Side Grasp Skill - 侧抓技能

实现从侧面抓取物体的技能，适用于从货架取物。

流程:
1. 移动到侧面预抓取位姿
2. 水平接近物体
3. 闭合夹爪
4. 后退并提起物体
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
class SideGraspParams:
    """侧抓参数"""
    # 物体信息
    object_position: np.ndarray = None  # 物体位置 [x, y, z]
    object_size: np.ndarray = None  # 物体尺寸 [lx, ly, lz]
    object_type: str = ""  # 物体类型

    # 抓取方向
    approach_direction: np.ndarray = field(
        default_factory=lambda: np.array([1, 0, 0])  # 默认从 x 方向接近
    )

    # 抓取参数
    approach_distance: float = 0.2  # 预抓取距离 (m)
    grasp_offset: float = 0.02  # 抓取偏移 (m)
    grasp_force: float = 30.0  # 抓取力 (N)
    grasp_width: float = 0.0  # 抓取宽度 (0 = 自动)

    # 运动参数
    approach_speed: float = 0.3  # 接近速度 (m/s)
    retreat_distance: float = 0.15  # 后退距离 (m)
    lift_height: float = 0.1  # 提起高度 (m)

    # 验证参数
    force_threshold: float = 5.0  # 力阈值 (N)


class SideGraspSkill(BaseSkill):
    """
    侧抓技能

    从侧面抓取物体，适用于从货架取物。
    """

    def __init__(
        self,
        context: SkillContext = None,
        arm: ArmSide = ArmSide.LEFT,
        params: SideGraspParams = None,
    ):
        """
        初始化侧抓技能

        Args:
            context: 执行上下文
            arm: 使用的手臂
            params: 抓取参数
        """
        super().__init__("side_grasp", context)
        self.arm = arm
        self.params = params or SideGraspParams()

    async def execute(self, **kwargs) -> SkillResult:
        """
        执行侧抓

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

            # 归一化接近方向
            approach_dir = self.params.approach_direction
            approach_dir = approach_dir / np.linalg.norm(approach_dir)
            self.params.approach_direction = approach_dir

            # 阶段 1: 移动到预抓取位姿
            self._update_progress(0.1)
            if not await self._move_to_pre_grasp():
                return self._fail("Failed to move to pre-grasp pose")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 2: 水平接近
            self._update_progress(0.3)
            if not await self._approach_object():
                return self._fail("Failed to approach object")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 3: 闭合夹爪
            self._update_progress(0.5)
            if not await self._close_gripper():
                return self._fail("Failed to close gripper")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 4: 后退并提起
            self._update_progress(0.7)
            if not await self._retreat_and_lift():
                return self._fail("Failed to retreat and lift")

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
                message="Side grasp completed successfully",
                data={"arm": self.arm.value}
            )

            return self._result

        except Exception as e:
            return self._fail(f"Exception during side grasp: {str(e)}", e)

    async def _move_to_pre_grasp(self) -> bool:
        """移动到预抓取位姿"""
        robot = self.context.robot
        if robot is None:
            return False

        # 计算预抓取位姿
        obj_pos = self.params.object_position
        approach_dir = self.params.approach_direction

        # 预抓取位置：物体位置减去接近方向乘以距离
        pre_grasp_pos = obj_pos - approach_dir * self.params.approach_distance

        # 计算朝向：夹爪指向物体
        # 计算旋转矩阵使 x 轴指向接近方向
        yaw = np.arctan2(approach_dir[1], approach_dir[0])
        pre_grasp_pose = SE3(
            position=tuple(pre_grasp_pos),
            rotation=SO3.from_euler_angles(0, np.pi/2, yaw)  # 侧向抓取姿态
        )

        # 移动手臂
        robot.move_arm_to_pose(self.arm, pre_grasp_pose, duration=2.0)

        # 等待运动完成
        return await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=10.0
        )

    async def _approach_object(self) -> bool:
        """水平接近物体"""
        robot = self.context.robot
        if robot is None:
            return False

        # 计算抓取位姿
        obj_pos = self.params.object_position
        approach_dir = self.params.approach_direction

        # 抓取位置：物体位置减去接近方向乘以偏移
        grasp_pos = obj_pos - approach_dir * self.params.grasp_offset

        yaw = np.arctan2(approach_dir[1], approach_dir[0])
        grasp_pose = SE3(
            position=tuple(grasp_pos),
            rotation=SO3.from_euler_angles(0, np.pi/2, yaw)
        )

        # 慢速接近
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
            # 使用物体尺寸 (垂直于接近方向的尺寸)
            approach_dir = self.params.approach_direction
            # 找到垂直于接近方向的两个尺寸
            if abs(approach_dir[0]) < 0.9:
                width = self.params.object_size[0] * 0.9
            else:
                width = self.params.object_size[1] * 0.9

        # 闭合夹爪
        robot.grasp(self.arm, width=width, force=self.params.grasp_force)

        # 等待夹爪闭合
        await asyncio.sleep(1.0)

        return True

    async def _retreat_and_lift(self) -> bool:
        """后退并提起"""
        robot = self.context.robot
        if robot is None:
            return False

        # 获取当前位姿
        current_state = robot.get_arm_state(self.arm)
        current_pose = current_state.end_effector_pose
        approach_dir = self.params.approach_direction

        # 后退位置：沿接近方向反方向后退
        retreat_pos = np.array(current_pose.position) - approach_dir * self.params.retreat_distance

        # 先后退
        retreat_pose = SE3(
            position=tuple(retreat_pos),
            rotation=current_pose.rotation
        )

        robot.move_arm_to_pose(self.arm, retreat_pose, duration=2.0)

        if not await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=5.0
        ):
            return False

        # 再提起
        lift_pos = retreat_pos.copy()
        lift_pos[2] += self.params.lift_height

        lift_pose = SE3(
            position=tuple(lift_pos),
            rotation=current_pose.rotation
        )

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
            message="Side grasp cancelled"
        )
        return self._result


__all__ = ["SideGraspParams", "SideGraspSkill"]
