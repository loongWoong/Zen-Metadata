"""
采集器工厂 - 根据元模型动态创建采集器实例
"""
from typing import Dict, Any, Optional, Type
from pathlib import Path

from .base import BaseCollector
from ..core.metamodel_registry import MetaRegistry
from ..core.metamodel import EntityMetaModel


class CollectorFactory:
    """采集器工厂"""
    
    def __init__(self, meta_registry: MetaRegistry):
        """
        初始化采集器工厂
        
        Args:
            meta_registry: 元模型注册表
        """
        self.meta_registry = meta_registry
    
    def create_collector(
        self, 
        entity_type: str,
        source: str,
        config: Optional[Dict[str, Any]] = None,
        entity_model: Optional[EntityMetaModel] = None
    ) -> Optional[BaseCollector]:
        """
        根据实体类型创建采集器实例
        
        Args:
            entity_type: 实体类型（如 "GitRepository", "Database" 等）
            source: 数据源标识
            config: 采集器配置
            entity_model: 实体元模型（可选，如果不提供则从注册表获取）
            
        Returns:
            采集器实例或None
        """
        if entity_model is None:
            entity_model = self.meta_registry.get_entity_model(entity_type)
            if not entity_model:
                return None
        
        # 获取采集器类
        collector_class = self.meta_registry.get_collector(entity_type)
        if not collector_class:
            return None
        
        # 合并配置：元模型中的collector配置 + 传入的config
        collector_config = entity_model.collector or {}
        merged_config = {
            **collector_config.get("params", {}),
            **(config or {})
        }
        
        # 添加元模型信息到配置中
        merged_config["entity_model"] = entity_model.to_dict()
        merged_config["entity_type"] = entity_type
        
        # 创建采集器实例
        try:
            collector = collector_class(
                name=entity_type,
                source=source,
                config=merged_config
            )
            return collector
        except Exception as e:
            print(f"创建采集器失败 ({entity_type}): {e}")
            return None
    
    def create_collector_by_collector_type(
        self,
        collector_type: str,
        source: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[BaseCollector]:
        """
        根据采集器类型（collector_type字符串）创建采集器实例
        优先使用元模型中定义的collector_type映射
        
        Args:
            collector_type: 采集器类型字符串（如 "git_repository", "code_metadata" 等）
            source: 数据源标识
            config: 采集器配置
            
        Returns:
            采集器实例或None
        """
        # 首先尝试从collector_type_map中获取实体类型（优先使用元模型定义的映射）
        entity_type = self.meta_registry.get_entity_type_by_collector_type(collector_type)
        if entity_type:
            collector = self.create_collector(entity_type, source, config)
            if collector:
                return collector
        
        # 如果collector_type_map中没有，尝试多种可能的实体类型名称（向后兼容）
        possible_types = [
            ''.join(word.capitalize() for word in collector_type.split('_')),  # git_repository -> GitRepository
            collector_type.replace('_', '').title(),  # git_repository -> Gitrepository
            collector_type.replace('_', ''),  # git_repository -> gitrepository
            collector_type,  # git_repository
            collector_type.title(),  # git_repository -> Git_Repository
        ]
        
        # 遍历所有可能的类型
        for entity_type in possible_types:
            collector = self.create_collector(entity_type, source, config)
            if collector:
                return collector
        
        return None
    
    def list_available_collectors(self) -> Dict[str, Dict[str, Any]]:
        """
        列出所有可用的采集器
        
        Returns:
            采集器信息字典，key为实体类型，value为采集器信息
        """
        collectors_info = {}
        
        for entity_type, collector_class in self.meta_registry.collectors.items():
            entity_model = self.meta_registry.get_entity_model(entity_type)
            if entity_model:
                collectors_info[entity_type] = {
                    "entity_type": entity_type,
                    "label": entity_model.label,
                    "description": entity_model.description,
                    "version": entity_model.version,
                    "collector_class": collector_class.__name__,
                    "collector_config": entity_model.collector
                }
        
        return collectors_info

