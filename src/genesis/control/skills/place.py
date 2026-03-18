"""
GENESIS Place Skill - 放置技能

实现将物体放置到目标位置的技能。

流程:
1. 移动到放置点上方
2. 下降到放置高度
3. 打开夹爪
4. 抬起手臂
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
class PlaceParams:
    """放置参数"""
    # 目标信息
    target_position: np.ndarray = None  # 目标位置 [x, y, z]
    target_yaw: float = 0.0  # 目标朝向 (rad)
    target_pose: SE3 = None  # 目标位姿 (优先使用)

    # 放置参数
    approach_height: float = 0.1  # 预放置高度 (m)
    place_height: float = 0.0  # 放置高度偏移 (m)

    # 运动参数
    approach_speed: float = 0.5  # 接近速度 (m/s)
    descent_speed: float = 0.1  # 下降速度 (m/s)
    retreat_speed: float = 0.3  # 退回速度 (m/s)
    retreat_height: float = 0.15  # 退回高度 (m)

    # 精确放置
    use_impedance: bool = False  # 是否使用阻抗控制
    impedance_stiffness: np.ndarray = field(
        default_factory=lambda: np.array([100.0, 100.0, 500.0])
    )


class PlaceSkill(BaseSkill):
    """
    放置技能

    将手中的物体放置到目标位置。
    """

    def __init__(
        self,
        context: SkillContext = None,
        arm: ArmSide = ArmSide.LEFT,
        params: PlaceParams = None,
    ):
        """
        初始化放置技能

        Args:
            context: 执行上下文
            arm: 使用的手臂
            params: 放置参数
        """
        super().__init__("place", context)
        self.arm = arm
        self.params = params or PlaceParams()

    async def execute(self, **kwargs) -> SkillResult:
        """
        执行放置

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
            if self.params.target_pose is None and self.params.target_position is None:
                return self._fail("Target position not specified")

            # 阶段 1: 移动到预放置位姿
            self._update_progress(0.2)
            if not await self._move_to_pre_place():
                return self._fail("Failed to move to pre-place pose")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 2: 下降到放置位姿
            self._update_progress(0.4)
            if not await self._descend_to_place():
                return self._fail("Failed to descend to place pose")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 3: 打开夹爪
            self._update_progress(0.6)
            if not await self._open_gripper():
                return self._fail("Failed to open gripper")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 4: 退回
            self._update_progress(0.8)
            if not await self._retreat():
                return self._fail("Failed to retreat")

            # 成功
            self._update_progress(1.0)
            self._set_status(SkillStatus.COMPLETED)

            self._result = SkillResult(
                success=True,
                status=SkillStatus.COMPLETED,
                message="Place completed successfully",
                data={"arm": self.arm.value}
            )

            return self._result

        except Exception as e:
            return self._fail(f"Exception during place: {str(e)}", e)

    async def _move_to_pre_place(self) -> bool:
        """移动到预放置位姿"""
        robot = self.context.robot
        if robot is None:
            return False

        # 获取目标位姿
        target_pose = self._get_target_pose()

        # 计算预放置位姿
        pre_place_pose = SE3(
            position=(
                target_pose.x,
                target_pose.y,
                target_pose.z + self.params.approach_height
            ),
            rotation=target_pose.rotation
        )

        # 移动手臂
        robot.move_arm_to_pose(self.arm, pre_place_pose, duration=2.0)

        # 等待运动完成
        return await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=10.0
        )

    async def _descend_to_place(self) -> bool:
        """下降到放置位姿"""
        robot = self.context.robot
        if robot is None:
            return False

        # 获取目标位姿
        target_pose = self._get_target_pose()

        # 计算放置位姿
        place_pose = SE3(
            position=(
                target_pose.x,
                target_pose.y,
                target_pose.z + self.params.place_height
            ),
            rotation=target_pose.rotation
        )

        # 如果使用阻抗控制
        if self.params.use_impedance and self.context.impedance_controller:
            # 使用阻抗控制下降
            impedance = self.context.impedance_controller
            impedance.set_compliant_mode(self.params.impedance_stiffness)
            impedance.set_target_pose(place_pose)

            # 等待到达或接触
            start_time = asyncio.get_event_loop().time()
            timeout = 5.0

            while asyncio.get_event_loop().time() - start_time < timeout:
                if self._check_cancelled():
                    return False

                # 检查是否到达或接触
                current_pose = robot.get_arm_state(self.arm).end_effector_pose
                pos_error = np.linalg.norm(
                    np.array(place_pose.position) - np.array(current_pose.position)
                )

                if pos_error < 0.01:
                    break

                await asyncio.sleep(0.01)
        else:
            # 普通运动
            robot.move_arm_to_pose(self.arm, place_pose, duration=3.0)

            return await self._wait_for_motion(
                lambda: robot.get_arm_state(self.arm).is_moving,
                timeout=10.0
            )

        return True

    async def _open_gripper(self) -> bool:
        """打开夹爪"""
        robot = self.context.robot
        if robot is None:
            return False

        # 打开夹爪
        robot.release(self.arm)

        # 等待夹爪打开
        await asyncio.sleep(0.5)

        return True

    async def _retreat(self) -> bool:
        """退回"""
        robot = self.context.robot
        if robot is None:
            return False

        # 获取当前位姿
        current_state = robot.get_arm_state(self.arm)
        current_pose = current_state.end_effector_pose

        # 计算退回位姿
        retreat_pose = SE3(
            position=(
                current_pose.x,
                current_pose.y,
                current_pose.z + self.params.retreat_height
            ),
            rotation=current_pose.rotation
        )

        # 退回
        robot.move_arm_to_pose(self.arm, retreat_pose, duration=2.0)

        return await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=5.0
        )

    def _get_target_pose(self) -> SE3:
        """获取目标位姿"""
        if self.params.target_pose is not None:
            return self.params.target_pose

        # 从位置创建位姿
        pos = self.params.target_position
        return SE3(
            position=(pos[0], pos[1], pos[2]),
            rotation=SO3.from_euler_angles(np.pi, 0, self.params.target_yaw)
        )

    async def cancel(self) -> bool:
        """取消放置"""
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
            message="Place cancelled"
        )
        return self._result


__all__ = ["PlaceParams", "PlaceSkill"]
