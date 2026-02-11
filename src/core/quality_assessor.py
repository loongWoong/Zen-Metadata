"""
质量评估器
"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from .models import MetadataEntity, MetadataRelationship
from .quality import (
    MetadataQualityScore, QualityIssue, QualityMetrics, 
    QualityDimension, QualityLevel
)
from .quality_rules import QualityRuleEngine, RuleSeverity, RequiredFieldRule, FreshnessRule, RelationshipConsistencyRule
from .graph import GraphStore
from .metamodel_registry import MetaRegistry


class QualityAssessor:
    """质量评估器"""
    
    def __init__(self, rule_engine: QualityRuleEngine, 
                 graph_store: Optional[GraphStore] = None,
                 meta_registry: Optional[MetaRegistry] = None):
        """
        初始化质量评估器
        
        Args:
            rule_engine: 规则引擎
            graph_store: 图数据库存储（用于获取关系信息）
            meta_registry: 元模型注册表（用于获取类型特定的质量规则）
        """
        self.rule_engine = rule_engine
        self.graph_store = graph_store
        self.meta_registry = meta_registry
        
        # 评分权重配置
        self.weights = {
            QualityDimension.COMPLETENESS: 0.3,
            QualityDimension.ACCURACY: 0.3,
            QualityDimension.CONSISTENCY: 0.2,
            QualityDimension.FRESHNESS: 0.2
        }
    
    def assess_entity(self, entity: MetadataEntity, 
                     relationships: Optional[List[MetadataRelationship]] = None) -> MetadataQualityScore:
        """
        评估单个实体的质量
        
        Args:
            entity: 元数据实体
            relationships: 实体关系列表（可选，如果不提供且 graph_store 可用，会尝试从图数据库获取）
            
        Returns:
            质量评分
        """
        # 获取关系信息
        if relationships is None and self.graph_store:
            try:
                result = self.graph_store.get_entity_relationships(entity.id)
                relationships = []
                if result and result.edges:
                    # 从 QueryResult 的 edges 中提取关系
                    for edge in result.edges:
                        # 尝试构建 MetadataRelationship 对象
                        try:
                            from .models import MetadataRelationship, RelationshipType
                            rel = MetadataRelationship(
                                source_id=edge.get("source", edge.get("source_id", "")),
                                target_id=edge.get("target", edge.get("target_id", "")),
                                type=RelationshipType(edge.get("type", edge.get("relationship_type", "related_to"))),
                                properties=edge.get("properties", {})
                            )
                            relationships.append(rel)
                        except Exception as e:
                            # 如果无法构建，至少保留原始边数据
                            pass
            except Exception as e:
                print(f"获取实体关系失败: {e}")
                relationships = []
        
        # 构建评估上下文
        context = {
            "relationships": relationships or [],
            "graph_store": self.graph_store
        }
        
        # 如果存在元模型注册表，加载类型特定的质量规则
        if self.meta_registry:
            entity_model = self.meta_registry.get_entity_model(entity.type)
            if entity_model and entity_model.quality_rules:
                # 根据元模型的质量规则动态添加规则
                self._load_metamodel_rules(entity_model, entity.type)
        
        # 使用规则引擎评估
        issues = self.rule_engine.evaluate_entity(entity, context)
        
        # 按维度分组问题
        issues_by_dimension = {
            QualityDimension.COMPLETENESS: [],
            QualityDimension.ACCURACY: [],
            QualityDimension.CONSISTENCY: [],
            QualityDimension.FRESHNESS: []
        }
        
        for issue in issues:
            issues_by_dimension[issue.dimension].append(issue)
        
        # 计算各维度评分
        completeness_score, completeness_details = self._calculate_completeness_score(entity, issues_by_dimension[QualityDimension.COMPLETENESS])
        accuracy_score, accuracy_details = self._calculate_accuracy_score(entity, issues_by_dimension[QualityDimension.ACCURACY])
        consistency_score, consistency_details = self._calculate_consistency_score(entity, issues_by_dimension[QualityDimension.CONSISTENCY], relationships)
        freshness_score, freshness_details = self._calculate_freshness_score(entity, issues_by_dimension[QualityDimension.FRESHNESS])
        
        # 计算综合评分
        overall_score = (
            completeness_score * self.weights[QualityDimension.COMPLETENESS] +
            accuracy_score * self.weights[QualityDimension.ACCURACY] +
            consistency_score * self.weights[QualityDimension.CONSISTENCY] +
            freshness_score * self.weights[QualityDimension.FRESHNESS]
        )
        
        return MetadataQualityScore(
            entity_id=entity.id,
            entity_type=entity.type,
            completeness_score=completeness_score,
            accuracy_score=accuracy_score,
            consistency_score=consistency_score,
            freshness_score=freshness_score,
            overall_score=overall_score,
            completeness_details=completeness_details,
            accuracy_details=accuracy_details,
            consistency_details=consistency_details,
            freshness_details=freshness_details
        )
    
    def _calculate_completeness_score(self, entity: MetadataEntity, issues: List[QualityIssue]) -> Tuple[float, Dict[str, Any]]:
        """计算完整性评分"""
        # 定义必填字段
        required_fields = ["name", "type", "source"]
        
        # 检查必填字段
        filled_count = 0
        missing_fields = []
        
        for field in required_fields:
            value = None
            if hasattr(entity, field):
                value = getattr(entity, field)
            elif field in entity.properties:
                value = entity.properties[field]
            
            if value is not None and (not isinstance(value, str) or value.strip()):
                filled_count += 1
            else:
                missing_fields.append(field)
        
        # 检查描述字段（可选但重要）
        has_description = entity.description is not None and entity.description.strip() != ""
        
        # 基础完整性评分
        base_score = filled_count / len(required_fields) if required_fields else 1.0
        
        # 描述字段加分（最多加 0.1）
        description_bonus = 0.1 if has_description else 0.0
        
        # 根据问题扣分
        issue_penalty = 0.0
        for issue in issues:
            if issue.severity == RuleSeverity.CRITICAL.value:
                issue_penalty += 0.2
            elif issue.severity == RuleSeverity.HIGH.value:
                issue_penalty += 0.1
            elif issue.severity == RuleSeverity.MEDIUM.value:
                issue_penalty += 0.05
        
        score = min(1.0, max(0.0, base_score + description_bonus - issue_penalty))
        
        details = {
            "required_fields": required_fields,
            "filled_count": filled_count,
            "missing_fields": missing_fields,
            "has_description": has_description,
            "issue_count": len(issues),
            "issue_penalty": issue_penalty
        }
        
        return score, details
    
    def _calculate_accuracy_score(self, entity: MetadataEntity, issues: List[QualityIssue]) -> Tuple[float, Dict[str, Any]]:
        """计算准确性评分"""
        # 基础准确性评分（假设数据准确）
        base_score = 1.0
        
        # 根据问题扣分
        issue_penalty = 0.0
        for issue in issues:
            if issue.severity == RuleSeverity.CRITICAL.value:
                issue_penalty += 0.3
            elif issue.severity == RuleSeverity.HIGH.value:
                issue_penalty += 0.15
            elif issue.severity == RuleSeverity.MEDIUM.value:
                issue_penalty += 0.08
            elif issue.severity == RuleSeverity.LOW.value:
                issue_penalty += 0.03
        
        score = min(1.0, max(0.0, base_score - issue_penalty))
        
        details = {
            "issue_count": len(issues),
            "issue_penalty": issue_penalty,
            "issues": [issue.to_dict() for issue in issues]
        }
        
        return score, details
    
    def _calculate_consistency_score(self, entity: MetadataEntity, 
                                    issues: List[QualityIssue],
                                    relationships: Optional[List[MetadataRelationship]]) -> Tuple[float, Dict[str, Any]]:
        """计算一致性评分"""
        # 基础一致性评分
        base_score = 1.0
        
        # 检查关系一致性
        relationship_issues = [issue for issue in issues if "relationship" in issue.rule_name.lower()]
        
        # 根据问题扣分
        issue_penalty = 0.0
        for issue in issues:
            if issue.severity == RuleSeverity.CRITICAL.value:
                issue_penalty += 0.25
            elif issue.severity == RuleSeverity.HIGH.value:
                issue_penalty += 0.12
            elif issue.severity == RuleSeverity.MEDIUM.value:
                issue_penalty += 0.06
        
        # 关系数量合理性检查
        relationship_bonus = 0.0
        if relationships:
            # 如果有关系，给予小幅加分
            if len(relationships) > 0:
                relationship_bonus = min(0.1, len(relationships) * 0.01)
        
        score = min(1.0, max(0.0, base_score - issue_penalty + relationship_bonus))
        
        details = {
            "issue_count": len(issues),
            "relationship_issue_count": len(relationship_issues),
            "relationship_count": len(relationships) if relationships else 0,
            "issue_penalty": issue_penalty,
            "relationship_bonus": relationship_bonus
        }
        
        return score, details
    
    def _calculate_freshness_score(self, entity: MetadataEntity, issues: List[QualityIssue]) -> Tuple[float, Dict[str, Any]]:
        """计算新鲜度评分"""
        updated_at = entity.updated_at
        if updated_at is None:
            updated_at = entity.created_at
        
        if updated_at is None:
            return 0.0, {"error": "缺少时间戳信息"}
        
        # 计算数据年龄（天数）
        age_days = (datetime.now() - updated_at).days
        
        # 新鲜度评分：越新分数越高
        # 使用指数衰减函数：score = e^(-age/90)
        import math
        if age_days <= 0:
            freshness_score = 1.0
        else:
            # 90天为半衰期
            freshness_score = math.exp(-age_days / 90.0)
        
        # 根据问题扣分
        issue_penalty = 0.0
        for issue in issues:
            if issue.severity == RuleSeverity.CRITICAL.value:
                issue_penalty += 0.3
            elif issue.severity == RuleSeverity.HIGH.value:
                issue_penalty += 0.15
            elif issue.severity == RuleSeverity.MEDIUM.value:
                issue_penalty += 0.08
        
        score = min(1.0, max(0.0, freshness_score - issue_penalty))
        
        details = {
            "age_days": age_days,
            "updated_at": updated_at.isoformat(),
            "base_freshness_score": freshness_score,
            "issue_count": len(issues),
            "issue_penalty": issue_penalty
        }
        
        return score, details
    
    def assess_batch(self, entities: List[MetadataEntity]) -> List[MetadataQualityScore]:
        """
        批量评估实体
        
        Args:
            entities: 实体列表
            
        Returns:
            质量评分列表
        """
        scores = []
        for entity in entities:
            try:
                score = self.assess_entity(entity)
                scores.append(score)
            except Exception as e:
                print(f"评估实体 {entity.id} 失败: {e}")
        return scores
    
    def calculate_metrics(self, scores: List[MetadataQualityScore]) -> QualityMetrics:
        """
        计算质量指标
        
        Args:
            scores: 质量评分列表
            
        Returns:
            质量指标
        """
        if not scores:
            return QualityMetrics()
        
        total = len(scores)
        
        # 计算平均分
        avg_completeness = sum(s.completeness_score for s in scores) / total
        avg_accuracy = sum(s.accuracy_score for s in scores) / total
        avg_consistency = sum(s.consistency_score for s in scores) / total
        avg_freshness = sum(s.freshness_score for s in scores) / total
        avg_overall = sum(s.overall_score for s in scores) / total
        
        # 统计质量等级分布
        excellent_count = sum(1 for s in scores if s.get_quality_level() == QualityLevel.EXCELLENT)
        good_count = sum(1 for s in scores if s.get_quality_level() == QualityLevel.GOOD)
        fair_count = sum(1 for s in scores if s.get_quality_level() == QualityLevel.FAIR)
        poor_count = sum(1 for s in scores if s.get_quality_level() == QualityLevel.POOR)
        critical_count = sum(1 for s in scores if s.get_quality_level() == QualityLevel.CRITICAL)
        
        # 统计问题（需要从评估过程中获取，这里简化处理）
        # 实际实现中可以从规则引擎获取问题统计
        
        return QualityMetrics(
            total_entities=total,
            assessed_entities=total,
            average_completeness=avg_completeness,
            average_accuracy=avg_accuracy,
            average_consistency=avg_consistency,
            average_freshness=avg_freshness,
            average_overall=avg_overall,
            excellent_count=excellent_count,
            good_count=good_count,
            fair_count=fair_count,
            poor_count=poor_count,
            critical_count=critical_count
        )
    
    def _load_metamodel_rules(self, entity_model, entity_type: str):
        """
        从元模型加载质量规则
        
        Args:
            entity_model: 实体元模型
            entity_type: 实体类型
        """
        if not entity_model or not entity_model.quality_rules:
            return
        
        quality_rules = entity_model.quality_rules
        
        # 处理完整性规则
        if 'completeness' in quality_rules:
            completeness_rules = quality_rules['completeness']
            required_properties = completeness_rules.get('required_properties', [])
            for prop_name in required_properties:
                # 检查规则是否已存在（避免重复添加）
                rule_name = f"{entity_type}_required_{prop_name}"
                existing_rule = self.rule_engine.get_rule(rule_name)
                if not existing_rule:
                    rule = RequiredFieldRule(
                        field_name=prop_name,
                        severity=RuleSeverity.MEDIUM,
                        enabled=True,
                        description=f"元模型要求 {entity_type} 必须包含字段 {prop_name}"
                    )
                    rule.name = rule_name  # 设置唯一名称
                    self.rule_engine.add_rule(rule)
        
        # 处理新鲜度规则
        if 'freshness' in quality_rules:
            freshness_rules = quality_rules['freshness']
            ttl_days = freshness_rules.get('ttl_days')
            if ttl_days:
                rule_name = f"{entity_type}_freshness_{ttl_days}days"
                existing_rule = self.rule_engine.get_rule(rule_name)
                if not existing_rule:
                    rule = FreshnessRule(
                        max_age_days=ttl_days,
                        severity=RuleSeverity.LOW,
                        enabled=True,
                        description=f"元模型要求 {entity_type} 数据应在 {ttl_days} 天内更新"
                    )
                    rule.name = rule_name  # 设置唯一名称
                    self.rule_engine.add_rule(rule)
        
        # 处理连通性规则（关系规则）
        # 注意：连通性规则需要检查关系数量，这在实际评估时通过上下文中的关系列表来检查
        # 这里暂时跳过，因为 RelationshipConsistencyRule 需要特定的关系类型
        # 如果需要实现，可以创建一个自定义规则来检查最小关系数量
        if 'connectivity' in quality_rules:
            # 连通性规则会在评估时通过关系数量来间接体现
            # 可以通过一致性评分中的 relationship_bonus 来反映
            pass
    
    def set_weights(self, weights: Dict[QualityDimension, float]):
        """
        设置评分权重
        
        Args:
            weights: 权重字典
        """
        # 归一化权重
        total = sum(weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in weights.items()}
        else:
            self.weights = weights

