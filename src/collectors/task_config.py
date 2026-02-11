"""
采集任务配置模型
"""
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CollectionTaskConfig(BaseModel):
    """采集任务配置"""
    
    # 基本信息
    entity_type: str = Field(..., description="实体类型（如 'GitRepository', 'Database' 等）")
    source: str = Field(..., description="数据源标识")
    
    # 采集器配置
    collector_config: Dict[str, Any] = Field(
        default_factory=dict,
        description="采集器特定配置（如连接字符串、路径等）"
    )
    
    # 元模型包信息（可选）
    package_name: Optional[str] = Field(None, description="元模型包名")
    
    # 过滤和选项
    filters: Optional[Dict[str, Any]] = Field(None, description="采集过滤条件")
    options: Optional[Dict[str, Any]] = Field(None, description="采集选项")
    
    # 增量采集
    incremental: bool = Field(default=False, description="是否为增量采集")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entity_type": self.entity_type,
            "source": self.source,
            "collector_config": self.collector_config,
            "package_name": self.package_name,
            "filters": self.filters,
            "options": self.options,
            "incremental": self.incremental
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollectionTaskConfig":
        """从字典创建"""
        return cls(**data)
    
    @classmethod
    def from_metamodel_package(
        cls,
        package_name: str,
        entity_types: List[str],
        source: str,
        collector_config: Optional[Dict[str, Any]] = None
    ) -> List["CollectionTaskConfig"]:
        """
        从元模型包创建多个采集任务配置
        
        Args:
            package_name: 包名
            entity_types: 实体类型列表
            source: 数据源标识
            collector_config: 采集器配置
            
        Returns:
            采集任务配置列表
        """
        configs = []
        for entity_type in entity_types:
            config = cls(
                entity_type=entity_type,
                source=source,
                collector_config=collector_config or {},
                package_name=package_name
            )
            configs.append(config)
        return configs



