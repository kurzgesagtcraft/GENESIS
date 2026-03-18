"""
GENESIS Retrieve Station Skill - 取料技能

实现从工站出料口取料的技能。

流程:
1. 导航到工站出料口附近
2. 等待/检查工站状态为 done
3. 从出料口抓取产品
4. 确认抓取成功
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
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
class RetrieveStationParams:
    """取料参数"""
    # 工站信息
    station_name: str = ""  # 工站名称
    station_type: str = ""  # 工站类型

    # 取料参数
    wait_for_done: bool = True  # 是否等待工站完成
    max_wait_time: float = 300.0  # 最大等待时间 (s)
    poll_interval: float = 1.0  # 轮询间隔 (s)

    # 抓取参数
    approach_height: float = 0.15  # 接近高度 (m)
    grasp_offset: float = 0.02  # 抓取偏移 (m)
    grasp_force: float = 30.0  # 抓取力 (N)

    # 运动参数
    navigation_timeout: float = 60.0  # 导航超时 (s)
    grasp_timeout: float = 10.0  # 抓取超时 (s)


class RetrieveStationSkill(BaseSkill):
    """
    取料技能

    从工站出料口取出产品。
    """

    def __init__(
        self,
        context: SkillContext = None,
        arm: ArmSide = ArmSide.LEFT,
        params: RetrieveStationParams = None,
    ):
        """
        初始化取料技能

        Args:
            context: 执行上下文
            arm: 使用的手臂
            params: 取料参数
        """
        super().__init__("retrieve_station", context)
        self.arm = arm
        self.params = params or RetrieveStationParams()

    async def execute(self, **kwargs) -> SkillResult:
        """
        执行取料

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
            if not self.params.station_name:
                return self._fail("Station name not specified")

            # 阶段 1: 导航到工站
            self._update_progress(0.1)
            if not await self._navigate_to_station():
                return self._fail("Failed to navigate to station")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 2: 等待工站完成
            self._update_progress(0.2)
            if self.params.wait_for_done:
                if not await self._wait_for_station_done():
                    return self._fail("Station did not complete in time")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 3: 感知出料口位姿
            self._update_progress(0.4)
            output_port_pose = await self._perceive_output_port()

            if output_port_pose is None:
                return self._fail("Failed to perceive output port")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 4: 抓取产品
            self._update_progress(0.6)
            if not await self._grasp_product(output_port_pose):
                return self._fail("Failed to grasp product")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 5: 确认抓取成功
            self._update_progress(0.9)
            if not await self._verify_grasp():
                return self._fail("Grasp verification failed")

            # 成功
            self._update_progress(1.0)
            self._set_status(SkillStatus.COMPLETED)

            self._result = SkillResult(
                success=True,
                status=SkillStatus.COMPLETED,
                message=f"Successfully retrieved product from {self.params.station_name}",
                data={
                    "station": self.params.station_name,
                    "arm": self.arm.value
                }
            )

            return self._result

        except Exception as e:
            return self._fail(f"Exception during retrieve: {str(e)}", e)

    async def _navigate_to_station(self) -> bool:
        """导航到工站"""
        navigator = self.context.navigator
        if navigator is None:
            return True

        success = await navigator.navigate_to_zone_async(
            self.params.station_name,
            timeout=self.params.navigation_timeout
        )

        return success

    async def _wait_for_station_done(self) -> bool:
        """等待工站完成"""
        world_manager = self.context.world_manager
        if world_manager is None:
            return True

        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < self.params.max_wait_time:
            if self._check_cancelled():
                return False

            # 检查工站状态
            stations = world_manager.stations
            if self.params.station_name in stations:
                station = stations[self.params.station_name]
                status = station.get_status()

                if status.get("state") == "done":
                    return True

                if status.get("state") == "error":
                    return False

            await asyncio.sleep(self.params.poll_interval)

        return False

    async def _perceive_output_port(self) -> Optional[SE3]:
        """感知出料口位姿"""
        perception = self.context.perception
        if perception is None:
            return self._get_default_output_port_pose()

        # 使用感知系统检测出料口
        if hasattr(perception, 'dock_detector'):
            dock_detector = perception.dock_detector
            docks = dock_detector.detect_docks()

            for dock in docks:
                if dock.station_name == self.params.station_name and dock.dock_type == "output":
                    return dock.pose

        return self._get_default_output_port_pose()

    def _get_default_output_port_pose(self) -> SE3:
        """获取默认出料口位姿"""
        world_manager = self.context.world_manager
        if world_manager is None:
            return SE3.identity()

        stations = world_manager.stations
        if self.params.station_name in stations:
            station = stations[self.params.station_name]
            return SE3(
                position=(
                    station.position[0] + 0.5,  # 假设出料口在侧面
                    station.position[1],
                    station.position[2] + 0.3
                ),
                rotation=SO3.from_euler_angles(np.pi, 0, 0)
            )

        return SE3.identity()

    async def _grasp_product(self, output_port_pose: SE3) -> bool:
        """抓取产品"""
        robot = self.context.robot
        if robot is None:
            return False

        # 计算预抓取位姿
        pre_grasp_pose = SE3(
            position=(
                output_port_pose.x,
                output_port_pose.y,
                output_port_pose.z + self.params.approach_height
            ),
            rotation=output_port_pose.rotation
        )

        # 移动到预抓取位姿
        robot.move_arm_to_pose(self.arm, pre_grasp_pose, duration=2.0)

        if not await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=self.params.grasp_timeout
        ):
            return False

        if self._check_cancelled():
            return False

        # 计算抓取位姿
        grasp_pose = SE3(
            position=(
                output_port_pose.x,
                output_port_pose.y,
                output_port_pose.z + self.params.grasp_offset
            ),
            rotation=output_port_pose.rotation
        )

        # 下降到抓取位姿
        robot.move_arm_to_pose(self.arm, grasp_pose, duration=2.0)

        if not await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=self.params.grasp_timeout
        ):
            return False

        # 闭合夹爪
        robot.grasp(self.arm, force=self.params.grasp_force)
        await asyncio.sleep(1.0)

        # 提起
        current_state = robot.get_arm_state(self.arm)
        current_pose = current_state.end_effector_pose

        lift_pose = SE3(
            position=(
                current_pose.x,
                current_pose.y,
                current_pose.z + 0.15
            ),
            rotation=current_pose.rotation
        )

        robot.move_arm_to_pose(self.arm, lift_pose, duration=1.5)

        return await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=5.0
        )

    async def _verify_grasp(self) -> bool:
        """验证抓取"""
        robot = self.context.robot
        if robot is None:
            return True

        # 检查夹爪状态
        gripper_state = robot.get_gripper_state(self.arm)

        # 检查力传感器
        wrench = robot.get_wrist_force(self.arm)
        force_magnitude = np.linalg.norm(wrench[:3])

        if force_magnitude > 5.0 or gripper_state.value != "open":
            return True

        return False

    async def cancel(self) -> bool:
        """取消取料"""
        self._cancel_flag = True

        if self.context.navigator:
            self.context.navigator.cancel()

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
            message="Retrieve cancelled"
        )
        return self._result


__all__ = ["RetrieveStationParams", "RetrieveStationSkill"]
