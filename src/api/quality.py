"""
质量管理系统 API
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, model_validator
from datetime import datetime
import json
import traceback
from ..processing.sqlite import SQLiteProcessor

from ..core.quality import MetadataQualityScore, QualityIssue, QualityMetrics
from ..core.quality_rules import QualityRuleEngine
from ..core.quality_assessor import QualityAssessor
from ..core.quality_monitor import QualityMonitor, AlertChannel
from ..core.graph import GraphStore
from ..core.models import MetadataEntity


router = APIRouter(prefix="/api/quality", tags=["quality"])

# 全局实例（在启动时初始化）
rule_engine: Optional[QualityRuleEngine] = None
quality_assessor: Optional[QualityAssessor] = None
quality_monitor: Optional[QualityMonitor] = None
graph_store: Optional[GraphStore] = None
sqlite_processor: Optional[SQLiteProcessor] = None


def set_dependencies(gs: GraphStore, sqlite: Optional[SQLiteProcessor] = None):
    """设置依赖"""
    global graph_store, rule_engine, quality_assessor, quality_monitor, sqlite_processor
    
    graph_store = gs
    sqlite_processor = sqlite
    
    # 初始化规则引擎
    rule_engine = QualityRuleEngine()
    
    # 初始化质量评估器
    quality_assessor = QualityAssessor(rule_engine, graph_store)
    
    # 初始化质量监控器
    quality_monitor = QualityMonitor(quality_assessor)


# ========== 请求/响应模型 ==========

class AssessEntityRequest(BaseModel):
    """评估实体请求"""
    entity_id: str


class AssessBatchRequest(BaseModel):
    """批量评估请求"""
    entity_ids: Optional[List[str]] = None
    entity_type: Optional[str] = None
    source: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_request(self):
        """验证请求参数"""
        # 如果提供了entity_ids，确保不为空
        if self.entity_ids is not None:
            if len(self.entity_ids) == 0:
                raise ValueError("entity_ids不能为空列表")
        # 如果没有提供entity_ids，必须提供entity_type
        elif not self.entity_type:
            raise ValueError("必须提供entity_ids或entity_type")
        
        return self


class AddRuleRequest(BaseModel):
    """添加规则请求"""
    type: str  # required_field, format, value_range, relationship, freshness, custom_python
    name: Optional[str] = None
    dimension: str = "completeness"
    severity: str = "medium"
    enabled: bool = True
    description: Optional[str] = None
    # 规则特定参数
    field_name: Optional[str] = None
    pattern: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    relationship_type: Optional[str] = None
    required: Optional[bool] = None
    max_age_days: Optional[int] = None
    expression: Optional[str] = None


class AlertConfigRequest(BaseModel):
    """告警配置请求"""
    email: Optional[Dict[str, Any]] = None
    webhook: Optional[Dict[str, Any]] = None


# ========== 质量评估 API ==========

@router.post("/assess/entity", response_model=Dict[str, Any])
async def assess_entity(request: AssessEntityRequest):
    """评估单个实体的质量"""
    if not quality_assessor or not graph_store:
        raise HTTPException(status_code=500, detail="质量评估器未初始化")
    
    try:
        # 获取实体
        entity_result = graph_store.find_entity(request.entity_id)
        if not entity_result:
            raise HTTPException(status_code=404, detail=f"实体 {request.entity_id} 不存在")
        
        # 转换为 MetadataEntity
        # 处理图数据库返回的节点格式
        if isinstance(entity_result, dict):
            # 节点属性可能在 'properties' 键中，也可能直接在顶层
            props = entity_result.get('properties', entity_result)
            
            # 提取必填字段
            entity_id = props.get('id', request.entity_id)
            entity_type = props.get('type', 'unknown')
            entity_name = props.get('name', entity_id)  # 如果没有name，使用id作为默认值
            entity_source = props.get('source', 'unknown')
            
            # 提取可选字段
            description = props.get('description')
            
            # 处理日期字段
            created_at = props.get('created_at')
            updated_at = props.get('updated_at')
            
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = datetime.now()
            elif created_at is None:
                created_at = datetime.now()
            
            if isinstance(updated_at, str):
                try:
                    updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                except:
                    updated_at = datetime.now()
            elif updated_at is None:
                updated_at = datetime.now()
            
            # 提取扩展属性（排除已使用的字段）
            excluded_fields = {'id', 'type', 'name', 'description', 'source', 'created_at', 'updated_at', 'properties'}
            properties = {k: v for k, v in props.items() if k not in excluded_fields}
            
            entity = MetadataEntity(
                id=entity_id,
                type=entity_type,
                name=entity_name,
                description=description,
                properties=properties,
                source=entity_source,
                created_at=created_at,
                updated_at=updated_at
            )
        else:
            raise HTTPException(status_code=500, detail=f"无法解析实体数据: 期望字典格式，得到 {type(entity_result).__name__}")
        
        # 评估质量
        score = quality_assessor.assess_entity(entity)
        
        # 监控告警
        alerts = quality_monitor.monitor_entity(request.entity_id, score) if quality_monitor else []
        
        # 持久化评估结果
        if sqlite_processor:
            try:
                score_dict = score.to_dict()
                sqlite_processor.store_quality_score(score_dict)
            except Exception as e:
                print(f"保存评估结果失败: {e}")
        
        return {
            "score": score.to_dict(),
            "alerts": alerts
        }
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"评估失败: {str(e)}"
        # 只在调试模式下包含完整traceback
        import os
        if os.getenv('DEBUG', 'false').lower() == 'true':
            error_detail += f"\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/assess/batch", response_model=Dict[str, Any])
async def assess_batch(request: AssessBatchRequest):
    """批量评估实体质量"""
    if not quality_assessor or not graph_store:
        raise HTTPException(status_code=500, detail="质量评估器未初始化")
    
    try:
        scores = []
        alerts_summary = {}
        
        # 如果提供了实体ID列表，直接评估
        if request.entity_ids:
            if len(request.entity_ids) == 0:
                raise HTTPException(status_code=400, detail="entity_ids不能为空列表")
            
            not_found_entities = []
            for entity_id in request.entity_ids:
                try:
                    entity_result = graph_store.find_entity(entity_id)
                    if not entity_result:
                        not_found_entities.append(entity_id)
                        continue
                    
                    # 处理图数据库返回的节点格式
                    if isinstance(entity_result, dict):
                        # 节点属性可能在 'properties' 键中，也可能直接在顶层
                        props = entity_result.get('properties', entity_result)
                        
                        # 提取必填字段
                        entity_id_val = props.get('id', entity_id)
                        entity_type = props.get('type', 'unknown')
                        entity_name = props.get('name', entity_id_val)
                        entity_source = props.get('source', 'unknown')
                        
                        # 提取可选字段
                        description = props.get('description')
                        
                        # 处理日期字段
                        created_at = props.get('created_at')
                        updated_at = props.get('updated_at')
                        
                        if isinstance(created_at, str):
                            try:
                                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            except:
                                created_at = datetime.now()
                        elif created_at is None:
                            created_at = datetime.now()
                        
                        if isinstance(updated_at, str):
                            try:
                                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                            except:
                                updated_at = datetime.now()
                        elif updated_at is None:
                            updated_at = datetime.now()
                        
                        # 提取扩展属性（排除已使用的字段）
                        excluded_fields = {'id', 'type', 'name', 'description', 'source', 'created_at', 'updated_at', 'properties'}
                        properties = {k: v for k, v in props.items() if k not in excluded_fields}
                        
                        entity = MetadataEntity(
                            id=entity_id_val,
                            type=entity_type,
                            name=entity_name,
                            description=description,
                            properties=properties,
                            source=entity_source,
                            created_at=created_at,
                            updated_at=updated_at
                        )
                    else:
                        not_found_entities.append(entity_id)
                        continue
                    
                    score = quality_assessor.assess_entity(entity)
                    scores.append(score)
                    
                    # 监控告警
                    if quality_monitor:
                        entity_alerts = quality_monitor.monitor_entity(entity_id, score)
                        if entity_alerts:
                            alerts_summary[entity_id] = entity_alerts
                except Exception as e:
                    print(f"评估实体 {entity_id} 失败: {e}")
                    not_found_entities.append(entity_id)
                    continue
            
            # 如果所有实体都找不到，返回错误
            if len(scores) == 0 and len(not_found_entities) > 0:
                raise HTTPException(
                    status_code=404, 
                    detail=f"所有实体都不存在: {', '.join(not_found_entities[:5])}{'...' if len(not_found_entities) > 5 else ''}"
                )
        else:
            # 根据类型和来源查询实体
            
            if not sqlite_processor:
                raise HTTPException(status_code=500, detail="SQLite处理器未初始化，无法按类型查询实体")
            
            if not request.entity_type:
                raise HTTPException(status_code=400, detail="当未提供entity_ids时，必须提供entity_type")
            
            # 从SQLite查询实体
            entities_data = sqlite_processor.query_entities(
                entity_type=request.entity_type,
                source=request.source,
                limit=1000
            )
            
            # 转换为MetadataEntity并评估
            for entity_data in entities_data:
                try:
                    # 处理日期字段
                    created_at = entity_data.get('created_at')
                    updated_at = entity_data.get('updated_at')
                    if isinstance(created_at, str):
                        try:
                            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        except:
                            created_at = datetime.now()
                    else:
                        created_at = created_at or datetime.now()
                    
                    if isinstance(updated_at, str):
                        try:
                            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        except:
                            updated_at = datetime.now()
                    else:
                        updated_at = updated_at or datetime.now()
                    
                    # 处理properties字段（可能是JSON字符串）
                    properties = entity_data.get('properties', {})
                    if isinstance(properties, str):
                        try:
                            properties = json.loads(properties)
                        except:
                            properties = {}
                    
                    entity = MetadataEntity(
                        id=entity_data.get('id', ''),
                        type=entity_data.get('type', 'unknown'),
                        name=entity_data.get('name', ''),
                        description=entity_data.get('description'),
                        properties=properties,
                        source=entity_data.get('source', 'unknown'),
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    
                    score = quality_assessor.assess_entity(entity)
                    scores.append(score)
                    
                    # 监控告警
                    if quality_monitor:
                        entity_alerts = quality_monitor.monitor_entity(entity.id, score)
                        if entity_alerts:
                            alerts_summary[entity.id] = entity_alerts
                except Exception as e:
                    print(f"评估实体 {entity_data.get('id', 'unknown')} 失败: {e}")
                    continue
        
        # 如果没有任何评估结果，返回错误
        if len(scores) == 0:
            raise HTTPException(status_code=400, detail="没有成功评估任何实体")
        
        # 计算指标
        metrics = quality_assessor.calculate_metrics(scores)
        
        # 持久化评估结果
        if sqlite_processor:
            try:
                for score in scores:
                    score_dict = score.to_dict()
                    sqlite_processor.store_quality_score(score_dict)
            except Exception as e:
                print(f"保存批量评估结果失败: {e}")
        
        return {
            "scores": [s.to_dict() for s in scores],
            "metrics": metrics.to_dict(),
            "alerts": alerts_summary,
            "count": len(scores)
        }
    except HTTPException:
        raise
    except Exception as e:
        error_detail = f"批量评估失败: {str(e)}"
        # 只在调试模式下包含完整traceback
        import os
        if os.getenv('DEBUG', 'false').lower() == 'true':
            error_detail += f"\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("/scores", response_model=Dict[str, Any])
async def get_quality_scores(
    entity_id: Optional[str] = Query(None, description="实体ID过滤"),
    entity_type: Optional[str] = Query(None, description="实体类型过滤"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量"),
    offset: int = Query(0, ge=0, description="偏移量")
):
    """查询质量评估结果"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite处理器未初始化")
    
    try:
        # 从数据库查询评估结果
        scores, total = sqlite_processor.query_quality_scores(
            entity_id=entity_id,
            entity_type=entity_type,
            limit=limit,
            offset=offset
        )
        
        return {
            "scores": scores,
            "count": len(scores),
            "total": total
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询评估结果失败: {str(e)}")


@router.get("/metrics", response_model=Dict[str, Any])
async def get_quality_metrics(
    entity_type: Optional[str] = Query(None, description="实体类型过滤"),
    source: Optional[str] = Query(None, description="数据源过滤"),
    limit: int = Query(1000, ge=1, le=10000, description="限制数量")
):
    """获取质量指标"""
    if not quality_assessor or not sqlite_processor:
        raise HTTPException(status_code=500, detail="质量评估器或SQLite处理器未初始化")
    
    try:
        # 从数据库获取最新的评估结果
        score_dicts = sqlite_processor.get_latest_quality_scores(entity_type=entity_type)
        
        # 如果指定了source，需要进一步过滤（需要关联实体表）
        if source:
            # 获取指定source的实体ID列表
            entities = sqlite_processor.query_entities(source=source, limit=limit)
            entity_ids = [e['id'] for e in entities]
            # 过滤评分结果
            score_dicts = [s for s in score_dicts if s.get('entity_id') in entity_ids]
        
        # 将字典转换为 MetadataQualityScore 对象
        from ..core.quality import MetadataQualityScore
        scores = []
        for score_dict in score_dicts:
            try:
                # 从字典创建 MetadataQualityScore 对象
                score = MetadataQualityScore(
                    entity_id=score_dict['entity_id'],
                    entity_type=score_dict['entity_type'],
                    completeness_score=score_dict['completeness_score'],
                    accuracy_score=score_dict['accuracy_score'],
                    consistency_score=score_dict['consistency_score'],
                    freshness_score=score_dict['freshness_score'],
                    overall_score=score_dict['overall_score'],
                    completeness_details=score_dict.get('completeness_details', {}),
                    accuracy_details=score_dict.get('accuracy_details', {}),
                    consistency_details=score_dict.get('consistency_details', {}),
                    freshness_details=score_dict.get('freshness_details', {})
                )
                scores.append(score)
            except Exception as e:
                print(f"转换评分对象失败: {e}")
                continue
        
        # 计算指标
        metrics = quality_assessor.calculate_metrics(scores)
        
        return metrics.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取指标失败: {str(e)}")


# ========== 规则管理 API ==========

@router.get("/rules", response_model=Dict[str, Any])
async def get_rules():
    """获取所有规则"""
    if not rule_engine:
        raise HTTPException(status_code=500, detail="规则引擎未初始化")
    
    return rule_engine.to_dict()


@router.post("/rules", response_model=Dict[str, Any])
async def add_rule(request: AddRuleRequest):
    """添加规则"""
    if not rule_engine:
        raise HTTPException(status_code=500, detail="规则引擎未初始化")
    
    try:
        # 构建规则配置
        rule_config = {
            "type": request.type,
            "name": request.name or f"{request.type}_{request.field_name or 'rule'}",
            "dimension": request.dimension,
            "severity": request.severity,
            "enabled": request.enabled,
            "description": request.description or ""
        }
        
        # 添加规则特定参数
        if request.field_name:
            rule_config["field_name"] = request.field_name
        if request.pattern:
            rule_config["pattern"] = request.pattern
        if request.min_value is not None:
            rule_config["min_value"] = request.min_value
        if request.max_value is not None:
            rule_config["max_value"] = request.max_value
        if request.allowed_values:
            rule_config["allowed_values"] = request.allowed_values
        if request.relationship_type:
            rule_config["relationship_type"] = request.relationship_type
        if request.required is not None:
            rule_config["required"] = request.required
        if request.max_age_days is not None:
            rule_config["max_age_days"] = request.max_age_days
        if request.expression:
            rule_config["expression"] = request.expression
        
        # 创建规则
        rule = rule_engine._create_rule_from_config(rule_config)
        if rule:
            rule_engine.add_rule(rule)
            return {"success": True, "rule": rule.to_dict()}
        else:
            raise HTTPException(status_code=400, detail="无法创建规则")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加规则失败: {str(e)}")


@router.delete("/rules/{rule_name}", response_model=Dict[str, Any])
async def delete_rule(rule_name: str):
    """删除规则"""
    if not rule_engine:
        raise HTTPException(status_code=500, detail="规则引擎未初始化")
    
    rule_engine.remove_rule(rule_name)
    return {"success": True, "message": f"规则 {rule_name} 已删除"}


@router.put("/rules/{rule_name}/enable", response_model=Dict[str, Any])
async def enable_rule(rule_name: str):
    """启用规则"""
    if not rule_engine:
        raise HTTPException(status_code=500, detail="规则引擎未初始化")
    
    rule_engine.enable_rule(rule_name)
    return {"success": True, "message": f"规则 {rule_name} 已启用"}


@router.put("/rules/{rule_name}/disable", response_model=Dict[str, Any])
async def disable_rule(rule_name: str):
    """禁用规则"""
    if not rule_engine:
        raise HTTPException(status_code=500, detail="规则引擎未初始化")
    
    rule_engine.disable_rule(rule_name)
    return {"success": True, "message": f"规则 {rule_name} 已禁用"}


# ========== 告警管理 API ==========

@router.get("/alerts", response_model=Dict[str, Any])
async def get_alerts(
    entity_id: Optional[str] = Query(None, description="实体ID过滤"),
    rule_name: Optional[str] = Query(None, description="规则名称过滤"),
    severity: Optional[str] = Query(None, description="严重程度过滤"),
    limit: int = Query(100, ge=1, le=1000, description="限制数量")
):
    """获取告警历史"""
    if not quality_monitor:
        raise HTTPException(status_code=500, detail="质量监控器未初始化")
    
    alerts = quality_monitor.get_alert_history(
        entity_id=entity_id,
        rule_name=rule_name,
        severity=severity,
        limit=limit
    )
    
    return {
        "alerts": alerts,
        "count": len(alerts)
    }


@router.get("/alerts/statistics", response_model=Dict[str, Any])
async def get_alert_statistics(days: int = Query(7, ge=1, le=365, description="统计天数")):
    """获取告警统计"""
    if not quality_monitor:
        raise HTTPException(status_code=500, detail="质量监控器未初始化")
    
    stats = quality_monitor.get_alert_statistics(days=days)
    return stats


@router.post("/alerts/configure", response_model=Dict[str, Any])
async def configure_alerts(request: AlertConfigRequest):
    """配置告警"""
    if not quality_monitor:
        raise HTTPException(status_code=500, detail="质量监控器未初始化")
    
    try:
        if request.email:
            email_config = request.email
            quality_monitor.configure_email(
                smtp_host=email_config.get("smtp_host"),
                smtp_port=email_config.get("smtp_port", 587),
                username=email_config.get("username"),
                password=email_config.get("password"),
                from_email=email_config.get("from_email"),
                to_emails=email_config.get("to_emails", [])
            )
        
        if request.webhook:
            webhook_config = request.webhook
            quality_monitor.configure_webhook(
                url=webhook_config.get("url"),
                method=webhook_config.get("method", "POST"),
                headers=webhook_config.get("headers")
            )
        
        return {"success": True, "message": "告警配置已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置告警失败: {str(e)}")


# ========== 趋势分析 API ==========

@router.get("/trend/{entity_id}", response_model=Dict[str, Any])
async def get_quality_trend(
    entity_id: str,
    days: int = Query(30, ge=1, le=365, description="统计天数")
):
    """获取实体质量趋势"""
    # 注意：趋势分析需要历史数据支持，这里简化处理
    return {
        "entity_id": entity_id,
        "message": "趋势分析功能需要历史数据支持，请确保定期记录质量评分"
    }

