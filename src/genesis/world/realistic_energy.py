"""
GENESIS Realistic Energy System Module

更真实的能源系统，包含日夜循环、天气影响、电池退化和多种能源。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import time
from datetime import datetime, timedelta


class WeatherCondition(Enum):
    """天气状况"""
    CLEAR = "clear"           # 晴朗
    PARTLY_CLOUDY = "partly_cloudy"  # 多云
    CLOUDY = "cloudy"         # 阴天
    RAIN = "rain"             # 雨天
    SNOW = "snow"             # 雪天
    STORM = "storm"           # 暴风雨


class EnergySourceType(Enum):
    """能源类型"""
    SOLAR = "solar"           # 太阳能
    WIND = "wind"             # 风能
    GRID = "grid"             # 电网
    GENERATOR = "generator"   # 发电机
    BATTERY_STORAGE = "battery_storage"  # 储能电池


class BatteryHealthState(Enum):
    """电池健康状态"""
    EXCELLENT = "excellent"   # 优秀 (>90%)
    GOOD = "good"             # 良好 (70-90%)
    FAIR = "fair"             # 一般 (50-70%)
    POOR = "poor"             # 较差 (30-50%)
    CRITICAL = "critical"     # 临界 (<30%)


@dataclass
class SolarConfig:
    """太阳能配置"""
    peak_power_watts: float = 100.0      # 峰值功率 (W)
    panel_efficiency: float = 0.20       # 面板效率
    tracking_enabled: bool = False       # 是否启用追踪
    tilt_angle_deg: float = 30.0         # 倾斜角度
    azimuth_deg: float = 180.0           # 方位角 (正南)


@dataclass
class WindConfig:
    """风能配置"""
    rated_power_watts: float = 50.0      # 额定功率 (W)
    cut_in_speed_ms: float = 3.0         # 启动风速 (m/s)
    rated_speed_ms: float = 12.0         # 额定风速 (m/s)
    cut_out_speed_ms: float = 25.0       # 切出风速 (m/s)
    rotor_diameter_m: float = 1.0        # 转子直径 (m)


@dataclass
class BatteryDegradationConfig:
    """电池退化配置"""
    cycle_life: int = 500                # 循环寿命
    calendar_life_years: float = 10.0    # 日历寿命 (年)
    depth_of_discharge_limit: float = 0.8  # 放电深度限制
    temperature_factor: float = 1.0      # 温度因子
    charge_rate_factor: float = 1.0      # 充电速率因子


@dataclass
class DayNightCycle:
    """日夜循环"""
    day_length_hours: float = 24.0       # 一天时长 (小时)
    sunrise_hour: float = 6.0            # 日出时间
    sunset_hour: float = 18.0            # 日落时间
    dawn_duration_hours: float = 1.0     # 黎明时长
    dusk_duration_hours: float = 1.0     # 黄昏时长

    def get_sun_position(self, current_hour: float) -> Tuple[float, float]:
        """
        获取太阳位置

        Args:
            current_hour: 当前小时 (0-24)

        Returns:
            (高度角, 方位角) 单位: 度
        """
        # 计算太阳高度角
        day_progress = (current_hour - self.sunrise_hour) / (self.sunset_hour - self.sunrise_hour)
        day_progress = np.clip(day_progress, 0.0, 1.0)

        # 高度角: 0° (日出/日落) 到 90° (正午)
        elevation = np.sin(day_progress * np.pi) * 90.0

        # 方位角: 东 (90°) → 南 (180°) → 西 (270°)
        azimuth = 90.0 + day_progress * 180.0

        return elevation, azimuth

    def is_daytime(self, current_hour: float) -> bool:
        """判断是否为白天"""
        return self.sunrise_hour <= current_hour <= self.sunset_hour

    def get_daylight_factor(self, current_hour: float) -> float:
        """
        获取日照因子

        Args:
            current_hour: 当前小时

        Returns:
            日照因子 (0-1)
        """
        if current_hour < self.sunrise_hour - self.dawn_duration_hours:
            return 0.0
        elif current_hour < self.sunrise_hour:
            # 黎明
            progress = (current_hour - (self.sunrise_hour - self.dawn_duration_hours)) / self.dawn_duration_hours
            return progress * 0.5
        elif current_hour < self.sunset_hour:
            # 白天
            elevation, _ = self.get_sun_position(current_hour)
            return np.sin(np.radians(elevation))
        elif current_hour < self.sunset_hour + self.dusk_duration_hours:
            # 黄昏
            progress = (current_hour - self.sunset_hour) / self.dusk_duration_hours
            return 0.5 * (1.0 - progress)
        else:
            return 0.0


@dataclass
class WeatherModel:
    """天气模型"""
    current_condition: WeatherCondition = WeatherCondition.CLEAR
    cloud_cover: float = 0.0             # 云量 (0-1)
    wind_speed_ms: float = 5.0           # 风速 (m/s)
    wind_direction_deg: float = 0.0      # 风向 (度)
    temperature_c: float = 25.0          # 温度 (°C)
    humidity: float = 0.5                # 湿度 (0-1)
    precipitation_rate: float = 0.0      # 降水率 (mm/h)

    # 天气变化参数
    change_probability: float = 0.01     # 每秒变化概率
    condition_weights: Dict[WeatherCondition, float] = field(default_factory=lambda: {
        WeatherCondition.CLEAR: 0.4,
        WeatherCondition.PARTLY_CLOUDY: 0.3,
        WeatherCondition.CLOUDY: 0.15,
        WeatherCondition.RAIN: 0.1,
        WeatherCondition.SNOW: 0.03,
        WeatherCondition.STORM: 0.02,
    })

    def update(self, dt: float):
        """
        更新天气状态

        Args:
            dt: 时间步长 (s)
        """
        # 随机天气变化
        if np.random.random() < self.change_probability * dt:
            self._randomize_condition()

        # 更新云量
        target_cloud = self._get_target_cloud_cover()
        self.cloud_cover += (target_cloud - self.cloud_cover) * 0.1 * dt

        # 更新风速 (随机波动)
        wind_variation = np.random.normal(0, 0.5) * dt
        self.wind_speed_ms = np.clip(self.wind_speed_ms + wind_variation, 0.0, 30.0)

        # 更新温度 (日变化)
        # 简化模型: 温度随时间变化

    def _randomize_condition(self):
        """随机选择天气状况"""
        conditions = list(self.condition_weights.keys())
        weights = list(self.condition_weights.values())
        self.current_condition = np.random.choice(conditions, p=weights)

    def _get_target_cloud_cover(self) -> float:
        """获取目标云量"""
        cloud_map = {
            WeatherCondition.CLEAR: 0.1,
            WeatherCondition.PARTLY_CLOUDY: 0.4,
            WeatherCondition.CLOUDY: 0.8,
            WeatherCondition.RAIN: 0.9,
            WeatherCondition.SNOW: 0.95,
            WeatherCondition.STORM: 1.0,
        }
        return cloud_map.get(self.current_condition, 0.0)

    def get_solar_efficiency(self) -> float:
        """
        获取太阳能效率因子

        Returns:
            效率因子 (0-1)
        """
        # 云量影响
        cloud_factor = 1.0 - self.cloud_cover * 0.8

        # 温度影响 (最佳温度约25°C)
        temp_factor = 1.0 - abs(self.temperature_c - 25.0) * 0.005

        # 降水影响
        rain_factor = 1.0 - self.precipitation_rate * 0.1

        return np.clip(cloud_factor * temp_factor * rain_factor, 0.0, 1.0)

    def get_wind_power_factor(self) -> float:
        """
        获取风能功率因子

        Returns:
            功率因子 (0-1+)
        """
        # 风速在启动风速以下或切出风速以上时为0
        if self.wind_speed_ms < 3.0 or self.wind_speed_ms > 25.0:
            return 0.0

        # 额定风速以下: 立方关系
        if self.wind_speed_ms < 12.0:
            return (self.wind_speed_ms / 12.0) ** 3

        # 额定风速到切出风速之间: 恒定
        return 1.0


class SolarArray:
    """
    太阳能发电阵列

    模拟太阳能板的发电过程，考虑日照、天气和面板参数。
    """

    def __init__(self, config: Optional[SolarConfig] = None):
        """
        初始化太阳能阵列

        Args:
            config: 太阳能配置
        """
        self.config = config or SolarConfig()
        self._current_output = 0.0
        self._total_generated = 0.0
        self._peak_output = 0.0

    def calculate_output(
        self,
        daylight_factor: float,
        weather_efficiency: float,
        sun_elevation: float,
    ) -> float:
        """
        计算当前发电功率

        Args:
            daylight_factor: 日照因子
            weather_efficiency: 天气效率
            sun_elevation: 太阳高度角

        Returns:
            发电功率 (W)
        """
        # 基础功率 = 峰值功率 × 日照因子
        base_power = self.config.peak_power_watts * daylight_factor

        # 天气影响
        weather_power = base_power * weather_efficiency

        # 面板效率
        panel_power = weather_power * self.config.panel_efficiency

        # 太阳角度影响 (简化模型)
        angle_factor = np.sin(np.radians(sun_elevation)) if sun_elevation > 0 else 0.0
        final_power = panel_power * angle_factor

        # 追踪系统增益
        if self.config.tracking_enabled:
            final_power *= 1.25  # 追踪系统可增加25%输出

        self._current_output = max(0.0, final_power)
        self._peak_output = max(self._peak_output, self._current_output)

        return self._current_output

    def update(self, dt: float, output: float):
        """
        更新发电统计

        Args:
            dt: 时间步长 (s)
            output: 当前输出功率 (W)
        """
        energy_wh = output * dt / 3600.0
        self._total_generated += energy_wh

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "current_output_w": self._current_output,
            "peak_output_w": self._peak_output,
            "total_generated_wh": self._total_generated,
            "config": {
                "peak_power_w": self.config.peak_power_watts,
                "efficiency": self.config.panel_efficiency,
                "tracking": self.config.tracking_enabled,
            },
        }


class WindTurbine:
    """
    风力发电机

    模拟风力发电过程。
    """

    def __init__(self, config: Optional[WindConfig] = None):
        """
        初始化风力发电机

        Args:
            config: 风能配置
        """
        self.config = config or WindConfig()
        self._current_output = 0.0
        self._total_generated = 0.0
        self._peak_output = 0.0
        self._rotor_rpm = 0.0

    def calculate_output(self, wind_speed: float, power_factor: float) -> float:
        """
        计算当前发电功率

        Args:
            wind_speed: 风速 (m/s)
            power_factor: 功率因子

        Returns:
            发电功率 (W)
        """
        # 计算转子转速 (简化)
        self._rotor_rpm = wind_speed * 10.0  # 简化关系

        # 计算功率
        self._current_output = self.config.rated_power_watts * power_factor
        self._peak_output = max(self._peak_output, self._current_output)

        return self._current_output

    def update(self, dt: float, output: float):
        """更新发电统计"""
        energy_wh = output * dt / 3600.0
        self._total_generated += energy_wh

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "current_output_w": self._current_output,
            "peak_output_w": self._peak_output,
            "total_generated_wh": self._total_generated,
            "rotor_rpm": self._rotor_rpm,
            "wind_speed_ms": self.config.rated_speed_ms,
        }


class BatteryWithDegradation:
    """
    带退化模型的电池

    模拟电池的充放电和健康退化过程。
    """

    def __init__(
        self,
        capacity_wh: float = 500.0,
        degradation_config: Optional[BatteryDegradationConfig] = None,
    ):
        """
        初始化电池

        Args:
            capacity_wh: 标称容量 (Wh)
            degradation_config: 退化配置
        """
        self._nominal_capacity = capacity_wh
        self._current_capacity = capacity_wh  # 当前实际容量
        self._current_level = capacity_wh     # 当前电量
        self.config = degradation_config or BatteryDegradationConfig()

        # 退化追踪
        self._cycle_count = 0
        self._total_charge_throughput = 0.0
        self._calendar_age_days = 0.0
        self._health_percentage = 100.0

        # 温度追踪
        self._current_temperature = 25.0

    def charge(self, power_watts: float, dt_seconds: float) -> float:
        """
        充电

        Args:
            power_watts: 充电功率 (W)
            dt_seconds: 时间步长 (s)

        Returns:
            实际充入能量 (Wh)
        """
        # 计算可用能量
        available_energy = power_watts * dt_seconds / 3600.0
        remaining_capacity = self._current_capacity - self._current_level

        # 实际充入能量
        actual_energy = min(available_energy, remaining_capacity)
        self._current_level += actual_energy

        # 更新充电吞吐量
        self._total_charge_throughput += actual_energy

        # 检查是否完成一个循环
        if self._current_level >= self._current_capacity:
            self._cycle_count += 0.5  # 充满算半个循环

        # 应用退化
        self._apply_degradation(actual_energy, is_charging=True)

        return actual_energy

    def discharge(self, power_watts: float, dt_seconds: float) -> float:
        """
        放电

        Args:
            power_watts: 放电功率 (W)
            dt_seconds: 时间步长 (s)

        Returns:
            实际放出能量 (Wh)
        """
        # 计算需求能量
        requested_energy = power_watts * dt_seconds / 3600.0

        # 实际放出能量
        actual_energy = min(requested_energy, self._current_level)
        self._current_level -= actual_energy

        # 更新充电吞吐量
        self._total_charge_throughput += actual_energy

        # 检查是否完成一个循环
        if self._current_level <= 0:
            self._cycle_count += 0.5  # 放完算半个循环

        # 应用退化
        self._apply_degradation(actual_energy, is_charging=False)

        return actual_energy

    def _apply_degradation(self, energy_wh: float, is_charging: bool):
        """
        应用电池退化

        Args:
            energy_wh: 能量 (Wh)
            is_charging: 是否为充电
        """
        # 循环退化
        cycle_degradation = (
            energy_wh / self._nominal_capacity / self.config.cycle_life
        )

        # 日历退化 (每天约0.01%)
        calendar_degradation = 0.0001 / 365.0

        # 温度因子 (高温加速退化)
        temp_factor = 1.0
        if self._current_temperature > 30:
            temp_factor = 1.0 + (self._current_temperature - 30) * 0.02
        elif self._current_temperature < 10:
            temp_factor = 1.0 + (10 - self._current_temperature) * 0.01

        # 放电深度因子
        dod = 1.0 - self.soc
        dod_factor = 1.0 + max(0, dod - self.config.depth_of_discharge_limit) * 2.0

        # 总退化
        total_degradation = (
            cycle_degradation + calendar_degradation
        ) * temp_factor * dod_factor

        # 更新容量
        self._current_capacity *= (1.0 - total_degradation)
        self._health_percentage = (self._current_capacity / self._nominal_capacity) * 100.0

    def update_calendar_age(self, dt_seconds: float):
        """更新日历年龄"""
        self._calendar_age_days += dt_seconds / 86400.0

    def set_temperature(self, temperature_c: float):
        """设置温度"""
        self._current_temperature = temperature_c

    @property
    def soc(self) -> float:
        """获取电量状态"""
        if self._current_capacity <= 0:
            return 0.0
        return self._current_level / self._current_capacity

    @property
    def health_percentage(self) -> float:
        """获取健康度"""
        return self._health_percentage

    @property
    def health_state(self) -> BatteryHealthState:
        """获取健康状态"""
        if self._health_percentage > 90:
            return BatteryHealthState.EXCELLENT
        elif self._health_percentage > 70:
            return BatteryHealthState.GOOD
        elif self._health_percentage > 50:
            return BatteryHealthState.FAIR
        elif self._health_percentage > 30:
            return BatteryHealthState.POOR
        else:
            return BatteryHealthState.CRITICAL

    @property
    def current_capacity(self) -> float:
        """获取当前实际容量"""
        return self._current_capacity

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "nominal_capacity_wh": self._nominal_capacity,
            "current_capacity_wh": self._current_capacity,
            "current_level_wh": self._current_level,
            "soc": self.soc,
            "health_percentage": self._health_percentage,
            "health_state": self.health_state.value,
            "cycle_count": self._cycle_count,
            "calendar_age_days": self._calendar_age_days,
            "temperature_c": self._current_temperature,
        }


class EnergyStorageSystem:
    """
    储能系统

    管理多个储能单元。
    """

    def __init__(self, total_capacity_wh: float = 1000.0):
        """
        初始化储能系统

        Args:
            total_capacity_wh: 总容量 (Wh)
        """
        self._batteries: List[BatteryWithDegradation] = []
        self._total_capacity = total_capacity_wh

        # 创建电池单元 (假设每个100Wh)
        num_batteries = int(np.ceil(total_capacity_wh / 100.0))
        for _ in range(num_batteries):
            self._batteries.append(BatteryWithDegradation(capacity_wh=100.0))

    def charge(self, power_watts: float, dt_seconds: float) -> float:
        """
        充电

        Args:
            power_watts: 充电功率 (W)
            dt_seconds: 时间步长 (s)

        Returns:
            实际充入能量 (Wh)
        """
        total_charged = 0.0
        remaining_power = power_watts

        for battery in self._batteries:
            if battery.soc < 1.0 and remaining_power > 0:
                charged = battery.charge(remaining_power, dt_seconds)
                total_charged += charged
                remaining_power -= charged * 3600.0 / dt_seconds

        return total_charged

    def discharge(self, power_watts: float, dt_seconds: float) -> float:
        """
        放电

        Args:
            power_watts: 放电功率 (W)
            dt_seconds: 时间步长 (s)

        Returns:
            实际放出能量 (Wh)
        """
        total_discharged = 0.0
        remaining_power = power_watts

        for battery in self._batteries:
            if battery.soc > 0.0 and remaining_power > 0:
                discharged = battery.discharge(remaining_power, dt_seconds)
                total_discharged += discharged
                remaining_power -= discharged * 3600.0 / dt_seconds

        return total_discharged

    def get_total_soc(self) -> float:
        """获取总电量状态"""
        if not self._batteries:
            return 0.0
        return sum(b.soc for b in self._batteries) / len(self._batteries)

    def get_average_health(self) -> float:
        """获取平均健康度"""
        if not self._batteries:
            return 0.0
        return sum(b.health_percentage for b in self._batteries) / len(self._batteries)

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "num_batteries": len(self._batteries),
            "total_soc": self.get_total_soc(),
            "average_health": self.get_average_health(),
            "total_capacity_wh": sum(b.current_capacity for b in self._batteries),
        }


class RealisticEnergyManager:
    """
    真实能源管理器

    整合太阳能、风能、储能和天气模型。
    """

    def __init__(
        self,
        solar_config: Optional[SolarConfig] = None,
        wind_config: Optional[WindConfig] = None,
        storage_capacity_wh: float = 1000.0,
        day_night_cycle: Optional[DayNightCycle] = None,
    ):
        """
        初始化能源管理器

        Args:
            solar_config: 太阳能配置
            wind_config: 风能配置
            storage_capacity_wh: 储能容量
            day_night_cycle: 日夜循环配置
        """
        self.day_night = day_night_cycle or DayNightCycle()
        self.weather = WeatherModel()
        self.solar = SolarArray(solar_config)
        self.wind = WindTurbine(wind_config)
        self.storage = EnergyStorageSystem(storage_capacity_wh)

        # 时间追踪
        self._current_hour = 12.0  # 从正午开始
        self._current_time = 0.0

        # 统计
        self._total_solar_generated = 0.0
        self._total_wind_generated = 0.0
        self._total_consumed = 0.0

    def update(self, dt: float):
        """
        更新能源系统

        Args:
            dt: 时间步长 (s)
        """
        self._current_time += dt
        self._current_hour = (self._current_hour + dt / 3600.0) % 24.0

        # 更新天气
        self.weather.update(dt)

        # 计算太阳能发电
        daylight_factor = self.day_night.get_daylight_factor(self._current_hour)
        sun_elevation, _ = self.day_night.get_sun_position(self._current_hour)
        weather_efficiency = self.weather.get_solar_efficiency()

        solar_output = self.solar.calculate_output(
            daylight_factor, weather_efficiency, sun_elevation
        )
        self.solar.update(dt, solar_output)

        # 计算风能发电
        wind_factor = self.weather.get_wind_power_factor()
        wind_output = self.wind.calculate_output(
            self.weather.wind_speed_ms, wind_factor
        )
        self.wind.update(dt, wind_output)

        # 总发电量
        total_generation = solar_output + wind_output

        # 存储过剩能量
        if total_generation > 0:
            stored = self.storage.charge(total_generation, dt)
            self._total_solar_generated += solar_output * dt / 3600.0
            self._total_wind_generated += wind_output * dt / 3600.0

        # 更新电池日历年龄
        for battery in self.storage._batteries:
            battery.update_calendar_age(dt)
            battery.set_temperature(self.weather.temperature_c)

    def consume(self, power_watts: float, dt: float) -> float:
        """
        消耗能量

        Args:
            power_watts: 需求功率 (W)
            dt: 时间步长 (s)

        Returns:
            实际获得能量 (Wh)
        """
        # 首先使用当前发电
        current_generation = self.solar._current_output + self.wind._current_output

        if current_generation >= power_watts:
            # 直接使用发电
            self._total_consumed += power_watts * dt / 3600.0
            return power_watts * dt / 3600.0

        # 使用储能补充
        deficit = power_watts - current_generation
        from_storage = self.storage.discharge(deficit, dt)

        total_consumed = (current_generation + deficit) * dt / 3600.0
        self._total_consumed += total_consumed

        return total_consumed

    def get_generation_status(self) -> Dict[str, Any]:
        """获取发电状态"""
        return {
            "solar": self.solar.get_status(),
            "wind": self.wind.get_status(),
            "storage": self.storage.get_status(),
            "weather": {
                "condition": self.weather.current_condition.value,
                "cloud_cover": self.weather.cloud_cover,
                "wind_speed_ms": self.weather.wind_speed_ms,
                "temperature_c": self.weather.temperature_c,
            },
            "time": {
                "hour": self._current_hour,
                "is_daytime": self.day_night.is_daytime(self._current_hour),
                "daylight_factor": self.day_night.get_daylight_factor(self._current_hour),
            },
            "totals": {
                "solar_generated_wh": self._total_solar_generated,
                "wind_generated_wh": self._total_wind_generated,
                "consumed_wh": self._total_consumed,
            },
        }

    def get_energy_balance(self) -> Dict[str, float]:
        """获取能量平衡"""
        return {
            "total_generated_wh": self._total_solar_generated + self._total_wind_generated,
            "total_consumed_wh": self._total_consumed,
            "net_balance_wh": self._total_solar_generated + self._total_wind_generated - self._total_consumed,
            "storage_soc": self.storage.get_total_soc(),
        }

    def forecast(self, hours: float = 24.0) -> List[Dict[str, Any]]:
        """
        预测未来能源生成

        Args:
            hours: 预测时长 (小时)

        Returns:
            预测数据列表
        """
        forecast_data = []
        current_hour = self._current_hour

        for h in range(int(hours)):
            future_hour = (current_hour + h) % 24.0

            # 预测日照
            daylight_factor = self.day_night.get_daylight_factor(future_hour)
            sun_elevation, _ = self.day_night.get_sun_position(future_hour)

            # 假设天气保持稳定 (简化)
            weather_efficiency = self.weather.get_solar_efficiency()
            solar_output = self.solar.config.peak_power_watts * daylight_factor * weather_efficiency * np.sin(np.radians(sun_elevation))

            # 预测风能
            wind_factor = self.weather.get_wind_power_factor()
            wind_output = self.wind.config.rated_power_watts * wind_factor

            forecast_data.append({
                "hour": future_hour,
                "solar_output_w": max(0, solar_output),
                "wind_output_w": wind_output,
                "total_output_w": max(0, solar_output) + wind_output,
                "daylight_factor": daylight_factor,
            })

        return forecast_data
