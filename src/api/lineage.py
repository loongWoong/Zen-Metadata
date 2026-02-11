"""
血缘追踪 API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from ..core.lineage import LineageTracker, LineageGranularity, ImpactAnalysis
from ..core.graph import GraphStore

router = APIRouter(prefix="/api/lineage", tags=["lineage"])

# 全局依赖
graph_store: Optional[GraphStore] = None
lineage_tracker: Optional[LineageTracker] = None


def set_dependencies(gs: GraphStore):
    """设置依赖"""
    global graph_store, lineage_tracker
    graph_store = gs
    if graph_store:
        lineage_tracker = LineageTracker(graph_store)


class LineageRequest(BaseModel):
    """血缘查询请求"""
    entity_id: str
    granularity: Optional[str] = None
    max_depth: int = 5


class ImpactAnalysisRequest(BaseModel):
    """影响分析请求"""
    entity_id: str
    direction: str = "downstream"  # "upstream" or "downstream"
    include_quality: bool = True


@router.get("/discover/{entity_id}")
async def discover_lineage(
    entity_id: str,
    granularity: Optional[str] = Query(None),
    max_depth: int = Query(5, ge=1, le=10)
):
    """
    发现实体的血缘关系
    
    Args:
        entity_id: 实体ID
        granularity: 血缘粒度（column/table/job/system）
        max_depth: 最大深度
    """
    if not lineage_tracker:
        raise HTTPException(status_code=500, detail="血缘追踪器未初始化")
    
    try:
        gran = None
        if granularity:
            try:
                gran = LineageGranularity(granularity)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的血缘粒度: {granularity}")
        
        result = lineage_tracker.discover_lineage(entity_id, gran, max_depth)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/upstream/{entity_id}")
async def trace_upstream(
    entity_id: str,
    depth: int = Query(-1, ge=-1, le=10)
):
    """
    追踪上游血缘
    
    Args:
        entity_id: 实体ID
        depth: 追踪深度（-1表示无限制）
    """
    if not lineage_tracker:
        raise HTTPException(status_code=500, detail="血缘追踪器未初始化")
    
    try:
        paths = lineage_tracker.trace_upstream(entity_id, depth)
        return {
            "entity_id": entity_id,
            "direction": "upstream",
            "paths": [
                {
                    "path": p.path,
                    "relationships": p.relationships,
                    "depth": p.depth,
                    "path_length": p.path_length,
                    "quality_score": p.quality_score,
                    "risk_score": p.risk_score
                }
                for p in paths
            ],
            "count": len(paths)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/downstream/{entity_id}")
async def trace_downstream(
    entity_id: str,
    depth: int = Query(-1, ge=-1, le=10)
):
    """
    追踪下游血缘
    
    Args:
        entity_id: 实体ID
        depth: 追踪深度（-1表示无限制）
    """
    if not lineage_tracker:
        raise HTTPException(status_code=500, detail="血缘追踪器未初始化")
    
    try:
        paths = lineage_tracker.trace_downstream(entity_id, depth)
        return {
            "entity_id": entity_id,
            "direction": "downstream",
            "paths": [
                {
                    "path": p.path,
                    "relationships": p.relationships,
                    "depth": p.depth,
                    "path_length": p.path_length,
                    "quality_score": p.quality_score,
                    "risk_score": p.risk_score
                }
                for p in paths
            ],
            "count": len(paths)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/impact")
async def analyze_impact(request: ImpactAnalysisRequest):
    """
    分析影响范围
    
    Args:
        request: 影响分析请求
    """
    if not lineage_tracker:
        raise HTTPException(status_code=500, detail="血缘追踪器未初始化")
    
    try:
        analysis = lineage_tracker.analyze_impact(
            request.entity_id,
            request.direction,
            request.include_quality
        )
        
        return {
            "entity_id": analysis.entity_id,
            "direction": analysis.direction,
            "affected_entities": analysis.affected_entities,
            "paths": [
                {
                    "path": p.path,
                    "relationships": p.relationships,
                    "depth": p.depth,
                    "path_length": p.path_length,
                    "quality_score": p.quality_score,
                    "risk_score": p.risk_score
                }
                for p in analysis.paths
            ],
            "risk_summary": analysis.risk_summary,
            "total_affected": analysis.total_affected,
            "high_risk_count": analysis.high_risk_count,
            "medium_risk_count": analysis.medium_risk_count,
            "low_risk_count": analysis.low_risk_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/impact/{entity_id}")
async def get_impact_analysis(
    entity_id: str,
    direction: str = Query("downstream", regex="^(upstream|downstream)$"),
    include_quality: bool = Query(True)
):
    """
    获取影响分析（GET方式）
    
    Args:
        entity_id: 实体ID
        direction: 分析方向
        include_quality: 是否包含质量评分
    """
    request = ImpactAnalysisRequest(
        entity_id=entity_id,
        direction=direction,
        include_quality=include_quality
    )
    return await analyze_impact(request)



