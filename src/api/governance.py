"""
数据治理 API
"""
from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime
import uuid

from ..core.governance import (
    Tag, EntityTag, DataStandard, StandardViolation,
    TagService, StandardService, CatalogService,
    TagCategory, DataStandardType
)
from ..processing.sqlite import SQLiteProcessor
from ..core.graph import GraphStore


router = APIRouter(prefix="/api/governance", tags=["数据治理"])

# 全局依赖
sqlite_processor: Optional[SQLiteProcessor] = None
graph_store: Optional[GraphStore] = None
tag_service: Optional[TagService] = None
standard_service: Optional[StandardService] = None
catalog_service: Optional[CatalogService] = None


def set_dependencies(sqlite: SQLiteProcessor, graph: Optional[GraphStore] = None):
    """设置依赖"""
    global sqlite_processor, graph_store, tag_service, standard_service, catalog_service
    sqlite_processor = sqlite
    graph_store = graph
    tag_service = TagService(sqlite, graph)
    standard_service = StandardService(sqlite)
    catalog_service = CatalogService(sqlite, graph)


# ========== 请求/响应模型 ==========

class CreateTagRequest(BaseModel):
    """创建标签请求"""
    name: str
    category: str
    description: Optional[str] = None
    color: str = "#808080"
    created_by: Optional[str] = None


class UpdateTagRequest(BaseModel):
    """更新标签请求"""
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class AddEntityTagRequest(BaseModel):
    """添加实体标签请求"""
    entity_id: str
    tag_id: str
    user_id: Optional[str] = None
    confidence: float = 1.0
    is_auto: bool = False


class BatchAddEntityTagsRequest(BaseModel):
    """批量添加实体标签请求"""
    entity_ids: List[str]
    tag_id: str
    user_id: Optional[str] = None
    confidence: float = 1.0
    is_auto: bool = False


class CreateStandardRequest(BaseModel):
    """创建数据标准请求"""
    name: str
    type: str
    entity_type: Optional[str] = None
    rule: Dict[str, Any]
    description: Optional[str] = None
    enabled: bool = True
    created_by: Optional[str] = None


class UpdateStandardRequest(BaseModel):
    """更新数据标准请求"""
    name: Optional[str] = None
    type: Optional[str] = None
    entity_type: Optional[str] = None
    rule: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class ValidateEntityRequest(BaseModel):
    """验证实体请求"""
    entity_id: str
    standard_id: Optional[str] = None


# ========== 标签管理 API ==========

@router.post("/tags", response_model=Dict[str, Any])
async def create_tag(request: CreateTagRequest):
    """创建标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    try:
        # 确保颜色值是字符串格式
        color = request.color
        if not isinstance(color, str):
            color = str(color) if color else "#808080"
        
        tag = Tag(
            id=str(uuid.uuid4()),
            name=request.name,
            category=request.category,
            description=request.description,
            color=color,
            created_by=request.created_by
        )
        
        created_tag = tag_service.create_tag(tag)
        # 使用model_dump()（Pydantic v2）或dict()（Pydantic v1）
        tag_dict = created_tag.model_dump() if hasattr(created_tag, 'model_dump') else created_tag.dict()
        return {"success": True, "tag": tag_dict}
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"创建标签失败: {str(e)}\n{traceback.format_exc()}")


@router.get("/tags", response_model=Dict[str, Any])
async def list_tags(category: Optional[str] = Query(None)):
    """列出标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    tags = tag_service.list_tags(category=category)
    # 使用model_dump()（Pydantic v2）或dict()（Pydantic v1）
    tag_dicts = [tag.model_dump() if hasattr(tag, 'model_dump') else tag.dict() for tag in tags]
    return {"tags": tag_dicts, "count": len(tags)}


@router.get("/tags/{tag_id}", response_model=Dict[str, Any])
async def get_tag(tag_id: str):
    """获取标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    tag = tag_service.get_tag(tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    tag_dict = tag.model_dump() if hasattr(tag, 'model_dump') else tag.dict()
    return {"tag": tag_dict}


@router.put("/tags/{tag_id}", response_model=Dict[str, Any])
async def update_tag(tag_id: str, request: UpdateTagRequest):
    """更新标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    updates = request.dict(exclude_unset=True)
    tag = tag_service.update_tag(tag_id, updates)
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    tag_dict = tag.model_dump() if hasattr(tag, 'model_dump') else tag.dict()
    return {"success": True, "tag": tag_dict}


@router.delete("/tags/{tag_id}", response_model=Dict[str, Any])
async def delete_tag(tag_id: str):
    """删除标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    success = tag_service.delete_tag(tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    return {"success": True, "message": "标签已删除"}


@router.post("/entity-tags/batch", response_model=Dict[str, Any])
async def batch_add_entity_tags(request: BatchAddEntityTagsRequest):
    """批量为实体添加标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    results = []
    errors = []
    
    for entity_id in request.entity_ids:
        try:
            entity_tag = EntityTag(
                id=str(uuid.uuid4()),
                entity_id=entity_id,
                tag_id=request.tag_id,
                user_id=request.user_id,
                confidence=request.confidence,
                is_auto=request.is_auto
            )
            created = tag_service.add_entity_tag(entity_tag)
            entity_tag_dict = created.model_dump() if hasattr(created, 'model_dump') else created.dict()
            results.append({
                "entity_id": entity_id,
                "success": True,
                "entity_tag_id": entity_tag_dict.get('id', created.id)
            })
        except Exception as e:
            errors.append({
                "entity_id": entity_id,
                "error": str(e)
            })
    
    return {
        "success": len(errors) == 0,
        "total": len(request.entity_ids),
        "succeeded": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors
    }


@router.post("/entity-tags", response_model=Dict[str, Any])
async def add_entity_tag(request: AddEntityTagRequest):
    """为实体添加标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    entity_tag = EntityTag(
        id=str(uuid.uuid4()),
        entity_id=request.entity_id,
        tag_id=request.tag_id,
        user_id=request.user_id,
        confidence=request.confidence,
        is_auto=request.is_auto
    )
    
    created = tag_service.add_entity_tag(entity_tag)
    entity_tag_dict = created.model_dump() if hasattr(created, 'model_dump') else created.dict()
    return {"success": True, "entity_tag": entity_tag_dict}


@router.delete("/entity-tags", response_model=Dict[str, Any])
async def remove_entity_tag(entity_id: str = Query(...), tag_id: str = Query(...)):
    """移除实体标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    success = tag_service.remove_entity_tag(entity_id, tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="实体标签关联不存在")
    
    return {"success": True, "message": "标签已移除"}


@router.get("/entities/{entity_id}/tags", response_model=Dict[str, Any])
async def get_entity_tags(entity_id: str):
    """获取实体的标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    tags = tag_service.get_entity_tags(entity_id)
    return {"tags": tags, "count": len(tags)}


@router.post("/entities/tags/batch", response_model=Dict[str, Any])
async def batch_get_entity_tags(entity_ids: List[str] = Body(..., description="实体ID列表")):
    """批量获取多个实体的标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    if not entity_ids:
        return {"tags_map": {}, "count": 0}
    
    tags_map = tag_service.batch_get_entity_tags(entity_ids)
    return {"tags_map": tags_map, "count": len(tags_map)}


@router.get("/tags/{tag_id}/entities", response_model=Dict[str, Any])
async def get_tagged_entities(tag_id: str, limit: int = Query(100, ge=1, le=1000)):
    """获取带标签的实体"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    entity_ids = tag_service.get_tagged_entities(tag_id, limit=limit)
    return {"entity_ids": entity_ids, "count": len(entity_ids)}


@router.get("/entities/{entity_id}/tags/recommend", response_model=Dict[str, Any])
async def recommend_tags(entity_id: str, limit: int = Query(5, ge=1, le=20)):
    """推荐标签"""
    if not tag_service:
        raise HTTPException(status_code=500, detail="标签服务未初始化")
    
    recommendations = tag_service.recommend_tags(entity_id, limit=limit)
    return {"recommendations": recommendations, "count": len(recommendations)}


# ========== 数据标准管理 API ==========

@router.post("/standards", response_model=Dict[str, Any])
async def create_standard(request: CreateStandardRequest):
    """创建数据标准"""
    if not standard_service:
        raise HTTPException(status_code=500, detail="标准服务未初始化")
    
    standard = DataStandard(
        id=str(uuid.uuid4()),
        name=request.name,
        type=request.type,
        entity_type=request.entity_type,
        rule=request.rule,
        description=request.description,
        enabled=request.enabled,
        created_by=request.created_by
    )
    
    created = standard_service.create_standard(standard)
    return {"success": True, "standard": created.dict()}


@router.get("/standards", response_model=Dict[str, Any])
async def list_standards(
    type: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None)
):
    """列出数据标准"""
    if not standard_service:
        raise HTTPException(status_code=500, detail="标准服务未初始化")
    
    standards = standard_service.list_standards(standard_type=type, entity_type=entity_type)
    return {"standards": [s.dict() for s in standards], "count": len(standards)}


@router.get("/standards/{standard_id}", response_model=Dict[str, Any])
async def get_standard(standard_id: str):
    """获取数据标准"""
    if not standard_service:
        raise HTTPException(status_code=500, detail="标准服务未初始化")
    
    standard = standard_service.get_standard(standard_id)
    if not standard:
        raise HTTPException(status_code=404, detail="标准不存在")
    
    return {"standard": standard.dict()}


@router.put("/standards/{standard_id}", response_model=Dict[str, Any])
async def update_standard(standard_id: str, request: UpdateStandardRequest):
    """更新数据标准"""
    if not standard_service:
        raise HTTPException(status_code=500, detail="标准服务未初始化")
    
    updates = request.dict(exclude_unset=True)
    standard = standard_service.update_standard(standard_id, updates)
    if not standard:
        raise HTTPException(status_code=404, detail="标准不存在")
    
    return {"success": True, "standard": standard.dict()}


@router.delete("/standards/{standard_id}", response_model=Dict[str, Any])
async def delete_standard(standard_id: str):
    """删除数据标准"""
    if not standard_service:
        raise HTTPException(status_code=500, detail="标准服务未初始化")
    
    success = standard_service.delete_standard(standard_id)
    if not success:
        raise HTTPException(status_code=404, detail="标准不存在")
    
    return {"success": True, "message": "标准已删除"}


@router.post("/standards/validate", response_model=Dict[str, Any])
async def validate_entity(request: ValidateEntityRequest):
    """验证实体是否符合标准"""
    if not standard_service:
        raise HTTPException(status_code=500, detail="标准服务未初始化")
    
    violations = standard_service.validate_entity(
        request.entity_id,
        standard_id=request.standard_id
    )
    
    # 记录违规项
    for violation in violations:
        standard_service.record_violation(violation)
    
    return {
        "entity_id": request.entity_id,
        "violations": [v.dict() for v in violations],
        "count": len(violations)
    }


@router.get("/violations", response_model=Dict[str, Any])
async def get_violations(
    entity_id: Optional[str] = Query(None),
    standard_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None)
):
    """获取违规项"""
    if not standard_service:
        raise HTTPException(status_code=500, detail="标准服务未初始化")
    
    violations = standard_service.get_violations(
        entity_id=entity_id,
        standard_id=standard_id,
        status=status
    )
    
    return {"violations": [v.dict() for v in violations], "count": len(violations)}


@router.put("/violations/{violation_id}/fix", response_model=Dict[str, Any])
async def fix_violation(violation_id: str):
    """修复违规项"""
    if not standard_service:
        raise HTTPException(status_code=500, detail="标准服务未初始化")
    
    # 更新违规项状态
    cursor = sqlite_processor.conn.cursor()
    cursor.execute("""
        UPDATE standard_violations 
        SET status = 'fixed', fixed_at = ?
        WHERE id = ?
    """, (datetime.now().isoformat(), violation_id))
    sqlite_processor.conn.commit()
    
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="违规项不存在")
    
    return {"success": True, "message": "违规项已标记为已修复"}


# ========== 数据目录与发现 API ==========

@router.get("/catalog", response_model=Dict[str, Any])
async def browse_catalog(
    category: Optional[str] = Query(None),
    tag_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
):
    """浏览数据目录"""
    if not catalog_service:
        raise HTTPException(status_code=500, detail="目录服务未初始化")
    
    entities, total = catalog_service.browse_catalog(
        category=category,
        tag_id=tag_id,
        entity_type=entity_type,
        source=source,
        limit=limit,
        offset=offset
    )
    
    return {
        "entities": entities,
        "count": len(entities),
        "total": total,
        "offset": offset,
        "limit": limit
    }


@router.get("/discover", response_model=Dict[str, Any])
async def discover_entities(
    q: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    limit: int = Query(10, ge=1, le=100)
):
    """智能发现实体"""
    if not catalog_service:
        raise HTTPException(status_code=500, detail="目录服务未初始化")
    
    entities = catalog_service.discover_entities(
        query=q,
        entity_type=entity_type,
        limit=limit
    )
    
    return {"entities": entities, "count": len(entities)}


@router.get("/analytics/usage", response_model=Dict[str, Any])
async def get_usage_analytics(entity_id: Optional[str] = Query(None)):
    """获取使用分析"""
    if not catalog_service:
        raise HTTPException(status_code=500, detail="目录服务未初始化")
    
    analytics = catalog_service.get_usage_analytics(entity_id=entity_id)
    return analytics


@router.get("/categories", response_model=Dict[str, Any])
async def get_categories():
    """获取标签分类列表"""
    return {
        "categories": [
            {"value": cat.value, "label": cat.value}
            for cat in TagCategory
        ]
    }


@router.get("/standard-types", response_model=Dict[str, Any])
async def get_standard_types():
    """获取数据标准类型列表"""
    return {
        "types": [
            {"value": t.value, "label": t.value}
            for t in DataStandardType
        ]
    }

