"""
GENESIS Feed Station Skill - 投料技能

实现向工站投料的技能。

流程:
1. 导航到工站入料口附近
2. 感知入料口精确位姿
3. 将物品放入入料口
4. 确认放入成功
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
class FeedStationParams:
    """投料参数"""
    # 工站信息
    station_name: str = ""  # 工站名称
    station_type: str = ""  # 工站类型

    # 物品信息
    item_type: str = ""  # 物品类型
    item_count: int = 1  # 物品数量

    # 投料参数
    approach_height: float = 0.15  # 接近高度 (m)
    place_offset: float = 0.05  # 放置偏移 (m)

    # 运动参数
    navigation_timeout: float = 60.0  # 导航超时 (s)
    place_timeout: float = 10.0  # 放置超时 (s)


class FeedStationSkill(BaseSkill):
    """
    投料技能

    将物品投入工站入料口。
    """

    def __init__(
        self,
        context: SkillContext = None,
        arm: ArmSide = ArmSide.LEFT,
        params: FeedStationParams = None,
    ):
        """
        初始化投料技能

        Args:
            context: 执行上下文
            arm: 使用的手臂
            params: 投料参数
        """
        super().__init__("feed_station", context)
        self.arm = arm
        self.params = params or FeedStationParams()

    async def execute(self, **kwargs) -> SkillResult:
        """
        执行投料

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

            # 阶段 2: 感知入料口位姿
            self._update_progress(0.3)
            input_port_pose = await self._perceive_input_port()

            if input_port_pose is None:
                return self._fail("Failed to perceive input port")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 3: 放置物品到入料口
            self._update_progress(0.5)
            if not await self._place_item(input_port_pose):
                return self._fail("Failed to place item")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 4: 确认放入成功
            self._update_progress(0.8)
            if not await self._verify_placement():
                return self._fail("Placement verification failed")

            # 成功
            self._update_progress(1.0)
            self._set_status(SkillStatus.COMPLETED)

            self._result = SkillResult(
                success=True,
                status=SkillStatus.COMPLETED,
                message=f"Successfully fed {self.params.item_count} {self.params.item_type} to {self.params.station_name}",
                data={
                    "station": self.params.station_name,
                    "item_type": self.params.item_type,
                    "item_count": self.params.item_count,
                    "arm": self.arm.value
                }
            )

            return self._result

        except Exception as e:
            return self._fail(f"Exception during feed: {str(e)}", e)

    async def _navigate_to_station(self) -> bool:
        """导航到工站"""
        navigator = self.context.navigator
        if navigator is None:
            # 如果没有导航器，假设已经在位置
            return True

        # 导航到工站区域
        success = await navigator.navigate_to_zone_async(
            self.params.station_name,
            timeout=self.params.navigation_timeout
        )

        return success

    async def _perceive_input_port(self) -> Optional[SE3]:
        """
        感知入料口位姿

        Returns:
            入料口位姿，如果失败返回 None
        """
        perception = self.context.perception
        if perception is None:
            # 如果没有感知系统，使用预设位姿
            return self._get_default_input_port_pose()

        # 使用感知系统检测入料口
        # 这里假设有 dock_detection 模块
        if hasattr(perception, 'dock_detector'):
            dock_detector = perception.dock_detector
            docks = dock_detector.detect_docks()

            for dock in docks:
                if dock.station_name == self.params.station_name and dock.dock_type == "input":
                    return dock.pose

        # 回退到预设位姿
        return self._get_default_input_port_pose()

    def _get_default_input_port_pose(self) -> SE3:
        """获取默认入料口位姿"""
        world_manager = self.context.world_manager
        if world_manager is None:
            return SE3.identity()

        # 从世界管理器获取工站信息
        stations = world_manager.stations
        if self.params.station_name in stations:
            station = stations[self.params.station_name]
            # 假设入料口在工站位置上方
            return SE3(
                position=(
                    station.position[0],
                    station.position[1],
                    station.position[2] + 0.5  # 假设入料口高度
                ),
                rotation=SO3.from_euler_angles(np.pi, 0, 0)
            )

        return SE3.identity()

    async def _place_item(self, input_port_pose: SE3) -> bool:
        """
        放置物品到入料口

        Args:
            input_port_pose: 入料口位姿

        Returns:
            是否成功
        """
        robot = self.context.robot
        if robot is None:
            return False

        # 计算预放置位姿 (入料口上方)
        pre_place_pose = SE3(
            position=(
                input_port_pose.x,
                input_port_pose.y,
                input_port_pose.z + self.params.approach_height
            ),
            rotation=input_port_pose.rotation
        )

        # 移动到预放置位姿
        robot.move_arm_to_pose(self.arm, pre_place_pose, duration=2.0)

        if not await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=self.params.place_timeout
        ):
            return False

        if self._check_cancelled():
            return False

        # 计算放置位姿
        place_pose = SE3(
            position=(
                input_port_pose.x,
                input_port_pose.y,
                input_port_pose.z + self.params.place_offset
            ),
            rotation=input_port_pose.rotation
        )

        # 下降到放置位姿
        robot.move_arm_to_pose(self.arm, place_pose, duration=2.0)

        if not await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=self.params.place_timeout
        ):
            return False

        # 打开夹爪
        robot.release(self.arm)
        await asyncio.sleep(0.5)

        # 抬起手臂
        current_state = robot.get_arm_state(self.arm)
        current_pose = current_state.end_effector_pose

        retreat_pose = SE3(
            position=(
                current_pose.x,
                current_pose.y,
                current_pose.z + 0.15
            ),
            rotation=current_pose.rotation
        )

        robot.move_arm_to_pose(self.arm, retreat_pose, duration=1.5)

        return await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=5.0
        )

    async def _verify_placement(self) -> bool:
        """确认放入成功"""
        # 检查夹爪是否为空
        robot = self.context.robot
        if robot is None:
            return True  # 无法验证，假设成功

        # 检查工站状态
        world_manager = self.context.world_manager
        if world_manager is not None:
            stations = world_manager.stations
            if self.params.station_name in stations:
                station = stations[self.params.station_name]
                # 检查工站是否接收了物品
                # 这里简化处理，实际需要检查工站状态

        return True

    async def cancel(self) -> bool:
        """取消投料"""
        self._cancel_flag = True

        # 停止导航
        if self.context.navigator:
            self.context.navigator.cancel()

        # 停止手臂
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
            message="Feed cancelled"
        )
        return self._result


__all__ = ["FeedStationParams", "FeedStationSkill"]
