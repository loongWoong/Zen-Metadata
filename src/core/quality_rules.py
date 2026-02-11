"""
质量规则引擎
"""
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from enum import Enum
from datetime import datetime, timedelta
import re
import json
from .models import MetadataEntity, MetadataRelationship
from .quality import QualityDimension, QualityIssue


class RuleSeverity(str, Enum):
    """规则严重程度"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QualityRule(ABC):
    """质量规则基类"""
    
    def __init__(self, 
                 name: str,
                 dimension: QualityDimension,
                 severity: RuleSeverity = RuleSeverity.MEDIUM,
                 enabled: bool = True,
                 description: str = ""):
        """
        初始化质量规则
        
        Args:
            name: 规则名称
            dimension: 质量维度
            severity: 严重程度
            enabled: 是否启用
            description: 规则描述
        """
        self.name = name
        self.dimension = dimension
        self.severity = severity
        self.enabled = enabled
        self.description = description
    
    @abstractmethod
    def evaluate(self, entity: MetadataEntity, context: Dict[str, Any] = None) -> Optional[QualityIssue]:
        """
        评估实体是否符合规则
        
        Args:
            entity: 元数据实体
            context: 评估上下文（可包含关系、图数据库连接等）
            
        Returns:
            如果违反规则，返回 QualityIssue；否则返回 None
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "dimension": self.dimension.value,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "description": self.description
        }


class RequiredFieldRule(QualityRule):
    """必填字段规则"""
    
    def __init__(self, 
                 field_name: str,
                 severity: RuleSeverity = RuleSeverity.HIGH,
                 **kwargs):
        """
        初始化必填字段规则
        
        Args:
            field_name: 字段名称
            severity: 严重程度
        """
        # 优先使用配置中的description，否则使用默认描述
        description = kwargs.pop('description', f"检查字段 {field_name} 是否为必填")
        super().__init__(
            name=f"required_field_{field_name}",
            dimension=QualityDimension.COMPLETENESS,
            severity=severity,
            description=description,
            **kwargs
        )
        self.field_name = field_name
    
    def evaluate(self, entity: MetadataEntity, context: Dict[str, Any] = None) -> Optional[QualityIssue]:
        """评估必填字段"""
        if not self.enabled:
            return None
        
        # 检查实体属性中是否存在该字段
        value = None
        if hasattr(entity, self.field_name):
            value = getattr(entity, self.field_name)
        elif self.field_name in entity.properties:
            value = entity.properties[self.field_name]
        
        if value is None or (isinstance(value, str) and not value.strip()):
            return QualityIssue(
                entity_id=entity.id,
                dimension=self.dimension,
                severity=self.severity.value,
                rule_name=self.name,
                message=f"必填字段 {self.field_name} 缺失或为空",
                details={"field_name": self.field_name, "entity_type": entity.type}
            )
        return None


class FieldFormatRule(QualityRule):
    """字段格式验证规则"""
    
    def __init__(self,
                 field_name: str,
                 pattern: str,
                 severity: RuleSeverity = RuleSeverity.MEDIUM,
                 **kwargs):
        """
        初始化字段格式规则
        
        Args:
            field_name: 字段名称
            pattern: 正则表达式模式
            severity: 严重程度
        """
        # 优先使用配置中的description，否则使用默认描述
        description = kwargs.pop('description', f"验证字段 {field_name} 的格式")
        super().__init__(
            name=f"format_{field_name}",
            dimension=QualityDimension.ACCURACY,
            severity=severity,
            description=description,
            **kwargs
        )
        self.field_name = field_name
        self.pattern = re.compile(pattern)
    
    def evaluate(self, entity: MetadataEntity, context: Dict[str, Any] = None) -> Optional[QualityIssue]:
        """评估字段格式"""
        if not self.enabled:
            return None
        
        value = None
        if hasattr(entity, self.field_name):
            value = getattr(entity, self.field_name)
        elif self.field_name in entity.properties:
            value = entity.properties[self.field_name]
        
        if value is None:
            return None  # 空值由必填字段规则处理
        
        if not isinstance(value, str):
            value = str(value)
        
        if not self.pattern.match(value):
            return QualityIssue(
                entity_id=entity.id,
                dimension=self.dimension,
                severity=self.severity.value,
                rule_name=self.name,
                message=f"字段 {self.field_name} 的格式不符合要求",
                details={
                    "field_name": self.field_name,
                    "value": value,
                    "pattern": self.pattern.pattern,
                    "entity_type": entity.type
                }
            )
        return None


class FieldValueRangeRule(QualityRule):
    """字段值域规则"""
    
    def __init__(self,
                 field_name: str,
                 min_value: Optional[float] = None,
                 max_value: Optional[float] = None,
                 allowed_values: Optional[List[Any]] = None,
                 severity: RuleSeverity = RuleSeverity.MEDIUM,
                 **kwargs):
        """
        初始化字段值域规则
        
        Args:
            field_name: 字段名称
            min_value: 最小值
            max_value: 最大值
            allowed_values: 允许的值列表
            severity: 严重程度
        """
        # 优先使用配置中的description，否则使用默认描述
        description = kwargs.pop('description', f"验证字段 {field_name} 的值域")
        super().__init__(
            name=f"value_range_{field_name}",
            dimension=QualityDimension.ACCURACY,
            severity=severity,
            description=description,
            **kwargs
        )
        self.field_name = field_name
        self.min_value = min_value
        self.max_value = max_value
        self.allowed_values = allowed_values
    
    def evaluate(self, entity: MetadataEntity, context: Dict[str, Any] = None) -> Optional[QualityIssue]:
        """评估字段值域"""
        if not self.enabled:
            return None
        
        value = None
        if hasattr(entity, self.field_name):
            value = getattr(entity, self.field_name)
        elif self.field_name in entity.properties:
            value = entity.properties[self.field_name]
        
        if value is None:
            return None
        
        # 检查允许的值列表
        if self.allowed_values is not None and value not in self.allowed_values:
            return QualityIssue(
                entity_id=entity.id,
                dimension=self.dimension,
                severity=self.severity.value,
                rule_name=self.name,
                message=f"字段 {self.field_name} 的值不在允许的范围内",
                details={
                    "field_name": self.field_name,
                    "value": value,
                    "allowed_values": self.allowed_values,
                    "entity_type": entity.type
                }
            )
        
        # 检查数值范围
        try:
            num_value = float(value)
            if self.min_value is not None and num_value < self.min_value:
                return QualityIssue(
                    entity_id=entity.id,
                    dimension=self.dimension,
                    severity=self.severity.value,
                    rule_name=self.name,
                    message=f"字段 {self.field_name} 的值小于最小值 {self.min_value}",
                    details={
                        "field_name": self.field_name,
                        "value": value,
                        "min_value": self.min_value,
                        "entity_type": entity.type
                    }
                )
            if self.max_value is not None and num_value > self.max_value:
                return QualityIssue(
                    entity_id=entity.id,
                    dimension=self.dimension,
                    severity=self.severity.value,
                    rule_name=self.name,
                    message=f"字段 {self.field_name} 的值大于最大值 {self.max_value}",
                    details={
                        "field_name": self.field_name,
                        "value": value,
                        "max_value": self.max_value,
                        "entity_type": entity.type
                    }
                )
        except (ValueError, TypeError):
            pass  # 非数值类型，跳过数值范围检查
        
        return None


class RelationshipConsistencyRule(QualityRule):
    """关系一致性规则"""
    
    def __init__(self,
                 relationship_type: str,
                 required: bool = False,
                 severity: RuleSeverity = RuleSeverity.MEDIUM,
                 **kwargs):
        """
        初始化关系一致性规则
        
        Args:
            relationship_type: 关系类型
            required: 是否必需
            severity: 严重程度
        """
        # 优先使用配置中的description，否则使用默认描述
        description = kwargs.pop('description', f"检查关系 {relationship_type} 的一致性")
        super().__init__(
            name=f"relationship_{relationship_type}",
            dimension=QualityDimension.CONSISTENCY,
            severity=severity,
            description=description,
            **kwargs
        )
        self.relationship_type = relationship_type
        self.required = required
    
    def evaluate(self, entity: MetadataEntity, context: Dict[str, Any] = None) -> Optional[QualityIssue]:
        """评估关系一致性"""
        if not self.enabled:
            return None
        
        if context is None:
            context = {}
        
        relationships = context.get("relationships", [])
        if not isinstance(relationships, list):
            relationships = []
        
        # 检查是否存在指定类型的关系
        has_relationship = any(
            rel.type == self.relationship_type or 
            (isinstance(rel, dict) and rel.get("type") == self.relationship_type)
            for rel in relationships
        )
        
        if self.required and not has_relationship:
            return QualityIssue(
                entity_id=entity.id,
                dimension=self.dimension,
                severity=self.severity.value,
                rule_name=self.name,
                message=f"实体缺少必需的关系 {self.relationship_type}",
                details={
                    "relationship_type": self.relationship_type,
                    "entity_type": entity.type,
                    "required": self.required
                }
            )
        
        return None


class FreshnessRule(QualityRule):
    """新鲜度规则"""
    
    def __init__(self,
                 max_age_days: int = 30,
                 severity: RuleSeverity = RuleSeverity.MEDIUM,
                 **kwargs):
        """
        初始化新鲜度规则
        
        Args:
            max_age_days: 最大年龄（天数）
            severity: 严重程度
        """
        # 优先使用配置中的description，否则使用默认描述
        description = kwargs.pop('description', f"检查数据新鲜度，最大年龄 {max_age_days} 天")
        super().__init__(
            name=f"freshness_max_{max_age_days}_days",
            dimension=QualityDimension.FRESHNESS,
            severity=severity,
            description=description,
            **kwargs
        )
        self.max_age_days = max_age_days
    
    def evaluate(self, entity: MetadataEntity, context: Dict[str, Any] = None) -> Optional[QualityIssue]:
        """评估新鲜度"""
        if not self.enabled:
            return None
        
        updated_at = entity.updated_at
        if updated_at is None:
            updated_at = entity.created_at
        
        if updated_at is None:
            return QualityIssue(
                entity_id=entity.id,
                dimension=self.dimension,
                severity=self.severity.value,
                rule_name=self.name,
                message="实体缺少更新时间信息",
                details={"entity_type": entity.type}
            )
        
        age_days = (datetime.now() - updated_at).days
        if age_days > self.max_age_days:
            return QualityIssue(
                entity_id=entity.id,
                dimension=self.dimension,
                severity=self.severity.value,
                rule_name=self.name,
                message=f"数据已过期，距离上次更新已 {age_days} 天（最大允许 {self.max_age_days} 天）",
                details={
                    "age_days": age_days,
                    "max_age_days": self.max_age_days,
                    "updated_at": updated_at.isoformat(),
                    "entity_type": entity.type
                }
            )
        
        return None


class CustomPythonRule(QualityRule):
    """自定义 Python 表达式规则"""
    
    def __init__(self,
                 name: str,
                 dimension: QualityDimension,
                 expression: str,
                 severity: RuleSeverity = RuleSeverity.MEDIUM,
                 **kwargs):
        """
        初始化自定义 Python 规则
        
        Args:
            name: 规则名称
            dimension: 质量维度
            expression: Python 表达式（返回 True 表示通过，False 或抛出异常表示失败）
            severity: 严重程度
        """
        # 优先使用配置中的description，否则使用默认描述
        description = kwargs.pop('description', f"自定义 Python 规则: {expression}")
        super().__init__(
            name=name,
            dimension=dimension,
            severity=severity,
            description=description,
            **kwargs
        )
        self.expression = expression
        self._compiled = None
    
    def evaluate(self, entity: MetadataEntity, context: Dict[str, Any] = None) -> Optional[QualityIssue]:
        """评估自定义规则"""
        if not self.enabled:
            return None
        
        try:
            # 构建评估环境
            eval_context = {
                "entity": entity,
                "context": context or {},
                "hasattr": hasattr,
                "getattr": getattr,
                "isinstance": isinstance,
                "len": len,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "datetime": datetime,
                "timedelta": timedelta,
            }
            
            # 执行表达式
            result = eval(self.expression, {"__builtins__": {}}, eval_context)
            
            if not result:
                return QualityIssue(
                    entity_id=entity.id,
                    dimension=self.dimension,
                    severity=self.severity.value,
                    rule_name=self.name,
                    message=f"自定义规则验证失败: {self.expression}",
                    details={
                        "expression": self.expression,
                        "entity_type": entity.type
                    }
                )
        except Exception as e:
            return QualityIssue(
                entity_id=entity.id,
                dimension=self.dimension,
                severity=self.severity.value,
                rule_name=self.name,
                message=f"自定义规则执行错误: {str(e)}",
                details={
                    "expression": self.expression,
                    "error": str(e),
                    "entity_type": entity.type
                }
            )
        
        return None


class QualityRuleEngine:
    """质量规则引擎"""
    
    def __init__(self):
        """初始化规则引擎"""
        self.rules: List[QualityRule] = []
        self._load_default_rules()
    
    def _load_default_rules(self):
        """加载默认规则"""
        # 默认必填字段规则
        self.add_rule(RequiredFieldRule("name", RuleSeverity.CRITICAL))
        self.add_rule(RequiredFieldRule("type", RuleSeverity.CRITICAL))
        self.add_rule(RequiredFieldRule("source", RuleSeverity.HIGH))
        
        # 默认新鲜度规则
        self.add_rule(FreshnessRule(max_age_days=90, severity=RuleSeverity.LOW))
    
    def add_rule(self, rule: QualityRule):
        """添加规则"""
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str):
        """移除规则"""
        self.rules = [r for r in self.rules if r.name != rule_name]
    
    def get_rule(self, rule_name: str) -> Optional[QualityRule]:
        """获取规则"""
        for rule in self.rules:
            if rule.name == rule_name:
                return rule
        return None
    
    def enable_rule(self, rule_name: str):
        """启用规则"""
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = True
    
    def disable_rule(self, rule_name: str):
        """禁用规则"""
        rule = self.get_rule(rule_name)
        if rule:
            rule.enabled = False
    
    def evaluate_entity(self, entity: MetadataEntity, context: Dict[str, Any] = None) -> List[QualityIssue]:
        """
        评估实体，返回所有违反的规则
        
        Args:
            entity: 元数据实体
            context: 评估上下文
            
        Returns:
            质量问题列表
        """
        issues = []
        for rule in self.rules:
            if rule.enabled:
                issue = rule.evaluate(entity, context)
                if issue:
                    issues.append(issue)
        return issues
    
    def load_rules_from_config(self, config: Dict[str, Any]):
        """
        从配置加载规则
        
        Args:
            config: 规则配置字典
        """
        rules_config = config.get("rules", [])
        
        for rule_config in rules_config:
            rule_type = rule_config.get("type")
            if not rule_type:
                continue
            
            try:
                rule = self._create_rule_from_config(rule_config)
                if rule:
                    self.add_rule(rule)
            except Exception as e:
                print(f"加载规则失败: {rule_config.get('name', 'unknown')}, 错误: {e}")
    
    def _create_rule_from_config(self, config: Dict[str, Any]) -> Optional[QualityRule]:
        """从配置创建规则"""
        rule_type = config.get("type")
        name = config.get("name", f"rule_{len(self.rules)}")
        dimension = QualityDimension(config.get("dimension", "completeness"))
        severity = RuleSeverity(config.get("severity", "medium"))
        enabled = config.get("enabled", True)
        
        if rule_type == "required_field":
            return RequiredFieldRule(
                field_name=config.get("field_name"),
                severity=severity,
                enabled=enabled,
                description=config.get("description", "")
            )
        elif rule_type == "format":
            return FieldFormatRule(
                field_name=config.get("field_name"),
                pattern=config.get("pattern"),
                severity=severity,
                enabled=enabled,
                description=config.get("description", "")
            )
        elif rule_type == "value_range":
            return FieldValueRangeRule(
                field_name=config.get("field_name"),
                min_value=config.get("min_value"),
                max_value=config.get("max_value"),
                allowed_values=config.get("allowed_values"),
                severity=severity,
                enabled=enabled,
                description=config.get("description", "")
            )
        elif rule_type == "relationship":
            return RelationshipConsistencyRule(
                relationship_type=config.get("relationship_type"),
                required=config.get("required", False),
                severity=severity,
                enabled=enabled,
                description=config.get("description", "")
            )
        elif rule_type == "freshness":
            return FreshnessRule(
                max_age_days=config.get("max_age_days", 30),
                severity=severity,
                enabled=enabled,
                description=config.get("description", "")
            )
        elif rule_type == "custom_python":
            return CustomPythonRule(
                name=name,
                dimension=dimension,
                expression=config.get("expression"),
                severity=severity,
                enabled=enabled,
                description=config.get("description", "")
            )
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rules": [rule.to_dict() for rule in self.rules],
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled])
        }

