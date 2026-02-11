"""
版本控制与审计 API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from ..core.version import (
    MetadataVersionControl, MetadataVersion, AuditEvent, OperationType
)
from ..core.models import MetadataEntity

router = APIRouter(prefix="/api/version", tags=["version"])

# 全局依赖
version_control: Optional[MetadataVersionControl] = None


def set_dependencies():
    """设置依赖"""
    global version_control
    if not version_control:
        version_control = MetadataVersionControl()


class CreateVersionRequest(BaseModel):
    """创建版本请求"""
    entity: Dict[str, Any]
    created_by: Optional[str] = None
    change_reason: Optional[str] = None
    metamodel_version: Optional[str] = None


class RollbackRequest(BaseModel):
    """回滚请求"""
    entity_id: str
    target_version: int


class AuditEventRequest(BaseModel):
    """审计事件请求"""
    entity_id: str
    operation_type: str
    operator: Optional[str] = None
    changed_fields: Optional[List[str]] = None
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    change_reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@router.post("/create")
async def create_version(request: CreateVersionRequest):
    """
    创建实体版本
    
    Args:
        request: 创建版本请求
    """
    if not version_control:
        raise HTTPException(status_code=500, detail="版本控制系统未初始化")
    
    try:
        # 构建实体对象
        entity_data = request.entity
        entity = MetadataEntity(
            id=entity_data.get("id"),
            type=entity_data.get("type"),
            name=entity_data.get("name"),
            description=entity_data.get("description"),
            properties=entity_data.get("properties", {}),
            source=entity_data.get("source"),
            created_at=datetime.fromisoformat(entity_data.get("created_at")) if isinstance(entity_data.get("created_at"), str) else entity_data.get("created_at"),
            updated_at=datetime.fromisoformat(entity_data.get("updated_at")) if isinstance(entity_data.get("updated_at"), str) else entity_data.get("updated_at")
        )
        
        version = version_control.create_version(
            entity,
            created_by=request.created_by,
            change_reason=request.change_reason,
            metamodel_version=request.metamodel_version
        )
        
        return {
            "entity_id": version.entity_id,
            "version": version.version,
            "metamodel_version": version.metamodel_version,
            "created_at": version.created_at.isoformat(),
            "created_by": version.created_by,
            "change_reason": version.change_reason
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}")
async def get_entity_versions(
    entity_id: str,
    version: Optional[int] = Query(None)
):
    """
    获取实体版本
    
    Args:
        entity_id: 实体ID
        version: 版本号（可选，如果不提供则返回所有版本）
    """
    if not version_control:
        raise HTTPException(status_code=500, detail="版本控制系统未初始化")
    
    try:
        if version is not None:
            # 获取指定版本
            v = version_control.get_version(entity_id, version)
            if not v:
                raise HTTPException(status_code=404, detail=f"版本 {version} 不存在")
            
            return {
                "entity_id": v.entity_id,
                "version": v.version,
                "metamodel_version": v.metamodel_version,
                "snapshot": v.snapshot,
                "created_at": v.created_at.isoformat(),
                "created_by": v.created_by,
                "change_reason": v.change_reason
            }
        else:
            # 获取所有版本
            versions = version_control.list_versions(entity_id)
            return {
                "entity_id": entity_id,
                "versions": [
                    {
                        "version": v.version,
                        "metamodel_version": v.metamodel_version,
                        "created_at": v.created_at.isoformat(),
                        "created_by": v.created_by,
                        "change_reason": v.change_reason
                    }
                    for v in versions
                ],
                "count": len(versions),
                "current_version": version_control.get_current_version(entity_id)
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}/diff")
async def diff_versions(
    entity_id: str,
    version1: int = Query(..., description="版本1"),
    version2: int = Query(..., description="版本2")
):
    """
    对比两个版本
    
    Args:
        entity_id: 实体ID
        version1: 版本1
        version2: 版本2
    """
    if not version_control:
        raise HTTPException(status_code=500, detail="版本控制系统未初始化")
    
    try:
        diff = version_control.diff_versions(entity_id, version1, version2)
        return diff
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback")
async def rollback_version(request: RollbackRequest):
    """
    回滚到指定版本
    
    Args:
        request: 回滚请求
    """
    if not version_control:
        raise HTTPException(status_code=500, detail="版本控制系统未初始化")
    
    try:
        success = version_control.rollback(request.entity_id, request.target_version)
        if not success:
            raise HTTPException(status_code=400, detail="回滚失败")
        
        return {
            "success": True,
            "entity_id": request.entity_id,
            "target_version": request.target_version,
            "new_version": version_control.get_current_version(request.entity_id)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/audit")
async def record_audit_event(request: AuditEventRequest):
    """
    记录审计事件
    
    Args:
        request: 审计事件请求
    """
    if not version_control:
        raise HTTPException(status_code=500, detail="版本控制系统未初始化")
    
    try:
        # 验证操作类型
        try:
            op_type = OperationType(request.operation_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的操作类型: {request.operation_type}")
        
        import uuid
        event = AuditEvent(
            event_id=str(uuid.uuid4()),
            entity_id=request.entity_id,
            operation_type=op_type,
            operator=request.operator,
            changed_fields=request.changed_fields or [],
            old_value=request.old_value,
            new_value=request.new_value,
            change_reason=request.change_reason,
            timestamp=datetime.now(),
            metadata=request.metadata or {}
        )
        
        success = version_control.record_audit_event(event)
        if not success:
            raise HTTPException(status_code=500, detail="记录审计事件失败")
        
        return {
            "success": True,
            "event_id": event.event_id,
            "timestamp": event.timestamp.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/events")
async def get_audit_events(
    entity_id: Optional[str] = Query(None),
    operation_type: Optional[str] = Query(None),
    start_time: Optional[str] = Query(None),
    end_time: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    查询审计事件
    
    Args:
        entity_id: 实体ID过滤
        operation_type: 操作类型过滤
        start_time: 开始时间（ISO格式）
        end_time: 结束时间（ISO格式）
        limit: 结果数量限制
    """
    if not version_control:
        raise HTTPException(status_code=500, detail="版本控制系统未初始化")
    
    try:
        op_type = None
        if operation_type:
            try:
                op_type = OperationType(operation_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的操作类型: {operation_type}")
        
        start_dt = None
        if start_time:
            start_dt = datetime.fromisoformat(start_time)
        
        end_dt = None
        if end_time:
            end_dt = datetime.fromisoformat(end_time)
        
        events = version_control.get_audit_events(
            entity_id=entity_id,
            operation_type=op_type,
            start_time=start_dt,
            end_time=end_dt,
            limit=limit
        )
        
        return {
            "events": [
                {
                    "event_id": e.event_id,
                    "entity_id": e.entity_id,
                    "operation_type": e.operation_type.value,
                    "operator": e.operator,
                    "changed_fields": e.changed_fields,
                    "old_value": e.old_value,
                    "new_value": e.new_value,
                    "change_reason": e.change_reason,
                    "timestamp": e.timestamp.isoformat(),
                    "metadata": e.metadata
                }
                for e in events
            ],
            "count": len(events)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/audit/statistics")
async def get_audit_statistics(
    days: int = Query(30, ge=1, le=365)
):
    """
    获取审计统计信息
    
    Args:
        days: 统计天数
    """
    if not version_control:
        raise HTTPException(status_code=500, detail="版本控制系统未初始化")
    
    try:
        stats = version_control.get_audit_statistics(days)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

