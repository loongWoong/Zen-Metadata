"""
元数据核心数据模型
"""
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class MetadataType(str, Enum):
    """元数据类型枚举"""
    DATABASE = "database"
    TABLE = "table"
    COLUMN = "column"
    FUNCTION = "function"
    CLASS = "class"
    FILE = "file"
    DIRECTORY = "directory"
    PACKAGE = "package"
    MODULE = "module"
    RELATIONSHIP = "relationship"
    SCHEMA = "schema"
    INDEX = "index"
    CONSTRAINT = "constraint"


class RelationshipType(str, Enum):
    """关系类型枚举"""
    CONTAINS = "contains"
    DEPENDS_ON = "depends_on"
    REFERENCES = "references"
    IMPLEMENTS = "implements"
    INHERITS = "inherits"
    CALLS = "calls"
    IMPORTS = "imports"
    USES = "uses"
    BELONGS_TO = "belongs_to"
    RELATED_TO = "related_to"


class MetadataEntity(BaseModel):
    """元数据实体基类"""
    id: str = Field(..., description="唯一标识符")
    type: Union[MetadataType, str] = Field(..., description="元数据类型（枚举或字符串）")
    name: str = Field(..., description="名称")
    description: Optional[str] = Field(None, description="描述")
    properties: Dict[str, Any] = Field(default_factory=dict, description="扩展属性")
    source: str = Field(..., description="数据源")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    
    @field_validator('type', mode='before')
    @classmethod
    def validate_type(cls, v):
        """验证类型字段，支持枚举和字符串"""
        if isinstance(v, MetadataType):
            return v.value
        if isinstance(v, str):
            # 尝试从字符串值匹配枚举
            try:
                return MetadataType(v).value
            except ValueError:
                # 如果不是标准枚举值，直接返回字符串（支持元模型自定义类型）
                return v
        return v
    
    class Config:
        use_enum_values = True


class MetadataRelationship(BaseModel):
    """元数据关系"""
    source_id: str = Field(..., description="源实体ID")
    target_id: str = Field(..., description="目标实体ID")
    type: Union[RelationshipType, str] = Field(..., description="关系类型（枚举或字符串）")
    properties: Dict[str, Any] = Field(default_factory=dict, description="关系属性")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    @field_validator('type', mode='before')
    @classmethod
    def validate_type(cls, v):
        """验证类型字段，支持枚举和字符串"""
        if isinstance(v, RelationshipType):
            return v.value
        if isinstance(v, str):
            # 尝试从字符串值匹配枚举
            try:
                return RelationshipType(v).value
            except ValueError:
                # 如果不是标准枚举值，直接返回字符串（支持元模型自定义类型）
                return v
        return v
    
    class Config:
        use_enum_values = True


class CollectionResult(BaseModel):
    """采集结果"""
    entities: List[MetadataEntity] = Field(default_factory=list, description="采集的实体")
    relationships: List[MetadataRelationship] = Field(default_factory=list, description="采集的关系")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="采集元信息")
    errors: List[str] = Field(default_factory=list, description="错误信息")


class QueryResult(BaseModel):
    """查询结果"""
    nodes: List[Dict[str, Any]] = Field(default_factory=list, description="节点")
    edges: List[Dict[str, Any]] = Field(default_factory=list, description="边")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="统计信息")





