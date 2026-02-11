"""
搜索与语义检索 API
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from ..core.search import SearchService, SearchResult
from ..core.graph import GraphStore
from ..processing.sqlite import SQLiteProcessor

router = APIRouter(prefix="/api/search", tags=["search"])

# 全局依赖
graph_store: Optional[GraphStore] = None
sqlite_processor: Optional[SQLiteProcessor] = None
search_service: Optional[SearchService] = None


def set_dependencies(gs: GraphStore, sp: Optional[SQLiteProcessor] = None):
    """设置依赖"""
    global graph_store, sqlite_processor, search_service
    graph_store = gs
    sqlite_processor = sp
    if graph_store:
        search_service = SearchService(graph_store, sqlite_processor)


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    entity_type: Optional[str] = None
    source: Optional[str] = None
    limit: int = 50
    use_semantic: bool = False
    use_graph: bool = True


@router.get("/")
async def search(
    q: str = Query(..., description="搜索关键词"),
    entity_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    use_semantic: bool = Query(False),
    use_graph: bool = Query(True)
):
    """
    综合搜索
    
    Args:
        q: 搜索关键词
        entity_type: 实体类型过滤
        source: 数据源过滤
        limit: 结果数量限制
        use_semantic: 是否使用语义搜索
        use_graph: 是否使用图推荐
    """
    if not search_service:
        raise HTTPException(status_code=500, detail="搜索服务未初始化")
    
    try:
        results = search_service.search(
            q,
            entity_type=entity_type,
            source=source,
            limit=limit,
            use_semantic=use_semantic,
            use_graph=use_graph
        )
        
        return {
            "query": q,
            "results": [
                {
                    "entity": r.entity,
                    "score": r.score,
                    "match_type": r.match_type,
                    "highlights": r.highlights
                }
                for r in results
            ],
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/")
async def search_post(request: SearchRequest):
    """
    综合搜索（POST方式）
    
    Args:
        request: 搜索请求
    """
    if not search_service:
        raise HTTPException(status_code=500, detail="搜索服务未初始化")
    
    try:
        results = search_service.search(
            request.query,
            entity_type=request.entity_type,
            source=request.source,
            limit=request.limit,
            use_semantic=request.use_semantic,
            use_graph=request.use_graph
        )
        
        return {
            "query": request.query,
            "results": [
                {
                    "entity": r.entity,
                    "score": r.score,
                    "match_type": r.match_type,
                    "highlights": r.highlights
                }
                for r in results
            ],
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/semantic")
async def semantic_search(
    q: str = Query(..., description="搜索关键词"),
    entity_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    """
    语义搜索
    
    Args:
        q: 搜索关键词
        entity_type: 实体类型过滤
        source: 数据源过滤
        limit: 结果数量限制
    """
    if not search_service:
        raise HTTPException(status_code=500, detail="搜索服务未初始化")
    
    try:
        results = search_service._semantic_search(
            q,
            entity_type=entity_type,
            source=source,
            limit=limit
        )
        
        return {
            "query": q,
            "results": [
                {
                    "entity": r.entity,
                    "score": r.score,
                    "match_type": r.match_type,
                    "highlights": r.highlights
                }
                for r in results
            ],
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend/{entity_id}")
async def get_recommendations(
    entity_id: str,
    limit: int = Query(10, ge=1, le=100)
):
    """
    获取图推荐
    
    Args:
        entity_id: 实体ID
        limit: 推荐数量
    """
    if not search_service:
        raise HTTPException(status_code=500, detail="搜索服务未初始化")
    
    try:
        results = search_service._graph_recommendation(entity_id, limit)
        
        return {
            "entity_id": entity_id,
            "recommendations": [
                {
                    "entity": r.entity,
                    "score": r.score,
                    "match_type": r.match_type,
                    "highlights": r.highlights
                }
                for r in results
            ],
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality")
async def search_with_quality(
    q: str = Query(..., description="搜索关键词"),
    entity_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    min_quality: float = Query(0.0, ge=0.0, le=1.0)
):
    """
    带质量过滤的搜索
    
    Args:
        q: 搜索关键词
        entity_type: 实体类型过滤
        source: 数据源过滤
        limit: 结果数量限制
        min_quality: 最小质量评分
    """
    if not search_service:
        raise HTTPException(status_code=500, detail="搜索服务未初始化")
    
    try:
        results = search_service.search_with_quality(
            q,
            entity_type=entity_type,
            source=source,
            limit=limit,
            min_quality=min_quality
        )
        
        return {
            "query": q,
            "results": [
                {
                    "entity": r.entity,
                    "score": r.score,
                    "match_type": r.match_type,
                    "highlights": r.highlights
                }
                for r in results
            ],
            "count": len(results),
            "min_quality": min_quality
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



