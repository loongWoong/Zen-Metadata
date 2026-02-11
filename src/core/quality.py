"""
元数据质量评分系统
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from dataclasses import dataclass


class QualityDimension(str, Enum):
    """质量维度枚举"""
    COMPLETENESS = "completeness"  # 完整性
    ACCURACY = "accuracy"  # 准确性
    CONSISTENCY = "consistency"  # 一致性
    FRESHNESS = "freshness"  # 新鲜度


class QualityLevel(str, Enum):
    """质量等级"""
    EXCELLENT = "excellent"  # 优秀 (0.9-1.0)
    GOOD = "good"  # 良好 (0.7-0.9)
    FAIR = "fair"  # 一般 (0.5-0.7)
    POOR = "poor"  # 较差 (0.3-0.5)
    CRITICAL = "critical"  # 严重 (0.0-0.3)


class MetadataQualityScore(BaseModel):
    """元数据质量评分"""
    entity_id: str = Field(..., description="实体ID")
    entity_type: str = Field(..., description="实体类型")
    completeness_score: float = Field(0.0, ge=0.0, le=1.0, description="完整性评分（0-1）")
    accuracy_score: float = Field(0.0, ge=0.0, le=1.0, description="准确性评分（0-1）")
    consistency_score: float = Field(0.0, ge=0.0, le=1.0, description="一致性评分（0-1）")
    freshness_score: float = Field(0.0, ge=0.0, le=1.0, description="新鲜度评分（0-1）")
    overall_score: float = Field(0.0, ge=0.0, le=1.0, description="综合评分（0-1）")
    
    # 评分详情
    completeness_details: Dict[str, Any] = Field(default_factory=dict, description="完整性评分详情")
    accuracy_details: Dict[str, Any] = Field(default_factory=dict, description="准确性评分详情")
    consistency_details: Dict[str, Any] = Field(default_factory=dict, description="一致性评分详情")
    freshness_details: Dict[str, Any] = Field(default_factory=dict, description="新鲜度评分详情")
    
    # 元信息
    assessed_at: datetime = Field(default_factory=datetime.now, description="评估时间")
    assessed_by: str = Field(default="quality_assessor", description="评估器名称")
    version: int = Field(default=1, description="评分版本")
    
    def get_quality_level(self) -> QualityLevel:
        """获取质量等级"""
        score = self.overall_score
        if score >= 0.9:
            return QualityLevel.EXCELLENT
        elif score >= 0.7:
            return QualityLevel.GOOD
        elif score >= 0.5:
            return QualityLevel.FAIR
        elif score >= 0.3:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL
    
    def get_dimension_score(self, dimension: QualityDimension) -> float:
        """获取指定维度的评分"""
        if dimension == QualityDimension.COMPLETENESS:
            return self.completeness_score
        elif dimension == QualityDimension.ACCURACY:
            return self.accuracy_score
        elif dimension == QualityDimension.CONSISTENCY:
            return self.consistency_score
        elif dimension == QualityDimension.FRESHNESS:
            return self.freshness_score
        else:
            return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "completeness_score": self.completeness_score,
            "accuracy_score": self.accuracy_score,
            "consistency_score": self.consistency_score,
            "freshness_score": self.freshness_score,
            "overall_score": self.overall_score,
            "quality_level": self.get_quality_level().value,
            "completeness_details": self.completeness_details,
            "accuracy_details": self.accuracy_details,
            "consistency_details": self.consistency_details,
            "freshness_details": self.freshness_details,
            "assessed_at": self.assessed_at.isoformat(),
            "assessed_by": self.assessed_by,
            "version": self.version
        }


class QualityIssue(BaseModel):
    """质量问题"""
    entity_id: str = Field(..., description="实体ID")
    dimension: QualityDimension = Field(..., description="质量维度")
    severity: str = Field(..., description="严重程度: critical, high, medium, low")
    rule_name: str = Field(..., description="触发的规则名称")
    message: str = Field(..., description="问题描述")
    details: Dict[str, Any] = Field(default_factory=dict, description="问题详情")
    detected_at: datetime = Field(default_factory=datetime.now, description="检测时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entity_id": self.entity_id,
            "dimension": self.dimension.value,
            "severity": self.severity,
            "rule_name": self.rule_name,
            "message": self.message,
            "details": self.details,
            "detected_at": self.detected_at.isoformat()
        }


class QualityMetrics(BaseModel):
    """质量指标统计"""
    total_entities: int = Field(0, description="总实体数")
    assessed_entities: int = Field(0, description="已评估实体数")
    average_completeness: float = Field(0.0, ge=0.0, le=1.0, description="平均完整性评分")
    average_accuracy: float = Field(0.0, ge=0.0, le=1.0, description="平均准确性评分")
    average_consistency: float = Field(0.0, ge=0.0, le=1.0, description="平均一致性评分")
    average_freshness: float = Field(0.0, ge=0.0, le=1.0, description="平均新鲜度评分")
    average_overall: float = Field(0.0, ge=0.0, le=1.0, description="平均综合评分")
    
    # 质量等级分布
    excellent_count: int = Field(0, description="优秀数量")
    good_count: int = Field(0, description="良好数量")
    fair_count: int = Field(0, description="一般数量")
    poor_count: int = Field(0, description="较差数量")
    critical_count: int = Field(0, description="严重数量")
    
    # 问题统计
    total_issues: int = Field(0, description="总问题数")
    critical_issues: int = Field(0, description="严重问题数")
    high_issues: int = Field(0, description="高优先级问题数")
    medium_issues: int = Field(0, description="中优先级问题数")
    low_issues: int = Field(0, description="低优先级问题数")
    
    calculated_at: datetime = Field(default_factory=datetime.now, description="计算时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_entities": self.total_entities,
            "assessed_entities": self.assessed_entities,
            "average_completeness": self.average_completeness,
            "average_accuracy": self.average_accuracy,
            "average_consistency": self.average_consistency,
            "average_freshness": self.average_freshness,
            "average_overall": self.average_overall,
            "excellent_count": self.excellent_count,
            "good_count": self.good_count,
            "fair_count": self.fair_count,
            "poor_count": self.poor_count,
            "critical_count": self.critical_count,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "high_issues": self.high_issues,
            "medium_issues": self.medium_issues,
            "low_issues": self.low_issues,
            "calculated_at": self.calculated_at.isoformat()
        }



