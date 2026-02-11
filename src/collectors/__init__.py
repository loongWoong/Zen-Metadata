"""
元数据采集器模块 - 可扩展的采集器框架
"""
from .base import BaseCollector
from .factory import CollectorFactory
from .task_config import CollectionTaskConfig

__all__ = [
    "BaseCollector",
    "CollectorFactory",
    "CollectionTaskConfig"
]


