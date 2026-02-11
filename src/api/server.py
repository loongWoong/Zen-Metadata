"""
FastAPI 服务 - 元数据管理 API
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from pathlib import Path
import traceback
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..core.graph import GraphStore
from ..core.config import get_config, load_config as load_app_config
from ..core.logging_config import setup_logging, get_logger
from ..core.exceptions import ZenMetadataException
from ..core.models import MetadataEntity, MetadataRelationship, QueryResult
from ..collectors.relational import RelationalDatabaseCollector
from ..collectors.graphdb import GraphDatabaseCollector
from ..collectors.code import CodeMetadataCollector
from ..collectors.filesystem import FileSystemCollector
from ..processing.sqlite import SQLiteProcessor
from ..processing.duckdb import DuckDBProcessor
from ..visualization.graphiti import GraphitiVisualizer
from .tasks import router as tasks_router, init_task_manager, set_dependencies as set_tasks_dependencies
from .export import router as export_router, set_dependencies as set_export_dependencies
from .websocket import router as websocket_router, set_task_manager as set_ws_task_manager
from .quality import router as quality_router, set_dependencies as set_quality_dependencies
from .metamodel import router as metamodel_router, set_dependencies as set_metamodel_dependencies
from .lineage import router as lineage_router, set_dependencies as set_lineage_dependencies
from .search import router as search_router, set_dependencies as set_search_dependencies
from .version import router as version_router, set_dependencies as set_version_dependencies
from .auth import router as auth_router, set_dependencies as set_auth_dependencies
from .collaboration import router as collaboration_router, set_dependencies as set_collaboration_dependencies
from .governance import router as governance_router, set_dependencies as set_governance_dependencies
from .visualization import router as visualization_router, set_dependencies as set_visualization_dependencies
from .menu import router as menu_router, set_dependencies as set_menu_dependencies
from .api_management import router as api_management_router, set_dependencies as set_api_management_dependencies
from ..core.tasks import TaskManager
from ..core.metamodel_registry import MetaRegistry
from ..core.auth import AuthService, PermissionEngine
from ..core.user_storage import UserStorage
from ..core.collaboration import CollaborationService

# 初始化配置和日志
config = load_app_config()
logger = setup_logging(
    log_level=config.logging.level,
    log_file=config.logging.file
)
api_logger = get_logger("api")

app = FastAPI(title="Zen Metadata API", version="0.1.0")

# 添加请求日志中间件（最先添加，最后执行）
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin", "none")
        api_logger.debug(f"请求: {request.method} {request.url.path} - Origin: {origin}")
        
        try:
            response = await call_next(request)
            api_logger.debug(f"响应: {request.method} {request.url.path} - Status: {response.status_code}")
            return response
        except Exception as e:
            api_logger.error(f"中间件捕获异常: {type(e).__name__} - {str(e)}", exc_info=True)
            raise

app.add_middleware(LoggingMiddleware)

# CORS 配置 - 最后添加，确保在响应时最先执行
# 注意：当使用 allow_origins=["*"] 时，不能同时使用 allow_credentials=True
# 如果需要支持 credentials，需要明确指定允许的 origins
api_logger.info(f"配置CORS中间件，允许的源: {config.cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
api_logger.info("CORS中间件已配置")

# 全局异常处理器
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """处理HTTP异常，记录详细错误信息"""
    origin = request.headers.get("origin", "unknown")
    api_logger.warning(
        f"HTTP异常: {exc.status_code} - {exc.detail}",
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "origin": origin,
        }
    )
    
    # 返回详细的错误信息，确保包含CORS头
    response = JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": str(request.url.path),
            "method": request.method,
        }
    )
    # 手动添加CORS头
    origin = request.headers.get("origin")
    if origin and origin in config.cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """处理所有未捕获的异常"""
    origin = request.headers.get("origin", "unknown")
    api_logger.error(
        f"未捕获异常: {type(exc).__name__} - {str(exc)}",
        exc_info=True,
        extra={
            "path": str(request.url.path),
            "method": request.method,
            "origin": origin,
        }
    )
    
    # 返回详细的错误信息，确保包含CORS头
    # 在生产环境中，不应该返回完整的 traceback
    error_detail = f"服务器内部错误: {str(exc)}"
    if config.api.debug:
        error_detail += f"\n{traceback.format_exc()}"
    
    response = JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "detail": error_detail,
            "error_type": type(exc).__name__,
            "path": str(request.url.path),
            "method": request.method,
        }
    )
    # 手动添加CORS头
    origin = request.headers.get("origin")
    if origin and origin in config.cors_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# 注册路由
app.include_router(tasks_router)
app.include_router(export_router)
app.include_router(websocket_router)
app.include_router(quality_router)
app.include_router(metamodel_router)
app.include_router(lineage_router)
app.include_router(search_router)
app.include_router(version_router)
app.include_router(auth_router)
app.include_router(collaboration_router)
app.include_router(governance_router)
app.include_router(visualization_router)
app.include_router(menu_router)
app.include_router(api_management_router)

# 全局存储实例
graph_store: Optional[GraphStore] = None
sqlite_processor: Optional[SQLiteProcessor] = None
duckdb_processor: Optional[DuckDBProcessor] = None
user_storage: Optional[UserStorage] = None
auth_service: Optional[AuthService] = None
permission_engine: Optional[PermissionEngine] = None
collaboration_service: Optional[CollaborationService] = None


@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    global graph_store, sqlite_processor, duckdb_processor, meta_registry
    global user_storage, auth_service, permission_engine, collaboration_service
    
    api_logger.info("正在初始化服务...")
    
    # 初始化 FalkorDB（允许连接失败，应用仍可启动）
    try:
        graph_store = GraphStore(
            host=config.falkordb.host,
            port=config.falkordb.port,
            password=config.falkordb.password,
            graph_name=config.falkordb.graph_name
        )
        api_logger.info(f"FalkorDB 连接成功: {config.falkordb.host}:{config.falkordb.port}")
    except Exception as e:
        api_logger.warning(f"FalkorDB 连接失败: {e}，应用将继续启动，但图数据库功能将不可用")
        graph_store = None
    
    # 初始化 SQLite
    sqlite_processor = SQLiteProcessor(config.sqlite.database)
    api_logger.info(f"SQLite 初始化成功: {config.sqlite.database}")
    
    # 初始化 DuckDB
    duckdb_processor = DuckDBProcessor(config.duckdb.database)
    api_logger.info(f"DuckDB 初始化成功: {config.duckdb.database}")
    
    # 初始化元模型注册表（需要在任务管理器之前初始化，以便传递meta_registry）
    metamodels_dir = config.metamodel.get('metamodels_dir', 'metamodels')
    plugins_dir = config.metamodel.get('plugins_dir', 'plugins')
    meta_registry = MetaRegistry(metamodels_dir=metamodels_dir, plugins_dir=plugins_dir)
    meta_registry.load_all()
    set_metamodel_dependencies(meta_registry)
    api_logger.info(
        f"已加载元模型注册表，实体模型数: {len(meta_registry.entity_models)}, "
        f"关系模型数: {len(meta_registry.relationship_models)}, "
        f"采集器类型数: {len(meta_registry.collector_type_map)}"
    )
    
    # 初始化任务管理器
    task_mgr = init_task_manager("data/tasks.json")
    set_tasks_dependencies(graph_store, sqlite_processor, duckdb_processor, meta_registry)
    set_export_dependencies(sqlite_processor, graph_store)
    
    # 初始化质量管理系统
    set_quality_dependencies(graph_store, sqlite_processor)
    
    # 更新质量评估器以使用元模型注册表
    from .quality import quality_assessor
    if quality_assessor:
        quality_assessor.meta_registry = meta_registry
    
    # 初始化血缘追踪系统
    set_lineage_dependencies(graph_store)
    
    # 初始化搜索服务
    set_search_dependencies(graph_store, sqlite_processor)
    
    # 初始化版本控制系统
    set_version_dependencies()
    
    # 加载质量规则配置
    quality_config = config.quality
    if quality_config and quality_config.get('enabled', True):
        from .quality import rule_engine
        if rule_engine:
            # 尝试从文件加载规则
            rules_file = quality_config.get('rules_file', 'config/quality_rules.yaml')
            rules_path = Path(rules_file)
            if rules_path.exists():
                try:
                    import yaml
                    with open(rules_path, 'r', encoding='utf-8') as f:
                        rules_config = yaml.safe_load(f)
                        rule_engine.load_rules_from_config(rules_config)
                        api_logger.info(f"已加载质量规则配置文件: {rules_file}")
                except Exception as e:
                    api_logger.warning(f"加载质量规则配置文件失败: {e}")
            else:
                # 如果文件不存在，尝试从 config 中直接加载规则
                if 'rules' in quality_config:
                    rule_engine.load_rules_from_config(quality_config)
    
    # 设置 WebSocket 任务管理器（修复重复初始化问题）
    if task_mgr:
        set_ws_task_manager(task_mgr)
        api_logger.info("WebSocket 任务管理器已设置")
    
    # 初始化用户存储和认证服务
    user_db_path = config.user_storage.get('database', 'data/users.db')
    user_storage = UserStorage(user_db_path)
    api_logger.info(f"用户存储初始化成功: {user_db_path}")
    
    # 初始化认证服务
    secret_key = config.auth.get('secret_key', 'your-secret-key-change-in-production')
    auth_service = AuthService(secret_key=secret_key)
    api_logger.info("认证服务初始化成功")
    
    # 初始化权限引擎
    permission_engine = PermissionEngine()
    
    # 初始化协作服务
    collaboration_service = CollaborationService()
    
    # 设置API依赖
    set_auth_dependencies(user_storage, auth_service, permission_engine)
    set_collaboration_dependencies(user_storage, collaboration_service)
    set_governance_dependencies(sqlite_processor, graph_store)
    set_menu_dependencies(user_storage, permission_engine)
    set_api_management_dependencies(user_storage, permission_engine)
    
    # 初始化可视化系统
    set_visualization_dependencies(graph_store, sqlite_processor)
    
    api_logger.info("已初始化用户认证与协作服务")
    api_logger.info("已初始化数据治理服务")
    api_logger.info("服务初始化完成")


@app.on_event("shutdown")
async def shutdown_event():
    """关闭时清理"""
    if graph_store:
        graph_store.close()
    if sqlite_processor:
        sqlite_processor.close()
    if duckdb_processor:
        duckdb_processor.close()
    if user_storage:
        user_storage.close()


# API 模型
class CollectRequest(BaseModel):
    """采集请求"""
    collector_type: str
    config: Dict[str, Any]


class QueryRequest(BaseModel):
    """查询请求"""
    query: str
    params: Optional[Dict[str, Any]] = None


# API 端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "Zen Metadata API",
        "version": "0.1.0",
        "endpoints": {
            "collect": "/api/collect",
            "query": "/api/query",
            "entities": "/api/entities",
            "relationships": "/api/relationships",
            "visualize": "/api/visualize",
            "statistics": "/api/statistics"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "services": {
            "graph_store": graph_store is not None,
            "sqlite_processor": sqlite_processor is not None,
            "duckdb_processor": duckdb_processor is not None,
            "user_storage": user_storage is not None,
            "auth_service": auth_service is not None
        }
    }


@app.post("/api/collect")
async def collect_metadata(request: CollectRequest):
    """
    采集元数据
    
    Args:
        request: 采集请求
        
    Returns:
        采集结果
    """
    try:
        collector = None
        
        if request.collector_type == "relational":
            conn_str = request.config.get("connection_string")
            source = request.config.get("source", "relational_db")
            collector = RelationalDatabaseCollector(conn_str, source, request.config)
        
        elif request.collector_type == "graphdb":
            db_type = request.config.get("db_type")
            conn_config = request.config.get("connection_config", {})
            source = request.config.get("source", "graph_db")
            collector = GraphDatabaseCollector(db_type, conn_config, source, request.config)
        
        elif request.collector_type == "code":
            source_path = request.config.get("source_path")
            source = request.config.get("source", "code")
            languages = request.config.get("languages", ["python"])
            collector = CodeMetadataCollector(source_path, source, languages, request.config)
        
        elif request.collector_type == "filesystem":
            scan_paths = request.config.get("scan_paths", [])
            source = request.config.get("source", "filesystem")
            collector = FileSystemCollector(scan_paths, source, request.config)
        
        else:
            raise HTTPException(status_code=400, detail=f"不支持的采集器类型: {request.collector_type}")
        
        # 在线程池中执行采集，避免阻塞主线程
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result = await loop.run_in_executor(executor, collector.collect)
        
        # 存储到图数据库
        if graph_store:
            graph_store.batch_add_entities(result.entities)
            graph_store.batch_add_relationships(result.relationships)
        
        # 存储到 SQLite
        if sqlite_processor:
            for entity in result.entities:
                sqlite_processor.store_entity(entity)
            for relationship in result.relationships:
                sqlite_processor.store_relationship(relationship)
        
        return {
            "success": True,
            "entities_count": len(result.entities),
            "relationships_count": len(result.relationships),
            "errors": result.errors
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
async def query_metadata(request: QueryRequest):
    """
    查询元数据
    
    Args:
        request: 查询请求
        
    Returns:
        查询结果
    """
    if not graph_store:
        raise HTTPException(status_code=500, detail="图数据库未初始化")
    
    try:
        result = graph_store.query(request.query, request.params)
        return {
            "nodes": result.nodes,
            "edges": result.edges,
            "statistics": result.statistics
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/entities")
async def get_entities(
    entity_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """获取实体列表"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite 未初始化")
    
    entities = sqlite_processor.query_entities(
        entity_type=entity_type,
        source=source,
        limit=limit
    )
    return {"entities": entities, "count": len(entities)}


@app.get("/api/relationships")
async def get_relationships(
    source_id: Optional[str] = Query(None),
    target_id: Optional[str] = Query(None),
    relationship_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000)
):
    """获取关系列表"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite 未初始化")
    
    relationships = sqlite_processor.query_relationships(
        source_id=source_id,
        target_id=target_id,
        relationship_type=relationship_type,
        limit=limit
    )
    return {"relationships": relationships, "count": len(relationships)}


@app.get("/api/visualize")
async def visualize_graph(
    entity_id: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    depth: int = Query(1, ge=1, le=5),
    layout: str = Query("spring")
):
    """可视化图数据"""
    api_logger.debug(f"可视化请求: entity_id={entity_id}, entity_type={entity_type}, depth={depth}")
    if not graph_store:
        raise HTTPException(status_code=500, detail="图数据库未初始化")
    
    try:
        # 构建查询 - 使用FalkorDB兼容的语法
        # FalkorDB不支持relationships(path)，需要直接返回节点和关系
        # 确保entity_id和entity_type不是空字符串
        entity_id = entity_id.strip() if entity_id and entity_id.strip() else None
        entity_type = entity_type.strip() if entity_type and entity_type.strip() else None
        
        if entity_id:
            # 转义entity_id中的单引号
            # 对于有entity_id的查询，使用路径查询来获取指定深度的关系
            # 注意：路径查询返回的是路径，graph.py会展开路径中的所有边
            # 路径查询的LIMIT限制的是路径数量，不是边的数量
            # 当depth较大时，需要更大的LIMIT来确保获取足够的路径
            escaped_id = str(entity_id).replace("'", "\\'")
            # 根据深度动态调整LIMIT：深度越大，需要的路径越多
            # 每个路径可能包含多个边，所以需要更大的限制
            limit_value = min(5000, 100 * depth * depth)  # 深度越大，需要的路径越多
            # 使用路径查询，并在RETURN中显式返回关系类型
            # 注意：FalkorDB可能不支持UNWIND，所以我们直接返回路径，然后在解析时提取
            # 对于路径查询，r 是关系列表，需要为每个关系返回类型
            query = f"""
            MATCH path = (n {{id: '{escaped_id}'}})-[r*1..{depth}]-(m)
            RETURN DISTINCT n, r, m
            LIMIT {limit_value}
            """
            # 注意：对于路径查询 [r*1..depth]，r 是关系列表，TYPE(r) 可能不适用
            # 关系类型会从关系对象中提取
            params = {}  # 不使用参数化查询
            api_logger.debug(f"构建 entity_id 查询: depth={depth}, limit={limit_value}")
        elif entity_type:
            # 转义entity_type中的特殊字符
            # 对于entity_type查询，从该类型的所有节点开始，使用路径查询来获取指定深度的关系
            # 根据深度动态调整LIMIT：深度越大，需要的路径越多
            escaped_type = str(entity_type).replace("'", "\\'")
            limit_value = min(5000, 100 * depth * depth)  # 深度越大，需要的路径越多
            # 使用路径查询，并在RETURN中显式返回关系类型
            # 注意：FalkorDB可能不支持UNWIND，所以我们直接返回路径，然后在解析时提取
            # 对于路径查询，r 是关系列表，需要为每个关系返回类型
            query = f"""
            MATCH path = (n:{escaped_type})-[r*1..{depth}]-(m)
            RETURN DISTINCT n, r, m
            LIMIT {limit_value}
            """
            # 注意：对于路径查询 [r*1..depth]，r 是关系列表，TYPE(r) 可能不适用
            # 关系类型会从关系对象中提取
            params = {}
            api_logger.debug(f"构建 entity_type 查询: type={entity_type}, depth={depth}, limit={limit_value}")
        else:
            # 默认查询：返回所有节点和关系
            # 注意：对于默认查询（没有起始节点），深度参数没有意义
            # 应该查询所有直接边，因为无法确定"从哪个节点开始的深度"
            # 使用两个查询分别获取所有节点和所有边，然后组合
            # 这样可以确保获取所有节点（包括孤立节点和只有入边的节点）
            api_logger.debug("构建默认查询（双查询方式）")
            
            # 查询1: 获取所有节点（包括孤立节点）
            nodes_query = """
            MATCH (n)
            RETURN DISTINCT n
            """
            # 查询2: 获取所有直接边（深度参数对默认查询没有意义）
            # 显式返回关系类型，确保能正确提取
            edges_query = """
            MATCH (n)-[r]->(m)
            RETURN DISTINCT n, r, m, TYPE(r) as rel_type
            """
            
            # 执行查询
            nodes_result = graph_store.query(nodes_query, {})
            edges_result = graph_store.query(edges_query, {})
            
            # 组合结果
            from src.core.models import QueryResult
            result = QueryResult()
            result.nodes = nodes_result.nodes
            result.edges = edges_result.edges
            result.statistics = {}
        
        # 对于entity_id和entity_type查询，执行常规查询
        if entity_id or entity_type:
            api_logger.debug(f"执行图查询: entity_id={entity_id}, entity_type={entity_type}")
            result = graph_store.query(query, params)
        
        api_logger.debug(f"查询结果: nodes={len(result.nodes)}, edges={len(result.edges)}")
        
        # 转换为可视化格式
        try:
            visualizer = GraphitiVisualizer()
            visualizer.load_from_query_result(result)
            
            graph_data = visualizer.to_graphiti_format()
            graph_layout = visualizer.get_layout(layout_type=layout)
            
            return {
                "graph": graph_data,
                "layout": graph_layout,
                "statistics": visualizer.get_statistics()
            }
        except Exception as viz_error:
            api_logger.error(f"可视化处理失败: {viz_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"可视化处理失败: {str(viz_error)}")
    
    except Exception as e:
        api_logger.error(f"可视化图数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/statistics")
async def get_statistics():
    """获取统计信息"""
    api_logger.debug("获取统计信息")
    stats = {}
    
    if graph_store:
        graph_stats = graph_store.get_statistics()
        stats["graph"] = graph_stats
    
    if sqlite_processor:
        sqlite_stats = sqlite_processor.get_statistics()
        stats["sqlite"] = sqlite_stats
    
    if duckdb_processor:
        duckdb_stats = duckdb_processor.get_statistics()
        stats["duckdb"] = duckdb_stats
    
    return stats


@app.get("/api/analytics/entity-distribution")
async def get_entity_distribution():
    """获取实体分布分析"""
    if not duckdb_processor:
        raise HTTPException(status_code=500, detail="DuckDB 未初始化")
    
    df = duckdb_processor.analyze_entity_distribution()
    return {"data": df.to_dict('records')}


@app.get("/api/analytics/relationship-patterns")
async def get_relationship_patterns():
    """获取关系模式分析"""
    if not duckdb_processor:
        raise HTTPException(status_code=500, detail="DuckDB 未初始化")
    
    df = duckdb_processor.analyze_relationship_patterns()
    return {"data": df.to_dict('records')}


@app.get("/api/analytics/central-entities")
async def get_central_entities(top_n: int = Query(10, ge=1, le=100)):
    """获取中心实体"""
    if not duckdb_processor:
        raise HTTPException(status_code=500, detail="DuckDB 未初始化")
    
    df = duckdb_processor.find_central_entities(top_n)
    return {"data": df.to_dict('records')}


@app.get("/api/entities/{entity_id}")
async def get_entity_detail(entity_id: str):
    """获取实体详情"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite 未初始化")
    
    entities = sqlite_processor.query_entities(limit=10000)
    entity = next((e for e in entities if e.get('id') == entity_id), None)
    
    if not entity:
        raise HTTPException(status_code=404, detail="实体不存在")
    
    # 获取实体的关系
    relationships = sqlite_processor.query_relationships(
        source_id=entity_id,
        limit=100
    )
    incoming_rels = sqlite_processor.query_relationships(
        target_id=entity_id,
        limit=100
    )
    
    return {
        "entity": entity,
        "outgoing_relationships": relationships,
        "incoming_relationships": incoming_rels
    }


@app.get("/api/entities/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: str,
    direction: Optional[str] = Query("both", regex="^(both|outgoing|incoming)$")
):
    """获取实体的关系"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite 未初始化")
    
    result = {"outgoing": [], "incoming": []}
    
    if direction in ["both", "outgoing"]:
        result["outgoing"] = sqlite_processor.query_relationships(
            source_id=entity_id,
            limit=100
        )
    
    if direction in ["both", "incoming"]:
        result["incoming"] = sqlite_processor.query_relationships(
            target_id=entity_id,
            limit=100
        )
    
    return result


@app.get("/api/search")
async def search_entities(
    q: str = Query(..., description="搜索关键词"),
    entity_type: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500)
):
    """全文搜索实体"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite 未初始化")
    
    # 获取所有实体进行搜索
    entities = sqlite_processor.query_entities(
        entity_type=entity_type,
        source=source,
        limit=10000
    )
    
    # 简单文本匹配搜索
    query_lower = q.lower()
    results = []
    for entity in entities:
        name = entity.get('name', '').lower()
        description = (entity.get('description') or '').lower()
        
        if query_lower in name or query_lower in description:
            results.append(entity)
            if len(results) >= limit:
                break
    
    return {
        "query": q,
        "results": results,
        "count": len(results)
    }


@app.post("/api/entities/batch")
async def batch_get_entities(entity_ids: List[str]):
    """批量获取实体"""
    if not sqlite_processor:
        raise HTTPException(status_code=500, detail="SQLite 未初始化")
    
    entities = sqlite_processor.query_entities(limit=10000)
    results = [e for e in entities if e.get('id') in entity_ids]
    
    return {
        "entities": results,
        "count": len(results),
        "requested": len(entity_ids)
    }


@app.post("/api/sync")
async def sync_data(incremental: bool = False):
    """同步 SQLite 到 DuckDB"""
    if not sqlite_processor or not duckdb_processor:
        raise HTTPException(status_code=500, detail="数据处理器未初始化")
    
    from ..processing.sync import DataSync
    
    sync = DataSync(sqlite_processor, duckdb_processor)
    
    if incremental:
        result = sync.sync_incremental()
    else:
        result = sync.sync_all()
    
    return {
        "success": len(result["errors"]) == 0,
        "stats": result
    }


if __name__ == "__main__":
    import uvicorn
    app_config = get_config()
    uvicorn.run(
        "src.api.server:app",
        host=app_config.api.host,
        port=app_config.api.port,
        reload=app_config.api.debug
    )

