"""
GENESIS 能量分析模块

分析系统能量收支，计算制造产品的净能量成本，
评估太阳能发电覆盖能力，提供能源优化建议。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import json
import math
from pathlib import Path
from datetime import datetime


class EnergySourceType(Enum):
    """能源类型"""
    SOLAR = "solar"           # 太阳能
    BATTERY = "battery"       # 电池
    GRID = "grid"             # 电网（备用）
    UNKNOWN = "unknown"       # 未知


class EnergyConsumerType(Enum):
    """能耗类型"""
    NAVIGATION = "navigation"       # 移动能耗
    MANIPULATION = "manipulation"   # 操作能耗
    STATION = "station"             # 工站能耗
    PERCEPTION = "perception"       # 感知能耗
    COMPUTATION = "computation"     # 计算能耗
    STANDBY = "standby"             # 待机能耗
    CHARGING_LOSS = "charging_loss" # 充电损耗
    UNKNOWN = "unknown"             # 未知


@dataclass
class EnergyEvent:
    """能量事件记录"""
    timestamp: float
    event_type: str
    source: EnergySourceType
    consumer: EnergyConsumerType
    power_watts: float
    duration_seconds: float
    energy_wh: float
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source": self.source.value,
            "consumer": self.consumer.value,
            "power_watts": self.power_watts,
            "duration_seconds": self.duration_seconds,
            "energy_wh": self.energy_wh,
            "metadata": self.metadata,
        }


@dataclass
class EnergyBalance:
    """能量平衡统计"""
    # 发电统计
    total_generated: float = 0.0       # 总发电量 (Wh)
    solar_generated: float = 0.0       # 太阳能发电 (Wh)
    grid_imported: float = 0.0         # 电网输入 (Wh)
    
    # 消耗统计
    total_consumed: float = 0.0        # 总消耗 (Wh)
    navigation_consumed: float = 0.0   # 移动消耗 (Wh)
    manipulation_consumed: float = 0.0 # 操作消耗 (Wh)
    station_consumed: float = 0.0      # 工站消耗 (Wh)
    perception_consumed: float = 0.0   # 感知消耗 (Wh)
    computation_consumed: float = 0.0  # 计算消耗 (Wh)
    standby_consumed: float = 0.0      # 待机消耗 (Wh)
    charging_loss: float = 0.0         # 充电损耗 (Wh)
    
    # 电池统计
    battery_start: float = 0.0         # 初始电量 (Wh)
    battery_end: float = 0.0           # 结束电量 (Wh)
    battery_capacity: float = 500.0    # 电池容量 (Wh)
    
    # 时间统计
    total_time: float = 0.0            # 总时间 (秒)
    
    @property
    def net_energy(self) -> float:
        """净能量 (发电 - 消耗)"""
        return self.total_generated - self.total_consumed
    
    @property
    def energy_ratio(self) -> float:
        """能量比率 (发电/消耗)"""
        return self.total_generated / self.total_consumed if self.total_consumed > 0 else 0.0
    
    @property
    def is_energy_positive(self) -> bool:
        """是否能量正收益"""
        return self.net_energy >= 0
    
    @property
    def self_sufficiency_ratio(self) -> float:
        """自给自足率 (太阳能/总消耗)"""
        return self.solar_generated / self.total_consumed if self.total_consumed > 0 else 0.0
    
    @property
    def average_power(self) -> float:
        """平均功率 (W)"""
        if self.total_time <= 0:
            return 0.0
        return self.total_consumed / (self.total_time / 3600)
    
    @property
    def navigation_ratio(self) -> float:
        """移动能耗占比"""
        return self.navigation_consumed / self.total_consumed if self.total_consumed > 0 else 0.0
    
    @property
    def manipulation_ratio(self) -> float:
        """操作能耗占比"""
        return self.manipulation_consumed / self.total_consumed if self.total_consumed > 0 else 0.0
    
    @property
    def station_ratio(self) -> float:
        """工站能耗占比"""
        return self.station_consumed / self.total_consumed if self.total_consumed > 0 else 0.0
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_generated": self.total_generated,
            "solar_generated": self.solar_generated,
            "grid_imported": self.grid_imported,
            "total_consumed": self.total_consumed,
            "navigation_consumed": self.navigation_consumed,
            "manipulation_consumed": self.manipulation_consumed,
            "station_consumed": self.station_consumed,
            "perception_consumed": self.perception_consumed,
            "computation_consumed": self.computation_consumed,
            "standby_consumed": self.standby_consumed,
            "charging_loss": self.charging_loss,
            "battery_start": self.battery_start,
            "battery_end": self.battery_end,
            "battery_capacity": self.battery_capacity,
            "total_time": self.total_time,
            "net_energy": self.net_energy,
            "energy_ratio": self.energy_ratio,
            "is_energy_positive": self.is_energy_positive,
            "self_sufficiency_ratio": self.self_sufficiency_ratio,
            "average_power": self.average_power,
            "navigation_ratio": self.navigation_ratio,
            "manipulation_ratio": self.manipulation_ratio,
            "station_ratio": self.station_ratio,
        }


@dataclass
class EnergyReport:
    """能量分析报告"""
    balance: EnergyBalance
    timeline: List[Dict] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    solar_coverage_analysis: Dict = field(default_factory=dict)
    cost_per_product: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "balance": self.balance.to_dict(),
            "timeline": self.timeline,
            "recommendations": self.recommendations,
            "solar_coverage_analysis": self.solar_coverage_analysis,
            "cost_per_product": self.cost_per_product,
        }


class EnergyAnalyzer:
    """能量分析器"""
    
    # 默认功率参数 (W)
    DEFAULT_POWER_PARAMS = {
        "navigation": 50.0,      # 移动功率
        "manipulation": 80.0,    # 操作功率
        "perception": 15.0,      # 感知功率
        "computation": 30.0,     # 计算功率
        "standby": 10.0,         # 待机功率
        "charging_efficiency": 0.85,  # 充电效率
    }
    
    # �站功率参数 (W)
    STATION_POWER_PARAMS = {
        "smelter": 500.0,
        "fabricator": 800.0,
        "assembler": 200.0,
    }
    
    def __init__(
        self,
        battery_capacity: float = 500.0,
        solar_peak_power: float = 100.0,
        power_params: Optional[Dict] = None,
    ):
        """
        初始化能量分析器
        
        Args:
            battery_capacity: 电池容量 (Wh)
            solar_peak_power: 太阳能峰值功率 (W)
            power_params: 功率参数覆盖
        """
        self.battery_capacity = battery_capacity
        self.solar_peak_power = solar_peak_power
        self.power_params = {**self.DEFAULT_POWER_PARAMS, **(power_params or {})}
        
        self.events: List[EnergyEvent] = []
        self.balance = EnergyBalance(battery_capacity=battery_capacity)
        
    def add_event(self, event: EnergyEvent) -> None:
        """添加能量事件"""
        self.events.append(event)
        
    def add_generation(
        self,
        timestamp: float,
        power_watts: float,
        duration_seconds: float,
        source: EnergySourceType = EnergySourceType.SOLAR,
        metadata: Optional[Dict] = None,
    ) -> None:
        """添加发电事件"""
        energy_wh = power_watts * duration_seconds / 3600
        
        event = EnergyEvent(
            timestamp=timestamp,
            event_type="generation",
            source=source,
            consumer=EnergyConsumerType.UNKNOWN,
            power_watts=power_watts,
            duration_seconds=duration_seconds,
            energy_wh=energy_wh,
            metadata=metadata or {},
        )
        self.add_event(event)
        
    def add_consumption(
        self,
        timestamp: float,
        power_watts: float,
        duration_seconds: float,
        consumer: EnergyConsumerType,
        metadata: Optional[Dict] = None,
    ) -> None:
        """添加消耗事件"""
        energy_wh = power_watts * duration_seconds / 3600
        
        event = EnergyEvent(
            timestamp=timestamp,
            event_type="consumption",
            source=EnergySourceType.BATTERY,
            consumer=consumer,
            power_watts=power_watts,
            duration_seconds=duration_seconds,
            energy_wh=energy_wh,
            metadata=metadata or {},
        )
        self.add_event(event)
    
    def analyze(self) -> EnergyBalance:
        """分析所有能量事件"""
        self.balance = EnergyBalance(battery_capacity=self.battery_capacity)
        
        if not self.events:
            return self.balance
        
        # 按时间排序
        sorted_events = sorted(self.events, key=lambda e: e.timestamp)
        
        for event in sorted_events:
            if event.event_type == "generation":
                self.balance.total_generated += event.energy_wh
                if event.source == EnergySourceType.SOLAR:
                    self.balance.solar_generated += event.energy_wh
                elif event.source == EnergySourceType.GRID:
                    self.balance.grid_imported += event.energy_wh
                    
            elif event.event_type == "consumption":
                self.balance.total_consumed += event.energy_wh
                if event.consumer == EnergyConsumerType.NAVIGATION:
                    self.balance.navigation_consumed += event.energy_wh
                elif event.consumer == EnergyConsumerType.MANIPULATION:
                    self.balance.manipulation_consumed += event.energy_wh
                elif event.consumer == EnergyConsumerType.STATION:
                    self.balance.station_consumed += event.energy_wh
                elif event.consumer == EnergyConsumerType.PERCEPTION:
                    self.balance.perception_consumed += event.energy_wh
                elif event.consumer == EnergyConsumerType.COMPUTATION:
                    self.balance.computation_consumed += event.energy_wh
                elif event.consumer == EnergyConsumerType.STANDBY:
                    self.balance.standby_consumed += event.energy_wh
                elif event.consumer == EnergyConsumerType.CHARGING_LOSS:
                    self.balance.charging_loss += event.energy_wh
        
        # 计算总时间
        if sorted_events:
            self.balance.total_time = sorted_events[-1].timestamp - sorted_events[0].timestamp
        
        return self.balance
    
    def analyze_solar_coverage(
        self,
        day_length_hours: float = 24.0,
        peak_hours: Tuple[float, float] = (10.0, 14.0),
    ) -> Dict:
        """
        分析太阳能覆盖能力
        
        Args:
            day_length_hours: 一天时长（模拟日夜循环）
            peak_hours: 峰值发电时段 (开始小时, 结束小时)
        
        Returns:
            太阳能覆盖分析结果
        """
        # 计算日均发电量
        # 假设正弦曲线模拟日照变化
        peak_start, peak_end = peak_hours
        peak_duration = peak_end - peak_start
        
        # 简化计算：峰值时段满功率，其他时段按比例
        avg_power_factor = 0.5  # 平均功率因子
        daily_solar_wh = self.solar_peak_power * day_length_hours * avg_power_factor
        
        # 计算日均消耗
        if self.balance.total_time > 0:
            hours = self.balance.total_time / 3600
            daily_consumption_wh = self.balance.total_consumed * (day_length_hours / hours)
        else:
            daily_consumption_wh = 0.0
        
        # 计算覆盖率
        coverage_ratio = daily_solar_wh / daily_consumption_wh if daily_consumption_wh > 0 else 0.0
        
        # 计算需要的太阳能板面积
        required_solar_power = daily_consumption_wh / (day_length_hours * avg_power_factor)
        required_panels = required_solar_power / self.solar_peak_power
        
        return {
            "daily_solar_generation_wh": daily_solar_wh,
            "daily_consumption_wh": daily_consumption_wh,
            "coverage_ratio": coverage_ratio,
            "is_self_sufficient": coverage_ratio >= 1.0,
            "current_solar_peak_power_w": self.solar_peak_power,
            "required_solar_peak_power_w": required_solar_power,
            "required_panels_multiplier": required_panels,
            "peak_hours": peak_hours,
            "day_length_hours": day_length_hours,
        }
    
    def calculate_product_energy_cost(
        self,
        product_type: str,
        quantity: int = 1,
    ) -> float:
        """
        计算产品能量成本
        
        Args:
            product_type: 产品类型
            quantity: 数量
        
        Returns:
            单位产品能量成本 (Wh)
        """
        # 产品能量成本估算（基于配方）
        # 这里使用简化模型，实际应从配方系统获取
        
        PRODUCT_ENERGY_COSTS = {
            "iron_bar": 500.0,          # 冶炼能耗
            "circuit_board": 800.0,     # 加工能耗
            "motor": 1000.0,            # 加工能耗
            "joint_module": 600.0,      # 加工能耗
            "frame_segment": 700.0,     # 加工能耗
            "controller_board": 1500.0, # 加工能耗
            "gripper_finger": 300.0,    # 加工能耗
            "assembled_arm": 200.0,     # 装配能耗
            "assembled_robot": 500.0,   # 装配能耗
        }
        
        base_cost = PRODUCT_ENERGY_COSTS.get(product_type, 0.0)
        
        # 加上运输和操作能耗估算
        transport_cost = 50.0  # 每次运输约 50Wh
        operation_cost = 20.0  # 每次操作约 20Wh
        
        # 简化：假设每个产品需要 3 次运输和 5 次操作
        total_cost = base_cost + transport_cost * 3 + operation_cost * 5
        
        return total_cost * quantity
    
    def generate_recommendations(self) -> List[str]:
        """生成能源优化建议"""
        recommendations = []
        
        if self.balance.total_consumed == 0:
            return ["无能耗数据，无法生成建议"]
        
        # 分析能量比率
        if self.balance.energy_ratio < 0.8:
            recommendations.append(
                f"能量比率仅为 {self.balance.energy_ratio:.1%}，"
                f"建议增加太阳能板面积或降低能耗"
            )
        
        # 分析自给自足率
        solar_analysis = self.analyze_solar_coverage()
        if not solar_analysis["is_self_sufficient"]:
            recommendations.append(
                f"太阳能覆盖率 {solar_analysis['coverage_ratio']:.1%}，"
                f"需要约 {solar_analysis['required_panels_multiplier']:.1f} 倍太阳能板"
            )
        
        # 分析能耗分布
        if self.balance.navigation_ratio > 0.4:
            recommendations.append(
                f"移动能耗占比 {self.balance.navigation_ratio:.1%}，"
                f"建议优化路径规划减少往返"
            )
        
        if self.balance.station_ratio > 0.5:
            recommendations.append(
                f"工站能耗占比 {self.balance.station_ratio:.1%}，"
                f"建议在工站加工期间执行其他任务"
            )
        
        # 充电策略建议
        if self.balance.charging_loss > self.balance.total_consumed * 0.1:
            recommendations.append(
                "充电损耗较高，建议优化充电时机，"
                "在日照高峰期充电以提高效率"
            )
        
        # 电池容量建议
        if self.balance.battery_capacity < self.balance.total_consumed * 0.2:
            recommendations.append(
                f"电池容量 {self.balance.battery_capacity:.0f}Wh 可能不足，"
                f"建议增加容量以减少充电次数"
            )
        
        return recommendations
    
    def get_report(self) -> EnergyReport:
        """生成完整分析报告"""
        self.analyze()
        
        # 生成时间线数据
        timeline = [e.to_dict() for e in sorted(self.events, key=lambda e: e.timestamp)]
        
        # 生成建议
        recommendations = self.generate_recommendations()
        
        # 太阳能覆盖分析
        solar_analysis = self.analyze_solar_coverage()
        
        # 计算主要产品能量成本
        cost_per_product = {
            "iron_bar": self.calculate_product_energy_cost("iron_bar"),
            "motor": self.calculate_product_energy_cost("motor"),
            "assembled_arm": self.calculate_product_energy_cost("assembled_arm"),
            "assembled_robot": self.calculate_product_energy_cost("assembled_robot"),
        }
        
        return EnergyReport(
            balance=self.balance,
            timeline=timeline,
            recommendations=recommendations,
            solar_coverage_analysis=solar_analysis,
            cost_per_product=cost_per_product,
        )
    
    def save_report(self, filepath: str) -> None:
        """保存报告到文件"""
        report = self.get_report()
        
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
    
    def load_from_log(self, log_path: str) -> int:
        """从日志文件加载能量事件"""
        path = Path(log_path)
        if not path.exists():
            return 0
        
        loaded_count = 0
        
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                    
                    # 解析能量相关日志
                    if "energy" in entry:
                        energy_info = entry["energy"]
                        
                        if energy_info.get("type") == "generation":
                            self.add_generation(
                                timestamp=entry.get("time", 0),
                                power_watts=energy_info.get("power", 0),
                                duration_seconds=energy_info.get("duration", 1),
                                source=EnergySourceType.SOLAR,
                                metadata=energy_info,
                            )
                        elif energy_info.get("type") == "consumption":
                            consumer_map = {
                                "navigation": EnergyConsumerType.NAVIGATION,
                                "manipulation": EnergyConsumerType.MANIPULATION,
                                "station": EnergyConsumerType.STATION,
                                "perception": EnergyConsumerType.PERCEPTION,
                                "computation": EnergyConsumerType.COMPUTATION,
                                "standby": EnergyConsumerType.STANDBY,
                            }
                            consumer = consumer_map.get(
                                energy_info.get("consumer", "unknown"),
                                EnergyConsumerType.UNKNOWN
                            )
                            self.add_consumption(
                                timestamp=entry.get("time", 0),
                                power_watts=energy_info.get("power", 0),
                                duration_seconds=energy_info.get("duration", 1),
                                consumer=consumer,
                                metadata=energy_info,
                            )
                        loaded_count += 1
                        
                except json.JSONDecodeError:
                    continue
        
        return loaded_count
    
    def clear(self) -> None:
        """清空所有记录"""
        self.events.clear()
        self.balance = EnergyBalance(battery_capacity=self.battery_capacity)


# 便捷函数
def analyze_energy(log_path: str) -> Dict:
    """分析日志文件并返回能量报告"""
    analyzer = EnergyAnalyzer()
    analyzer.load_from_log(log_path)
    return analyzer.get_report().to_dict()


def calculate_energy_ratio(generated: float, consumed: float) -> float:
    """计算能量比率"""
    return generated / consumed if consumed > 0 else 0.0
