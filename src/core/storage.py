"""
存储层抽象接口
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

from .models import MetadataEntity, MetadataRelationship, QueryResult


class StorageInterface(ABC):
    """存储接口抽象类"""
    
    @abstractmethod
    def add_entity(self, entity: MetadataEntity) -> bool:
        """添加实体"""
        pass
    
    @abstractmethod
    def add_relationship(self, relationship: MetadataRelationship) -> bool:
        """添加关系"""
        pass
    
    @abstractmethod
    def query(self, query: str, params: Optional[Dict[str, Any]] = None) -> QueryResult:
        """执行查询"""
        pass
    
    @abstractmethod
    def find_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """查找实体"""
        pass
    
    @abstractmethod
    def delete_entity(self, entity_id: str) -> bool:
        """删除实体"""
        pass



