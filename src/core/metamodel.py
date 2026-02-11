"""
元模型数据模型
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    """属性类型枚举"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ENUM = "enum"
    JSON = "json"


class EntityMetaModel(BaseModel):
    """实体元模型"""
    type: str = Field(..., description="实体类型标识符（唯一）")
    version: str = Field(default="v1", description="版本号")
    label: str = Field(..., description="显示标签")
    description: Optional[str] = Field(None, description="描述")
    
    # 属性定义
    properties: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="属性定义，key为属性名，value为属性配置"
    )
    
    # 关系定义
    relationships: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="允许的关系类型和目标类型"
    )
    
    # 采集器配置
    collector: Optional[Dict[str, Any]] = Field(
        None,
        description="采集器配置（plugin, entry, params等）"
    )
    
    # 质量规则配置
    quality_rules: Optional[Dict[str, Any]] = Field(
        None,
        description="质量规则配置（completeness, freshness, connectivity等）"
    )
    
    # 元信息
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    created_by: Optional[str] = Field(None, description="创建者")
    
    def get_full_type(self) -> str:
        """获取完整类型标识（包含版本）"""
        return f"{self.type}@{self.version}"
    
    def get_required_properties(self) -> List[str]:
        """获取必填属性列表"""
        required = []
        for prop_name, prop_config in self.properties.items():
            if prop_config.get("required", False):
                required.append(prop_name)
        return required
    
    def validate_property(self, prop_name: str, value: Any) -> Tuple[bool, Optional[str]]:
        """
        验证属性值
        
        Args:
            prop_name: 属性名
            value: 属性值
            
        Returns:
            (是否有效, 错误信息)
        """
        if prop_name not in self.properties:
            return True, None  # 未知属性允许通过（扩展属性）
        
        prop_config = self.properties[prop_name]
        prop_type = prop_config.get("type", "string")
        
        # 类型检查
        if prop_type == PropertyType.STRING.value:
            if not isinstance(value, str):
                return False, f"属性 {prop_name} 必须是字符串类型"
        elif prop_type == PropertyType.INTEGER.value:
            if not isinstance(value, int):
                return False, f"属性 {prop_name} 必须是整数类型"
        elif prop_type == PropertyType.FLOAT.value:
            if not isinstance(value, (int, float)):
                return False, f"属性 {prop_name} 必须是数字类型"
        elif prop_type == PropertyType.BOOLEAN.value:
            if not isinstance(value, bool):
                return False, f"属性 {prop_name} 必须是布尔类型"
        elif prop_type == PropertyType.ENUM.value:
            allowed_values = prop_config.get("values", [])
            if value not in allowed_values:
                return False, f"属性 {prop_name} 的值必须在 {allowed_values} 中"
        
        # 必填检查
        if prop_config.get("required", False) and value is None:
            return False, f"属性 {prop_name} 是必填的"
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type,
            "version": self.version,
            "full_type": self.get_full_type(),
            "label": self.label,
            "description": self.description,
            "properties": self.properties,
            "relationships": self.relationships,
            "collector": self.collector,
            "quality_rules": self.quality_rules,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by
        }


class RelationshipMetaModel(BaseModel):
    """关系元模型"""
    type: str = Field(..., description="关系类型标识符（唯一）")
    version: str = Field(default="v1", description="版本号")
    label: str = Field(..., description="显示标签")
    description: Optional[str] = Field(None, description="描述")
    
    # 源和目标类型约束
    source_types: List[str] = Field(
        default_factory=list,
        description="允许的源实体类型列表（空列表表示允许所有类型）"
    )
    target_types: List[str] = Field(
        default_factory=list,
        description="允许的目标实体类型列表（空列表表示允许所有类型）"
    )
    
    # 关系属性定义
    properties: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="关系属性定义"
    )
    
    # 是否可推理/派生
    inferable: bool = Field(default=False, description="是否可以通过推理生成")
    derivable: bool = Field(default=False, description="是否可以从其他关系派生")
    
    # 元信息
    enabled: bool = Field(default=True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    created_by: Optional[str] = Field(None, description="创建者")
    
    def get_full_type(self) -> str:
        """获取完整类型标识（包含版本）"""
        return f"{self.type}@{self.version}"
    
    def validate_relationship(self, source_type: str, target_type: str) -> Tuple[bool, Optional[str]]:
        """
        验证关系是否有效
        
        Args:
            source_type: 源实体类型
            target_type: 目标实体类型
            
        Returns:
            (是否有效, 错误信息)
        """
        if self.source_types and source_type not in self.source_types:
            return False, f"源类型 {source_type} 不在允许的类型列表中: {self.source_types}"
        
        if self.target_types and target_type not in self.target_types:
            return False, f"目标类型 {target_type} 不在允许的类型列表中: {self.target_types}"
        
        return True, None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "type": self.type,
            "version": self.version,
            "full_type": self.get_full_type(),
            "label": self.label,
            "description": self.description,
            "source_types": self.source_types,
            "target_types": self.target_types,
            "properties": self.properties,
            "inferable": self.inferable,
            "derivable": self.derivable,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by
        }


class MetaModelPackage(BaseModel):
    """元模型包（用于上传和部署）"""
    entity_models: List[EntityMetaModel] = Field(default_factory=list, description="实体元模型列表")
    relationship_models: List[RelationshipMetaModel] = Field(default_factory=list, description="关系元模型列表")
    plugins: Dict[str, str] = Field(default_factory=dict, description="插件代码，key为文件名，value为代码内容")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="包元信息")
    collector_type: Optional[str] = Field(None, description="采集器类型标识符（用于创建采集任务时选择）")
    config_schema: Optional[List[Dict[str, Any]]] = Field(None, description="配置schema（用于生成采集任务配置界面）")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "entity_models": [m.to_dict() for m in self.entity_models],
            "relationship_models": [m.to_dict() for m in self.relationship_models],
            "plugins": self.plugins,
            "metadata": self.metadata,
            "collector_type": self.collector_type
        }
        if self.config_schema:
            result["config_schema"] = self.config_schema
        return result

