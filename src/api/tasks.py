"""
任务管理 API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus
# #region agent log
import json as json_log
import time
log_path = r"g:\data\Zen metadata\.cursor\debug.log"
# #endregion

from ..core.tasks import TaskManager, Task, TaskStatus, TaskType
from ..core.graph import GraphStore
from ..core.models import CollectionResult
from ..collectors.relational import RelationalDatabaseCollector
from ..collectors.graphdb import GraphDatabaseCollector
from ..collectors.code import CodeMetadataCollector
from ..collectors.filesystem import FileSystemCollector
from ..collectors.factory import CollectorFactory
from ..collectors.task_config import CollectionTaskConfig
from ..processing.sqlite import SQLiteProcessor
from ..processing.duckdb import DuckDBProcessor
from ..processing.sync import DataSync


router = APIRouter(prefix="/api/tasks", tags=["tasks"])

# 全局任务管理器
task_manager: Optional[TaskManager] = None
graph_store: Optional[GraphStore] = None
sqlite_processor: Optional[SQLiteProcessor] = None
duckdb_processor: Optional[DuckDBProcessor] = None
meta_registry = None
collector_factory: Optional[CollectorFactory] = None


def init_task_manager(storage_path: str = "data/tasks.json"):
    """初始化任务管理器"""
    global task_manager
    task_manager = TaskManager(storage_path)
    return task_manager


def set_dependencies(gs: GraphStore, sp: SQLiteProcessor, dp: Optional[DuckDBProcessor] = None, mr = None):
    """设置依赖"""
    global graph_store, sqlite_processor, duckdb_processor, meta_registry, collector_factory
    graph_store = gs
    sqlite_processor = sp
    duckdb_processor = dp
    meta_registry = mr
    # 创建采集器工厂
    if mr:
        collector_factory = CollectorFactory(mr)
    else:
        collector_factory = None


class CollectTaskRequest(BaseModel):
    """采集任务请求"""
    collector_type: str
    config: Dict[str, Any]


async def execute_collect_task(task_id: str, collector_type: str, config: Dict[str, Any], incremental: bool = False):
    """
    执行采集任务
    
    Args:
        task_id: 任务ID
        collector_type: 采集器类型
        config: 配置
        incremental: 是否为增量采集模式（True=增量更新，False=新建任务）
    """
    if not task_manager:
        return
    
    try:
        # 更新状态为运行中
        task_manager.update_task_status(task_id, TaskStatus.RUNNING, "开始采集...")
        
        collector = None
        task_type = None
        
        # 首先尝试使用工厂模式从元模型创建采集器（优先使用元模型定义的collector_type）
        if collector_factory and meta_registry:
            # 检查是否是元模型中定义的采集器类型
            entity_type = meta_registry.get_entity_type_by_collector_type(collector_type)
            if entity_type:
                # 使用元模型定义的实体类型创建采集器
                collector = collector_factory.create_collector(
                    entity_type,
                    config.get("source", collector_type),
                    config
                )
                if collector:
                    task_type = TaskType.COLLECT_METAMODEL
                    task_manager.update_task_progress(task_id, 10.0, f"初始化{collector_type}采集器（元模型，实体类型: {entity_type}）...")
            
            # 如果直接映射失败，尝试使用命名转换方式（向后兼容）
            if not collector:
                collector = collector_factory.create_collector_by_collector_type(
                    collector_type,
                    config.get("source", collector_type),
                    config
                )
                if collector:
                    task_type = TaskType.COLLECT_METAMODEL
                    task_manager.update_task_progress(task_id, 10.0, f"初始化{collector_type}采集器（元模型，命名转换）...")
        
        # 如果工厂模式失败，回退到硬编码的采集器（向后兼容）
        if not collector:
            if collector_type == "relational":
                task_type = TaskType.COLLECT_RELATIONAL
                conn_str = config.get("connection_string")
                if not conn_str:
                    # 从配置构建连接字符串
                    db_type = config.get("type", "postgresql")
                    host = config.get("host", "localhost")
                    port = config.get("port", 5432)
                    database = config.get("database", "")
                    username = config.get("username", "")
                    password = config.get("password", "")
                    
                    # #region agent log
                    try:
                        with open(log_path, 'a', encoding='utf-8') as f:
                            f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"A","location":"tasks.py:execute_collect_task","message":"Building connection string","data":{"db_type":db_type,"host":host,"port":port,"database":database,"username":username,"password_length":len(password) if password else 0,"password_has_at":"@" in password if password else False},"timestamp":int(time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                    
                    # URL 编码用户名和密码，避免特殊字符（如 @）被误解析
                    username_encoded = quote_plus(username)
                    password_encoded = quote_plus(password)
                    
                    # #region agent log
                    try:
                        with open(log_path, 'a', encoding='utf-8') as f:
                            f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"A","location":"tasks.py:execute_collect_task","message":"After URL encoding","data":{"username_encoded":username_encoded,"password_encoded_preview":password_encoded[:20] if len(password_encoded) > 20 else password_encoded},"timestamp":int(time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                    
                    if db_type == "postgresql":
                        conn_str = f"postgresql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
                    elif db_type == "mysql":
                        conn_str = f"mysql+pymysql://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
                    else:
                        conn_str = f"{db_type}://{username_encoded}:{password_encoded}@{host}:{port}/{database}"
                    
                    # #region agent log
                    try:
                        with open(log_path, 'a', encoding='utf-8') as f:
                            f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"A","location":"tasks.py:execute_collect_task","message":"Connection string built","data":{"conn_str_preview":conn_str.split("@")[0] + "@***" if "@" in conn_str else conn_str[:50]},"timestamp":int(time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                
                source = config.get("source", "relational_db")
                # #region agent log
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json_log.dumps({"sessionId":"debug-session","runId":"initial","hypothesisId":"B","location":"tasks.py:execute_collect_task","message":"Creating RelationalDatabaseCollector","data":{"source":source,"has_conn_str":bool(conn_str)},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                collector = RelationalDatabaseCollector(conn_str, source, config)
                task_manager.update_task_progress(task_id, 10.0, "初始化关系型数据库采集器...")
            
            elif collector_type == "graphdb":
                task_type = TaskType.COLLECT_GRAPHDB
                db_type = config.get("db_type")
                conn_config = config.get("connection_config", config)
                source = config.get("source", "graph_db")
                collector = GraphDatabaseCollector(db_type, conn_config, source, config)
                task_manager.update_task_progress(task_id, 10.0, "初始化图数据库采集器...")
            
            elif collector_type == "code":
                task_type = TaskType.COLLECT_CODE
                source_path = config.get("source_path")
                source = config.get("source", "code")
                languages = config.get("languages", ["python"])
                collector = CodeMetadataCollector(source_path, source, languages, config)
                task_manager.update_task_progress(task_id, 10.0, "初始化代码采集器...")
            
            elif collector_type == "filesystem":
                task_type = TaskType.COLLECT_FILESYSTEM
                scan_paths = config.get("scan_paths", [])
                source = config.get("source", "filesystem")
                collector = FileSystemCollector(scan_paths, source, config)
                task_manager.update_task_progress(task_id, 10.0, "初始化文件系统采集器...")
            
            else:
                # 如果都不匹配，抛出错误
                available_collectors = []
                if collector_factory:
                    available_collectors = list(collector_factory.list_available_collectors().keys())
                raise ValueError(
                    f"不支持的采集器类型: {collector_type}。"
                    f"支持的硬编码类型: relational, graphdb, code, filesystem。"
                    f"可用的元模型采集器: {available_collectors}"
                )
        
        # 在线程池中执行采集，避免阻塞事件循环
        task_manager.update_task_progress(task_id, 30.0, "执行采集...")
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            result: CollectionResult = await loop.run_in_executor(executor, collector.collect)
        
        # 存储到图数据库
        if graph_store and result.entities:
            if incremental:
                task_manager.update_task_progress(task_id, 60.0, "增量更新图数据库...")
                entity_count = graph_store.batch_merge_entities(result.entities)
                rel_count = graph_store.batch_merge_relationships(result.relationships)
            else:
                task_manager.update_task_progress(task_id, 60.0, "存储到图数据库...")
                entity_count = graph_store.batch_add_entities(result.entities)
                rel_count = graph_store.batch_add_relationships(result.relationships)
        else:
            entity_count = 0
            rel_count = 0
        
        # 存储到 SQLite
        if sqlite_processor and result.entities:
            if incremental:
                task_manager.update_task_progress(task_id, 80.0, "增量更新SQLite...")
            else:
                task_manager.update_task_progress(task_id, 80.0, "存储到SQLite...")
            for entity in result.entities:
                sqlite_processor.store_entity(entity)  # store_entity 已经使用 INSERT OR REPLACE，支持增量
            for relationship in result.relationships:
                sqlite_processor.store_relationship(relationship, incremental=incremental)
        
        # 同步到 DuckDB
        if duckdb_processor and sqlite_processor and result.entities:
            task_manager.update_task_progress(task_id, 90.0, "同步到DuckDB...")
            try:
                sync = DataSync(sqlite_processor, duckdb_processor)
                sync_result = sync.sync_incremental()  # 使用增量同步，只同步新数据
                # #region agent log
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json_log.dumps({"sessionId":"debug-session","runId":"duckdb-sync","hypothesisId":"H","location":"tasks.py:execute_collect_task","message":"DuckDB sync completed","data":{"entities_synced":sync_result.get("entities_synced",0),"relationships_synced":sync_result.get("relationships_synced",0),"errors_count":len(sync_result.get("errors",[]))},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
            except Exception as sync_err:
                # #region agent log
                try:
                    with open(log_path, 'a', encoding='utf-8') as f:
                        f.write(json_log.dumps({"sessionId":"debug-session","runId":"duckdb-sync","hypothesisId":"H","location":"tasks.py:execute_collect_task","message":"DuckDB sync failed","data":{"error":str(sync_err)},"timestamp":int(time.time()*1000)})+"\n")
                except: pass
                # #endregion
                # 同步失败不影响任务完成，只记录错误
                pass
        
        # 完成任务
        task_manager.update_task_progress(task_id, 100.0, "采集完成")
        task_manager.set_task_result(task_id, {
            "entities_count": len(result.entities),
            "relationships_count": len(result.relationships),
            "stored_entities": entity_count,
            "stored_relationships": rel_count,
            "errors": result.errors
        })
        task_manager.update_task_status(task_id, TaskStatus.COMPLETED, "采集完成")
        
    except Exception as e:
        error_msg = str(e)
        task_manager.update_task_status(
            task_id, 
            TaskStatus.FAILED, 
            error=error_msg
        )


@router.post("/collect")
async def create_collect_task(request: CollectTaskRequest, background_tasks: BackgroundTasks):
    """
    创建采集任务
    
    Args:
        request: 采集请求
        background_tasks: 后台任务
        
    Returns:
        任务信息
    """
    if not task_manager:
        raise HTTPException(status_code=500, detail="任务管理器未初始化")
    
    # 首先尝试从元模型注册表获取采集器类型
    task_type = None
    if meta_registry:
        # 检查是否是元模型中定义的采集器类型
        entity_type = meta_registry.get_entity_type_by_collector_type(request.collector_type)
        if entity_type:
            # 验证采集器是否存在
            if collector_factory:
                test_collector = collector_factory.create_collector(
                    entity_type,
                    request.config.get("source", request.collector_type),
                    request.config
                )
                if test_collector:
                    task_type = TaskType.COLLECT_METAMODEL
    
    # 如果不是元模型类型，回退到硬编码的类型（向后兼容）
    if not task_type:
        task_type_map = {
            "relational": TaskType.COLLECT_RELATIONAL,
            "graphdb": TaskType.COLLECT_GRAPHDB,
            "code": TaskType.COLLECT_CODE,
            "filesystem": TaskType.COLLECT_FILESYSTEM
        }
        task_type = task_type_map.get(request.collector_type)
    
    # 如果仍然没有找到，尝试使用工厂模式查找（兼容旧方式）
    if not task_type:
        if collector_factory:
            # 尝试创建采集器以验证是否存在
            test_collector = collector_factory.create_collector_by_collector_type(
                request.collector_type,
                request.config.get("source", request.collector_type),
                request.config
            )
            if test_collector:
                task_type = TaskType.COLLECT_METAMODEL
            else:
                # 列出所有可用的采集器类型
                available_collector_types = meta_registry.list_collector_types() if meta_registry else []
                available_types = [ct["collector_type"] for ct in available_collector_types]
                raise HTTPException(
                    status_code=400, 
                    detail=f"不支持的采集器类型: {request.collector_type}。可用的采集器类型: {available_types}"
                )
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的采集器类型: {request.collector_type}，且元模型注册表未初始化"
            )
    
    # 创建任务（对于元模型采集器，在配置中保存collector_type以便后续使用）
    task_config = request.config.copy()
    if task_type == TaskType.COLLECT_METAMODEL:
        task_config["collector_type"] = request.collector_type
    
    task = task_manager.create_task(task_type, task_config)
    
    # 添加到后台任务
    background_tasks.add_task(
        execute_collect_task,
        task.id,
        request.collector_type,
        request.config
    )
    
    return {
        "task_id": task.id,
        "status": task.status,
        "created_at": task.created_at.isoformat()
    }


@router.get("/{task_id}")
async def get_task(task_id: str):
    """
    获取任务信息
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务信息
    """
    if not task_manager:
        raise HTTPException(status_code=500, detail="任务管理器未初始化")
    
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "id": task.id,
        "type": task.type,
        "status": task.status,
        "progress": task.progress,
        "message": task.message,
        "result": task.result,
        "error": task.error,
        "config": task.config,
        "created_at": task.created_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None
    }


@router.get("/{task_id}/progress")
async def get_task_progress(task_id: str):
    """
    获取任务进度
    
    Args:
        task_id: 任务ID
        
    Returns:
        任务进度信息
    """
    if not task_manager:
        raise HTTPException(status_code=500, detail="任务管理器未初始化")
    
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "message": task.message
    }


@router.get("")
async def list_tasks(
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    limit: int = 100
):
    """
    列出任务
    
    Args:
        status: 状态过滤
        task_type: 任务类型过滤
        limit: 限制数量
        
    Returns:
        任务列表
    """
    if not task_manager:
        raise HTTPException(status_code=500, detail="任务管理器未初始化")
    
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status)
        except ValueError:
            pass
    
    type_enum = None
    if task_type:
        try:
            type_enum = TaskType(task_type)
        except ValueError:
            pass
    
    tasks = task_manager.list_tasks(status_enum, type_enum, limit)
    
    return {
        "tasks": [
            {
                "id": task.id,
                "type": task.type,
                "status": task.status,
                "progress": task.progress,
                "message": task.message,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None
            }
            for task in tasks
        ],
        "count": len(tasks)
    }


@router.put("/{task_id}")
async def update_task(task_id: str, request: CollectTaskRequest):
    """
    更新任务配置
    
    Args:
        task_id: 任务ID
        request: 更新请求
        
    Returns:
        更新结果
    """
    if not task_manager:
        raise HTTPException(status_code=500, detail="任务管理器未初始化")
    
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 不能更新运行中的任务
    if task.status == TaskStatus.RUNNING:
        raise HTTPException(status_code=400, detail="不能更新运行中的任务")
    
    # 构建配置
    config = request.config
    success = task_manager.update_task_config(task_id, config)
    
    if not success:
        raise HTTPException(status_code=400, detail="更新任务失败")
    
    return {"success": True, "message": "任务已更新"}


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        删除结果
    """
    if not task_manager:
        raise HTTPException(status_code=500, detail="任务管理器未初始化")
    
    success = task_manager.delete_task(task_id)
    if not success:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {"success": True, "message": "任务已删除"}


@router.post("/{task_id}/rerun")
async def rerun_task(task_id: str, background_tasks: BackgroundTasks):
    """
    重跑任务（增量采集模式）
    
    Args:
        task_id: 任务ID
        background_tasks: 后台任务
        
    Returns:
        重跑结果
    """
    try:
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Rerun task request","data":{"task_id":task_id},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        
        if not task_manager:
            error_msg = "任务管理器未初始化"
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Task manager not initialized","data":{"error":error_msg},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            raise HTTPException(status_code=500, detail=error_msg)
        
        task = task_manager.get_task(task_id)
        if not task:
            error_msg = f"任务不存在: {task_id}"
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Task not found","data":{"error":error_msg,"task_id":task_id},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            raise HTTPException(status_code=404, detail=error_msg)
        
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Task found","data":{"task_id":task_id,"task_type":task.type,"task_status":task.status,"has_config":bool(task.config),"config_keys":list(task.config.keys()) if task.config else []},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        
        # 只能重跑已完成或失败的任务
        if task.status == TaskStatus.RUNNING:
            error_msg = "任务正在运行中，无法重跑"
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Task is running","data":{"error":error_msg,"task_id":task_id,"task_status":task.status},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            raise HTTPException(status_code=400, detail=error_msg)
        
        if task.status == TaskStatus.PENDING:
            error_msg = "任务尚未运行，请使用启动功能"
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Task is pending","data":{"error":error_msg,"task_id":task_id,"task_status":task.status},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 检查任务配置
        if not task.config:
            error_msg = "任务配置不存在，无法重跑"
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Task config missing","data":{"error":error_msg,"task_id":task_id,"task_type":task.type},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            raise HTTPException(status_code=400, detail=error_msg)
        
        # 确定采集器类型
        type_map = {
            TaskType.COLLECT_RELATIONAL: "relational",
            TaskType.COLLECT_GRAPHDB: "graphdb",
            TaskType.COLLECT_CODE: "code",
            TaskType.COLLECT_FILESYSTEM: "filesystem",
            TaskType.COLLECT_METAMODEL: None  # 元模型采集器需要从配置中获取
        }
        
        collector_type = type_map.get(task.type)
        
        # 如果是元模型采集器，从配置中获取采集器类型
        if task.type == TaskType.COLLECT_METAMODEL:
            collector_type = task.config.get("collector_type")
            if not collector_type:
                # 尝试从其他可能的字段获取
                collector_type = task.config.get("collectorType") or task.config.get("type")
                if not collector_type:
                    error_msg = f"元模型采集任务缺少collector_type配置。任务类型: {task.type}, 配置键: {list(task.config.keys())}"
                    # #region agent log
                    try:
                        with open(log_path, 'a', encoding='utf-8') as f:
                            f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Collector type missing","data":{"error":error_msg,"task_id":task_id,"task_type":task.type,"config_keys":list(task.config.keys())},"timestamp":int(time.time()*1000)})+"\n")
                    except: pass
                    # #endregion
                    raise HTTPException(status_code=400, detail=error_msg)
        elif not collector_type:
            error_msg = f"不支持的任务类型: {task.type}。支持的类型: {list(type_map.keys())}"
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Unsupported task type","data":{"error":error_msg,"task_id":task_id,"task_type":task.type,"supported_types":list(type_map.keys())},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            raise HTTPException(status_code=400, detail=error_msg)
        
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Collector type determined","data":{"task_id":task_id,"collector_type":collector_type,"task_type":task.type},"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        
        # 重置任务状态为pending，准备重新运行
        task_manager.update_task_status(task_id, TaskStatus.PENDING, "准备重新运行...")
        task_manager.update_task_progress(task_id, 0.0, "准备重新运行...")
        
        # 添加到后台任务，使用增量模式
        try:
            background_tasks.add_task(
                execute_collect_task,
                task_id,  # 使用原任务ID，不创建新任务
                collector_type,
                task.config,
                True  # incremental=True，增量采集模式
            )
            # #region agent log
            try:
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Background task added","data":{"task_id":task_id,"collector_type":collector_type},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
        except Exception as e:
            # 如果添加后台任务失败，恢复任务状态
            error_msg = f"启动重跑失败: {str(e)}"
            task_manager.update_task_status(task_id, TaskStatus.FAILED, error_msg)
            # #region agent log
            try:
                import traceback
                with open(log_path, 'a', encoding='utf-8') as f:
                    f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Background task add failed","data":{"error":error_msg,"task_id":task_id,"traceback":traceback.format_exc()},"timestamp":int(time.time()*1000)})+"\n")
            except: pass
            # #endregion
            raise HTTPException(status_code=500, detail=error_msg)
        
        return {
            "success": True,
            "message": "任务已开始重新运行（增量采集模式）",
            "task_id": task_id,
            "collector_type": collector_type
        }
    except HTTPException:
        # 重新抛出HTTP异常，保持原有错误信息
        raise
    except Exception as e:
        # 捕获所有其他异常，记录详细信息
        import traceback
        error_msg = f"重跑任务时发生未预期的错误: {str(e)}"
        error_detail = {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": traceback.format_exc(),
            "task_id": task_id
        }
        # #region agent log
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(json_log.dumps({"sessionId":"debug-session","runId":"rerun-task","hypothesisId":"R","location":"tasks.py:rerun_task","message":"Unexpected error","data":error_detail,"timestamp":int(time.time()*1000)})+"\n")
        except: pass
        # #endregion
        raise HTTPException(status_code=500, detail=f"{error_msg}\n详细信息: {traceback.format_exc()}")

