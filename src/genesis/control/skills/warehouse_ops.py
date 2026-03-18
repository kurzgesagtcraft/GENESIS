"""
GENESIS Warehouse Operations Skills - 仓储技能

实现仓库存储和取出的技能。

流程:
- 存储: 导航 → 寻找空槽位 → 放置物品
- 取出: 导航 → 寻找物品槽位 → 抓取物品
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
class WarehouseStoreParams:
    """仓储存储参数"""
    # 物品信息
    item_type: str = ""  # 物品类型
    item_id: str = ""  # 物品 ID (可选)

    # 槽位信息
    slot_id: Optional[int] = None  # 指定槽位 (可选)

    # 放置参数
    approach_height: float = 0.15  # 接近高度 (m)
    place_offset: float = 0.05  # 放置偏移 (m)

    # 导航参数
    navigation_timeout: float = 60.0  # 导航超时 (s)


@dataclass
class WarehouseRetrieveParams:
    """仓储取出参数"""
    # 物品信息
    item_type: str = ""  # 物品类型
    item_id: str = ""  # 物品 ID (可选)

    # 槽位信息
    slot_id: Optional[int] = None  # 指定槽位 (可选)

    # 抓取参数
    approach_height: float = 0.15  # 接近高度 (m)
    grasp_offset: float = 0.02  # 抓取偏移 (m)
    grasp_force: float = 30.0  # 抓取力 (N)

    # 导航参数
    navigation_timeout: float = 60.0  # 导航超时 (s)


class WarehouseStoreSkill(BaseSkill):
    """
    仓储存储技能

    将物品存入仓库。
    """

    def __init__(
        self,
        context: SkillContext = None,
        arm: ArmSide = ArmSide.LEFT,
        params: WarehouseStoreParams = None,
    ):
        """
        初始化仓储存储技能

        Args:
            context: 执行上下文
            arm: 使用的手臂
            params: 存储参数
        """
        super().__init__("warehouse_store", context)
        self.arm = arm
        self.params = params or WarehouseStoreParams()

    async def execute(self, **kwargs) -> SkillResult:
        """
        执行存储

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
            if not self.params.item_type:
                return self._fail("Item type not specified")

            # 阶段 1: 导航到仓库
            self._update_progress(0.1)
            if not await self._navigate_to_warehouse():
                return self._fail("Failed to navigate to warehouse")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 2: 寻找空槽位
            self._update_progress(0.3)
            slot_id, slot_pose = await self._find_empty_slot()

            if slot_id is None:
                return self._fail("No empty slot available")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 3: 放置物品
            self._update_progress(0.5)
            if not await self._place_item(slot_pose):
                return self._fail("Failed to place item")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 4: 更新库存记录
            self._update_progress(0.9)
            await self._update_inventory(slot_id)

            # 成功
            self._update_progress(1.0)
            self._set_status(SkillStatus.COMPLETED)

            self._result = SkillResult(
                success=True,
                status=SkillStatus.COMPLETED,
                message=f"Successfully stored {self.params.item_type} in slot {slot_id}",
                data={
                    "item_type": self.params.item_type,
                    "slot_id": slot_id,
                    "arm": self.arm.value
                }
            )

            return self._result

        except Exception as e:
            return self._fail(f"Exception during store: {str(e)}", e)

    async def _navigate_to_warehouse(self) -> bool:
        """导航到仓库"""
        navigator = self.context.navigator
        if navigator is None:
            return True

        return await navigator.navigate_to_zone_async(
            "warehouse",
            timeout=self.params.navigation_timeout
        )

    async def _find_empty_slot(self) -> Tuple[Optional[int], Optional[SE3]]:
        """
        寻找空槽位

        Returns:
            (槽位 ID, 槽位位姿)，如果没找到返回 (None, None)
        """
        world_manager = self.context.world_manager
        if world_manager is None:
            return None, None

        warehouse = world_manager.warehouse
        if warehouse is None:
            return None, None

        # 如果指定了槽位，检查是否可用
        if self.params.slot_id is not None:
            if warehouse.is_slot_empty(self.params.slot_id):
                slot_pose = warehouse.get_slot_pose(self.params.slot_id)
                return self.params.slot_id, slot_pose
            else:
                return None, None

        # 寻找空槽位
        empty_slots = warehouse.get_empty_slots()
        if not empty_slots:
            return None, None

        # 选择最近的空槽位
        robot = self.context.robot
        if robot is not None:
            robot_pos = robot.get_base_pose()
            min_dist = float('inf')
            best_slot = empty_slots[0]

            for slot_id in empty_slots:
                slot_pose = warehouse.get_slot_pose(slot_id)
                dist = np.sqrt(
                    (slot_pose.x - robot_pos[0])**2 +
                    (slot_pose.y - robot_pos[1])**2
                )
                if dist < min_dist:
                    min_dist = dist
                    best_slot = slot_id

            slot_pose = warehouse.get_slot_pose(best_slot)
            return best_slot, slot_pose

        # 返回第一个空槽位
        slot_id = empty_slots[0]
        slot_pose = warehouse.get_slot_pose(slot_id)
        return slot_id, slot_pose

    async def _place_item(self, slot_pose: SE3) -> bool:
        """放置物品"""
        robot = self.context.robot
        if robot is None:
            return False

        # 计算预放置位姿
        pre_place_pose = SE3(
            position=(
                slot_pose.x,
                slot_pose.y,
                slot_pose.z + self.params.approach_height
            ),
            rotation=SO3.from_euler_angles(np.pi, 0, 0)
        )

        # 移动到预放置位姿
        robot.move_arm_to_pose(self.arm, pre_place_pose, duration=2.0)

        if not await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=10.0
        ):
            return False

        if self._check_cancelled():
            return False

        # 计算放置位姿
        place_pose = SE3(
            position=(
                slot_pose.x,
                slot_pose.y,
                slot_pose.z + self.params.place_offset
            ),
            rotation=SO3.from_euler_angles(np.pi, 0, 0)
        )

        # 下降到放置位姿
        robot.move_arm_to_pose(self.arm, place_pose, duration=2.0)

        if not await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=10.0
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

    async def _update_inventory(self, slot_id: int):
        """更新库存记录"""
        world_manager = self.context.world_manager
        if world_manager is None:
            return

        warehouse = world_manager.warehouse
        if warehouse is None:
            return

        # 记录物品存储
        warehouse.store_item(self.params.item_type, slot_id)

    async def cancel(self) -> bool:
        """取消存储"""
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
            message="Store cancelled"
        )
        return self._result


class WarehouseRetrieveSkill(BaseSkill):
    """
    仓储取出技能

    从仓库取出物品。
    """

    def __init__(
        self,
        context: SkillContext = None,
        arm: ArmSide = ArmSide.LEFT,
        params: WarehouseRetrieveParams = None,
    ):
        """
        初始化仓储取出技能

        Args:
            context: 执行上下文
            arm: 使用的手臂
            params: 取出参数
        """
        super().__init__("warehouse_retrieve", context)
        self.arm = arm
        self.params = params or WarehouseRetrieveParams()

    async def execute(self, **kwargs) -> SkillResult:
        """
        执行取出

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
            if not self.params.item_type and self.params.slot_id is None:
                return self._fail("Item type or slot ID must be specified")

            # 阶段 1: 导航到仓库
            self._update_progress(0.1)
            if not await self._navigate_to_warehouse():
                return self._fail("Failed to navigate to warehouse")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 2: 寻找物品槽位
            self._update_progress(0.3)
            slot_id, slot_pose = await self._find_item_slot()

            if slot_id is None:
                return self._fail("Item not found in warehouse")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 3: 抓取物品
            self._update_progress(0.5)
            if not await self._grasp_item(slot_pose):
                return self._fail("Failed to grasp item")

            if self._check_cancelled():
                return self._cancel()

            # 阶段 4: 更新库存记录
            self._update_progress(0.9)
            await self._update_inventory(slot_id)

            # 成功
            self._update_progress(1.0)
            self._set_status(SkillStatus.COMPLETED)

            self._result = SkillResult(
                success=True,
                status=SkillStatus.COMPLETED,
                message=f"Successfully retrieved item from slot {slot_id}",
                data={
                    "item_type": self.params.item_type,
                    "slot_id": slot_id,
                    "arm": self.arm.value
                }
            )

            return self._result

        except Exception as e:
            return self._fail(f"Exception during retrieve: {str(e)}", e)

    async def _navigate_to_warehouse(self) -> bool:
        """导航到仓库"""
        navigator = self.context.navigator
        if navigator is None:
            return True

        return await navigator.navigate_to_zone_async(
            "warehouse",
            timeout=self.params.navigation_timeout
        )

    async def _find_item_slot(self) -> Tuple[Optional[int], Optional[SE3]]:
        """
        寻找物品槽位

        Returns:
            (槽位 ID, 槽位位姿)，如果没找到返回 (None, None)
        """
        world_manager = self.context.world_manager
        if world_manager is None:
            return None, None

        warehouse = world_manager.warehouse
        if warehouse is None:
            return None, None

        # 如果指定了槽位
        if self.params.slot_id is not None:
            slot_pose = warehouse.get_slot_pose(self.params.slot_id)
            return self.params.slot_id, slot_pose

        # 根据物品类型查找
        slots_with_item = warehouse.find_slots_with_item(self.params.item_type)
        if not slots_with_item:
            return None, None

        # 选择最近的槽位
        robot = self.context.robot
        if robot is not None:
            robot_pos = robot.get_base_pose()
            min_dist = float('inf')
            best_slot = slots_with_item[0]

            for slot_id in slots_with_item:
                slot_pose = warehouse.get_slot_pose(slot_id)
                dist = np.sqrt(
                    (slot_pose.x - robot_pos[0])**2 +
                    (slot_pose.y - robot_pos[1])**2
                )
                if dist < min_dist:
                    min_dist = dist
                    best_slot = slot_id

            slot_pose = warehouse.get_slot_pose(best_slot)
            return best_slot, slot_pose

        slot_id = slots_with_item[0]
        slot_pose = warehouse.get_slot_pose(slot_id)
        return slot_id, slot_pose

    async def _grasp_item(self, slot_pose: SE3) -> bool:
        """抓取物品"""
        robot = self.context.robot
        if robot is None:
            return False

        # 计算预抓取位姿
        pre_grasp_pose = SE3(
            position=(
                slot_pose.x,
                slot_pose.y,
                slot_pose.z + self.params.approach_height
            ),
            rotation=SO3.from_euler_angles(np.pi, 0, 0)
        )

        # 移动到预抓取位姿
        robot.move_arm_to_pose(self.arm, pre_grasp_pose, duration=2.0)

        if not await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=10.0
        ):
            return False

        if self._check_cancelled():
            return False

        # 计算抓取位姿
        grasp_pose = SE3(
            position=(
                slot_pose.x,
                slot_pose.y,
                slot_pose.z + self.params.grasp_offset
            ),
            rotation=SO3.from_euler_angles(np.pi, 0, 0)
        )

        # 下降到抓取位姿
        robot.move_arm_to_pose(self.arm, grasp_pose, duration=2.0)

        if not await self._wait_for_motion(
            lambda: robot.get_arm_state(self.arm).is_moving,
            timeout=10.0
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

    async def _update_inventory(self, slot_id: int):
        """更新库存记录"""
        world_manager = self.context.world_manager
        if world_manager is None:
            return

        warehouse = world_manager.warehouse
        if warehouse is None:
            return

        # 记录物品取出
        warehouse.retrieve_item(slot_id)

    async def cancel(self) -> bool:
        """取消取出"""
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


__all__ = [
    "WarehouseStoreParams",
    "WarehouseRetrieveParams",
    "WarehouseStoreSkill",
    "WarehouseRetrieveSkill",
]
