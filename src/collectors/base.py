"""
采集器基类 - 定义可扩展的采集器接口
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from datetime import datetime
import hashlib
import uuid

from ..core.models import (
    MetadataEntity, 
    MetadataRelationship, 
    CollectionResult,
    MetadataType,
    RelationshipType
)


class BaseCollector(ABC):
    """采集器基类"""
    
    def __init__(self, name: str, source: str, config: Optional[Dict[str, Any]] = None):
        """
        初始化采集器
        
        Args:
            name: 采集器名称
            source: 数据源标识
            config: 配置信息（可包含entity_model元模型信息）
        """
        self.name = name
        self.source = source
        self.config = config or {}
        self.collected_at = datetime.now()
        
        # 从配置中提取元模型信息
        self.entity_model = self.config.get("entity_model")
        self.entity_type = self.config.get("entity_type")
    
    @abstractmethod
    def collect(self, *args, **kwargs) -> CollectionResult:
        """
        执行采集操作
        
        Returns:
            采集结果
        """
        pass
    
    def generate_id(self, *parts: str) -> str:
        """
        生成唯一ID
        
        Args:
            *parts: ID组成部分
            
        Returns:
            唯一ID
        """
        combined = f"{self.source}:{':'.join(str(p) for p in parts)}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def create_entity(self, 
                     entity_type: Union[MetadataType, str],
                     name: str,
                     description: Optional[str] = None,
                     properties: Optional[Dict[str, Any]] = None,
                     entity_id: Optional[str] = None) -> MetadataEntity:
        """
        创建元数据实体
        
        Args:
            entity_type: 实体类型（MetadataType枚举或字符串类型名）
            name: 名称
            description: 描述
            properties: 扩展属性
            entity_id: 实体ID（可选，自动生成）
            
        Returns:
            元数据实体
        """
        # 如果传入的是字符串类型，直接使用；如果是MetadataType枚举，转换为字符串
        if isinstance(entity_type, MetadataType):
            type_str = entity_type.value
        else:
            type_str = str(entity_type)
        
        if entity_id is None:
            entity_id = self.generate_id(type_str, name)
        
        # 合并properties，确保采集时间被设置
        final_properties = properties or {}
        # 如果properties中没有collected_at，则添加采集时间
        if 'collected_at' not in final_properties:
            final_properties['collected_at'] = self.collected_at.isoformat()
        
        return MetadataEntity(
            id=entity_id,
            type=type_str,  # MetadataEntity.type现在接受字符串
            name=name,
            description=description,
            properties=final_properties,
            source=self.source
        )
    
    def create_relationship(self,
                           source_id: str,
                           target_id: str,
                           relationship_type: Union[RelationshipType, str],
                           properties: Optional[Dict[str, Any]] = None) -> MetadataRelationship:
        """
        创建元数据关系
        
        Args:
            source_id: 源实体ID
            target_id: 目标实体ID
            relationship_type: 关系类型（RelationshipType枚举或字符串类型名）
            properties: 关系属性
            
        Returns:
            元数据关系
        """
        # 如果传入的是字符串类型，直接使用；如果是RelationshipType枚举，转换为字符串
        if isinstance(relationship_type, RelationshipType):
            type_str = relationship_type.value
        else:
            type_str = str(relationship_type)
        
        return MetadataRelationship(
            source_id=source_id,
            target_id=target_id,
            type=type_str,  # MetadataRelationship.type现在接受字符串
            properties=properties or {}
        )
    
    def validate_config(self, required_keys: list) -> bool:
        """
        验证配置
        
        Args:
            required_keys: 必需的配置键列表
            
        Returns:
            是否有效
        """
        return all(key in self.config for key in required_keys)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值
        """
        return self.config.get(key, default)
    
    def get_entity_model(self) -> Optional[Dict[str, Any]]:
        """
        获取实体元模型信息
        
        Returns:
            实体元模型字典或None
        """
        return self.entity_model
    
    def get_entity_type(self) -> Optional[str]:
        """
        获取实体类型
        
        Returns:
            实体类型字符串或None
        """
        return self.entity_type





