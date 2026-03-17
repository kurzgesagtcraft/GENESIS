"""
GENESIS Configuration Module - 配置管理模块

使用 OmegaConf 进行配置管理，支持 YAML 文件加载和配置合并。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from omegaconf import DictConfig, OmegaConf


class Config:
    """
    配置类，封装 OmegaConf 配置对象。
    
    提供点号访问、配置合并、保存等功能。
    """
    
    def __init__(self, cfg: Optional[DictConfig] = None) -> None:
        """初始化配置对象。"""
        self._cfg = cfg if cfg is not None else OmegaConf.create()
    
    def __getattr__(self, name: str) -> Any:
        """点号访问配置项。"""
        if name.startswith("_"):
            return super().__getattribute__(name)
        return OmegaConf.select(self._cfg, name)
    
    def __setattr__(self, name: str, value: Any) -> None:
        """点号设置配置项。"""
        if name.startswith("_"):
            super().__setattr__(name, value)
        else:
            OmegaConf.update(self._cfg, name, value)
    
    def __getitem__(self, key: str) -> Any:
        """字典式访问。"""
        return self._cfg[key]
    
    def __setitem__(self, key: str, value: Any) -> None:
        """字典式设置。"""
        self._cfg[key] = value
    
    def __contains__(self, key: str) -> bool:
        """检查键是否存在。"""
        return key in self._cfg
    
    def __repr__(self) -> str:
        """字符串表示。"""
        return f"Config({OmegaConf.to_yaml(self._cfg)})"
    
    def __str__(self) -> str:
        """字符串表示。"""
        return OmegaConf.to_yaml(self._cfg)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。"""
        return OmegaConf.to_container(self._cfg, resolve=True)
    
    def to_yaml(self) -> str:
        """转换为 YAML 字符串。"""
        return OmegaConf.to_yaml(self._cfg)
    
    def merge(self, other: Union[Config, DictConfig, Dict[str, Any]]) -> Config:
        """
        合并另一个配置。
        
        Args:
            other: 要合并的配置
            
        Returns:
            合并后的新配置对象
        """
        if isinstance(other, Config):
            other_cfg = other._cfg
        elif isinstance(other, dict):
            other_cfg = OmegaConf.create(other)
        else:
            other_cfg = other
        
        merged = OmegaConf.merge(self._cfg, other_cfg)
        return Config(merged)
    
    def update(self, key: str, value: Any) -> None:
        """更新配置项。"""
        OmegaConf.update(self._cfg, key, value)
    
    def save(self, path: Union[str, Path]) -> None:
        """保存配置到 YAML 文件。"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            OmegaConf.save(self._cfg, f, resolve=True)
    
    @classmethod
    def from_yaml(cls, path: Union[str, Path]) -> Config:
        """
        从 YAML 文件加载配置。
        
        Args:
            path: YAML 文件路径
            
        Returns:
            配置对象
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        
        with open(path, "r", encoding="utf-8") as f:
            cfg = OmegaConf.load(f)
        return cls(cfg)
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> Config:
        """从字典创建配置。"""
        return cls(OmegaConf.create(d))
    
    @classmethod
    def create(cls, **kwargs: Any) -> Config:
        """从关键字参数创建配置。"""
        return cls(OmegaConf.create(kwargs))


def load_config(
    config_path: Union[str, Path, None] = None,
    overrides: Optional[Dict[str, Any]] = None,
    default_config: Optional[Dict[str, Any]] = None,
) -> Config:
    """
    加载配置文件。
    
    Args:
        config_path: 配置文件路径，支持 YAML 格式
        overrides: 配置覆盖项，优先级最高
        default_config: 默认配置，优先级最低
        
    Returns:
        配置对象
        
    Example:
        >>> cfg = load_config("configs/world_config.yaml")
        >>> print(cfg.world.size)
        [50.0, 50.0]
    """
    configs = []
    
    # 1. 默认配置
    if default_config is not None:
        configs.append(OmegaConf.create(default_config))
    
    # 2. 文件配置
    if config_path is not None:
        path = Path(config_path)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                configs.append(OmegaConf.load(f))
        else:
            raise FileNotFoundError(f"Config file not found: {path}")
    
    # 3. 覆盖配置
    if overrides is not None:
        configs.append(OmegaConf.create(overrides))
    
    # 合并所有配置
    if len(configs) == 0:
        return Config()
    elif len(configs) == 1:
        return Config(configs[0])
    else:
        merged = OmegaConf.merge(*configs)
        return Config(merged)


def merge_configs(*configs: Config) -> Config:
    """
    合并多个配置对象。
    
    后面的配置会覆盖前面的配置。
    
    Args:
        *configs: 配置对象列表
        
    Returns:
        合并后的配置对象
    """
    if len(configs) == 0:
        return Config()
    
    cfg_list = [c._cfg for c in configs]
    merged = OmegaConf.merge(*cfg_list)
    return Config(merged)
