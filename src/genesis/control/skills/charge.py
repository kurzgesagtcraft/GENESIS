"""
GENESIS Charge Skill - 充电技能

实现机器人自动充电的技能。

流程:
1. 导航到充电站
2. 精确对接
3. 等待充电至目标电量
4. 脱离充电站
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import numpy as np

from genesis.control.skills.base_skill import (
    BaseSkill,
    SkillContext,
    SkillResult,
    SkillStatus,
)


@dataclass
class ChargeParams:
    """充电参数"""
    # 目标电量
    target_soc: float = 0.95  # 目标 SOC (0-1)
    min_soc: float = 0.15  # 最低 SOC (触发充电)

    # 对接参数
    dock_tolerance: float = 0.3  # 对接容差 (m)
    dock_timeout: float = 30.0  # 对接超时 (s)

    # 充电参数
    charge_timeout: float = 3600.0  # 充电超时 (s) - 1小时
    poll_interval: float = 1.0  # 轮询间隔 (s)

    # 导航参数
    navigation_timeout: float = 60.0  # 导航超时 (s)


class ChargeSkill(BaseSkill):
    """
    充电技能

    让机器人自动充电。
    """

    def __init__(
        self,
        context: SkillContext = None,
        params: ChargeParams = None,
    ):
        """
        初始化充电技能

        Args:
            context: 执行上下文
            params: 充电参数
        """
        super().__init__("charge", context)
        self.params = params or ChargeParams()

    async def execute(self, **kwargs) -> SkillResult:
        """
        执行充电

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

            # 阶段 1: 导航到充电站
            self._update_progress(0.1)
            if not await self._navigate_to_charger():
                return self._fail("Failed to navigate to charger")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 2: 精确对接
            self._update_progress(0.2)
            if not await self._dock_to_charger():
                return self._fail("Failed to dock to charger")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 3: 等待充电
            self._update_progress(0.3)
            if not await self._wait_for_charge():
                return self._fail("Charging failed or timed out")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 4: 脱离充电站
            self._update_progress(0.9)
            if not await self._undock_from_charger():
                return self._fail("Failed to undock from charger")

            # 成功
            self._update_progress(1.0)
            self._set_status(SkillStatus.COMPLETED)

            robot = self.context.robot
            final_soc = robot.get_battery_soc() if robot else 0.0

            self._result = SkillResult(
                success=True,
                status=SkillStatus.COMPLETED,
                message=f"Charging completed. Battery: {final_soc*100:.1f}%",
                data={
                    "final_soc": final_soc,
                    "target_soc": self.params.target_soc
                }
            )

            return self._result

        except Exception as e:
            return self._fail(f"Exception during charging: {str(e)}", e)

    async def _navigate_to_charger(self) -> bool:
        """导航到充电站"""
        navigator = self.context.navigator
        if navigator is None:
            return True

        success = await navigator.navigate_to_zone_async(
            "charging_dock",
            timeout=self.params.navigation_timeout
        )

        return success

    async def _dock_to_charger(self) -> bool:
        """精确对接"""
        robot = self.context.robot
        if robot is None:
            return True

        # 获取充电站位置
        world_manager = self.context.world_manager
        if world_manager is None:
            return True

        charging_dock = world_manager.charging_dock
        if charging_dock is None:
            return True

        # 感知充电站精确位置
        perception = self.context.perception
        dock_pose = None

        if perception is not None and hasattr(perception, 'dock_detector'):
            dock_detector = perception.dock_detector
            docks = dock_detector.detect_docks()

            for dock in docks:
                if dock.dock_type == "charging":
                    dock_pose = dock.pose
                    break

        if dock_pose is None:
            # 使用预设位置
            dock_pose = charging_dock.position

        # 精确对接
        # 这里简化处理，实际需要视觉伺服或精确导航
        start_time = asyncio.get_event_loop().time()

        while asyncio.get_event_loop().time() - start_time < self.params.dock_timeout:
            if self._check_cancelled():
                return False

            # 检查是否已对接
            if charging_dock.is_robot_docked(robot.get_base_pose()):
                return True

            # 计算到充电站的距离
            robot_pos = robot.get_base_pose()
            dock_pos = dock_pose if hasattr(dock_pose, 'position') else dock_pose

            if isinstance(dock_pos, tuple):
                dx = dock_pos[0] - robot_pos[0]
                dy = dock_pos[1] - robot_pos[1]
            else:
                dx = dock_pos[0] - robot_pos[0]
                dy = dock_pos[1] - robot_pos[1]

            dist = np.sqrt(dx*dx + dy*dy)

            if dist < self.params.dock_tolerance:
                # 已足够接近
                return True

            # 继续移动
            # 简化：直接设置速度
            speed = min(0.3, dist)
            angle = np.arctan2(dy, dx)
            yaw = robot_pos[2]

            # 计算需要的角速度
            angle_diff = angle - yaw
            while angle_diff > np.pi:
                angle_diff -= 2 * np.pi
            while angle_diff < -np.pi:
                angle_diff += 2 * np.pi

            robot.set_velocity(speed, angle_diff * 0.5)

            await asyncio.sleep(0.1)

        # 超时
        robot.stop_base()
        return False

    async def _wait_for_charge(self) -> bool:
        """等待充电"""
        robot = self.context.robot
        if robot is None:
            return True

        start_time = asyncio.get_event_loop().time()
        start_soc = robot.get_battery_soc()

        while asyncio.get_event_loop().time() - start_time < self.params.charge_timeout:
            if self._check_cancelled():
                return False

            current_soc = robot.get_battery_soc()

            # 更新进度
            if current_soc >= self.params.target_soc:
                return True

            # 计算充电进度
            if self.params.target_soc > start_soc:
                charge_progress = (current_soc - start_soc) / (self.params.target_soc - start_soc)
                # 映射到 0.3 - 0.9
                self._update_progress(0.3 + 0.6 * min(1.0, charge_progress))

            await asyncio.sleep(self.params.poll_interval)

        return False

    async def _undock_from_charger(self) -> bool:
        """脱离充电站"""
        robot = self.context.robot
        if robot is None:
            return True

        # 后退
        robot.set_velocity(-0.2, 0)
        await asyncio.sleep(2.0)
        robot.stop_base()

        return True

    async def cancel(self) -> bool:
        """取消充电"""
        self._cancel_flag = True

        if self.context.navigator:
            self.context.navigator.cancel()

        if self.context.robot:
            self.context.robot.stop_base()

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
            message="Charging cancelled"
        )
        return self._result


__all__ = ["ChargeParams", "ChargeSkill"]
