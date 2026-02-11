# Zen Metadata 项目功能实现逻辑分析文档

## 1. 项目概述

Zen Metadata 是一个基于图数据库的统一元数据管理系统，旨在实现万事万物的元数据统一管理，支撑大模型进行语义理解和交互。系统采用前后端分离架构，提供完整的元数据采集、存储、查询、分析和可视化能力。

### 1.1 核心设计理念

- **统一性**：所有元数据统一表示为实体（Entity）和关系（Relationship）
- **可扩展性**：采用插件化采集器架构，易于添加新的数据源
- **多存储支持**：同时支持图数据库（FalkorDB）、关系型数据库（SQLite）和分析型数据库（DuckDB）
- **语义化**：支持丰富的元数据类型和关系类型，为LLM提供结构化语义信息

## 2. 系统架构

### 2.1 整体架构图

```plantuml
@startuml 系统整体架构
!theme plain
skinparam componentStyle rectangle

package "前端层" {
  [React前端应用] as Frontend
  [ReactFlow可视化] as ReactFlow
  [Ant Design UI] as AntD
}

package "API服务层" {
  [FastAPI服务] as FastAPI
  [RESTful API] as REST
  [WebSocket服务] as WS
  [任务管理API] as TaskAPI
}

package "业务逻辑层" {
  [采集器管理器] as CollectorMgr
  [数据转换器] as Transformer
  [查询处理器] as QueryProcessor
  [可视化处理器] as Visualizer
}

package "采集器层" {
  [关系型数据库采集器] as RelationalCollector
  [图数据库采集器] as GraphDBCollector
  [代码元数据采集器] as CodeCollector
  [文件系统采集器] as FSCollector
}

package "数据存储层" {
  database "FalkorDB\n(图数据库)" as FalkorDB
  database "SQLite\n(关系型数据库)" as SQLite
  database "DuckDB\n(分析型数据库)" as DuckDB
}

Frontend --> FastAPI : HTTP/WebSocket
FastAPI --> REST
FastAPI --> WS
FastAPI --> TaskAPI
FastAPI --> CollectorMgr
FastAPI --> QueryProcessor
FastAPI --> Visualizer

CollectorMgr --> RelationalCollector
CollectorMgr --> GraphDBCollector
CollectorMgr --> CodeCollector
CollectorMgr --> FSCollector

RelationalCollector --> Transformer
GraphDBCollector --> Transformer
CodeCollector --> Transformer
FSCollector --> Transformer

Transformer --> FalkorDB
Transformer --> SQLite
SQLite --> DuckDB : 数据同步

QueryProcessor --> FalkorDB
QueryProcessor --> SQLite
QueryProcessor --> DuckDB

Visualizer --> QueryProcessor

@enduml
```

### 2.2 分层架构说明

系统采用经典的分层架构设计：

1. **展示层**：React + TypeScript 前端应用，提供用户交互界面
2. **API服务层**：FastAPI 提供 RESTful API 和 WebSocket 实时通信
3. **业务逻辑层**：处理采集、转换、查询、可视化等核心业务逻辑
4. **采集器层**：可扩展的采集器框架，支持多种数据源
5. **数据存储层**：多数据库支持，满足不同场景需求

## 3. 核心数据模型

### 3.1 数据模型类图

```plantuml
@startuml 核心数据模型
!theme plain
skinparam classAttributeIconSize 0

class MetadataType {
  + DATABASE
  + TABLE
  + COLUMN
  + FUNCTION
  + CLASS
  + FILE
  + DIRECTORY
  + PACKAGE
  + MODULE
  + SCHEMA
  + INDEX
  + CONSTRAINT
}

class RelationshipType {
  + CONTAINS
  + DEPENDS_ON
  + REFERENCES
  + IMPLEMENTS
  + INHERITS
  + CALLS
  + IMPORTS
  + USES
  + BELONGS_TO
  + RELATED_TO
}

class MetadataEntity {
  - id: str
  - type: MetadataType
  - name: str
  - description: Optional[str]
  - properties: Dict[str, Any]
  - source: str
  - created_at: datetime
  - updated_at: datetime
}

class MetadataRelationship {
  - source_id: str
  - target_id: str
  - type: RelationshipType
  - properties: Dict[str, Any]
  - created_at: datetime
}

class CollectionResult {
  - entities: List[MetadataEntity]
  - relationships: List[MetadataRelationship]
  - metadata: Dict[str, Any]
  - errors: List[str]
}

class QueryResult {
  - nodes: List[Dict[str, Any]]
  - edges: List[Dict[str, Any]]
  - statistics: Dict[str, Any]
}

MetadataEntity "1" --> "*" MetadataRelationship : source
MetadataEntity "1" --> "*" MetadataRelationship : target
CollectionResult "1" --> "*" MetadataEntity
CollectionResult "1" --> "*" MetadataRelationship
QueryResult "1" --> "*" MetadataEntity : contains
QueryResult "1" --> "*" MetadataRelationship : contains

@enduml
```

### 3.2 数据模型说明

- **MetadataEntity（元数据实体）**：表示系统中的各种元数据对象，如数据库、表、函数、文件等
- **MetadataRelationship（元数据关系）**：表示实体之间的关系，如包含、依赖、引用等
- **CollectionResult（采集结果）**：采集器返回的结果，包含实体列表和关系列表
- **QueryResult（查询结果）**：图查询返回的结果，包含节点、边和统计信息

## 4. 采集器架构

### 4.1 采集器类图

```plantuml
@startuml 采集器架构
!theme plain
skinparam classAttributeIconSize 0

abstract class BaseCollector {
  # name: str
  # source: str
  # config: Dict[str, Any]
  # collected_at: datetime
  + collect()*: CollectionResult
  + generate_id(*parts: str): str
  + create_entity(...): MetadataEntity
  + create_relationship(...): MetadataRelationship
  + validate_config(required_keys: list): bool
  + get_config(key: str, default: Any): Any
}

class RelationalDatabaseCollector {
  - connection_string: str
  - engine: Engine
  - inspector: Inspector
  + collect(): CollectionResult
  - _collect_databases(): List[MetadataEntity]
  - _collect_tables(database_id: str): List[MetadataEntity]
  - _collect_columns(table_id: str): List[MetadataEntity]
  - _collect_indexes(table_id: str): List[MetadataEntity]
  - _collect_foreign_keys(table_id: str): List[MetadataRelationship]
}

class GraphDatabaseCollector {
  - db_type: str
  - connection_config: Dict
  - driver: Any
  + collect(): CollectionResult
  - _collect_nodes(): List[MetadataEntity]
  - _collect_relationships(): List[MetadataRelationship]
  - _collect_labels(): List[str]
  - _collect_relationship_types(): List[str]
}

class CodeMetadataCollector {
  - source_path: str
  - languages: List[str]
  - parsers: Dict[str, Parser]
  + collect(): CollectionResult
  - _collect_files(): List[MetadataEntity]
  - _collect_modules(file_id: str): List[MetadataEntity]
  - _collect_classes(module_id: str): List[MetadataEntity]
  - _collect_functions(module_id: str): List[MetadataEntity]
  - _collect_imports(module_id: str): List[MetadataRelationship]
  - _parse_file(file_path: str, language: str): AST
}

class FileSystemCollector {
  - scan_paths: List[str]
  - exclude_patterns: List[str]
  + collect(): CollectionResult
  - _scan_directory(path: str): List[MetadataEntity]
  - _collect_file_metadata(file_path: str): MetadataEntity
  - _collect_directory_metadata(dir_path: str): MetadataEntity
  - _should_exclude(path: str): bool
}

BaseCollector <|-- RelationalDatabaseCollector
BaseCollector <|-- GraphDatabaseCollector
BaseCollector <|-- CodeMetadataCollector
BaseCollector <|-- FileSystemCollector

@enduml
```

### 4.2 采集器工作流程

```plantuml
@startuml 采集器工作流程
!theme plain
start

:初始化采集器;
:验证配置;

if (采集器类型?) then (关系型数据库)
  :连接数据库;
  :采集数据库元数据;
  :采集表元数据;
  :采集列元数据;
  :采集索引和约束;
  :采集外键关系;
elseif (图数据库) then
  :连接图数据库;
  :采集节点标签;
  :采集节点数据;
  :采集关系类型;
  :采集关系数据;
elseif (代码) then
  :扫描代码文件;
  :解析AST;
  :提取模块信息;
  :提取类和函数;
  :提取导入关系;
elseif (文件系统) then
  :扫描目录;
  :收集文件元数据;
  :收集目录结构;
  :建立包含关系;
endif

:创建实体列表;
:创建关系列表;
:构建CollectionResult;
:返回结果;

stop

@enduml
```

## 5. 数据存储架构

### 5.1 存储层类图

```plantuml
@startuml 数据存储架构
!theme plain
skinparam classAttributeIconSize 0

class GraphStore {
  - db: FalkorDB
  - graph: Graph
  - graph_name: str
  + __init__(host, port, password, graph_name)
  + add_entity(entity: MetadataEntity): bool
  + add_relationship(rel: MetadataRelationship): bool
  + batch_add_entities(entities: List): int
  + batch_add_relationships(rels: List): int
  + merge_entity(entity: MetadataEntity): bool
  + merge_relationship(rel: MetadataRelationship): bool
  + query(cypher_query: str, params: Dict): QueryResult
  + find_entity(entity_id: str): Optional[Dict]
  + get_entity_relationships(entity_id: str): QueryResult
  + delete_entity(entity_id: str): bool
  + get_statistics(): Dict[str, Any]
  + close()
}

class SQLiteProcessor {
  - database_path: Path
  - conn: Connection
  + __init__(database_path: str)
  + store_entity(entity: MetadataEntity): bool
  + store_relationship(rel: MetadataRelationship, incremental: bool): bool
  + query_entities(...): List[Dict]
  + query_relationships(...): List[Dict]
  + get_statistics(): Dict[str, Any]
  + close()
  - _init_schema()
}

class DuckDBProcessor {
  - database_path: Optional[Path]
  - conn: Connection
  + __init__(database_path: Optional[str])
  + load_from_sqlite(sqlite_path: str)
  + analyze_entity_distribution(): DataFrame
  + analyze_relationship_patterns(): DataFrame
  + find_central_entities(top_n: int): DataFrame
  + get_statistics(): Dict[str, Any]
  + close()
  - _init_schema()
}

class DataSync {
  - sqlite_processor: SQLiteProcessor
  - duckdb_processor: DuckDBProcessor
  + sync_all(): Dict[str, Any]
  + sync_incremental(): Dict[str, Any]
  - _sync_entities(): int
  - _sync_relationships(): int
}

GraphStore --> FalkorDB : 使用
SQLiteProcessor --> SQLite : 使用
DuckDBProcessor --> DuckDB : 使用
DataSync --> SQLiteProcessor : 读取
DataSync --> DuckDBProcessor : 写入

@enduml
```

### 5.2 数据存储流程

```plantuml
@startuml 数据存储流程
!theme plain

start

:采集器返回CollectionResult;

:存储到FalkorDB图数据库;
note right
  使用Cypher查询语言
  支持实体和关系的创建
  支持MERGE操作（增量更新）
end note

:存储到SQLite关系型数据库;
note right
  使用INSERT OR REPLACE
  支持增量更新
  提供索引优化查询
end note

if (需要同步?) then (是)
  :同步到DuckDB分析数据库;
  note right
    从SQLite读取数据
    写入DuckDB
    支持增量同步
  end note
else (否)
endif

stop

@enduml
```

## 6. API服务架构

### 6.1 API服务类图

```plantuml
@startuml API服务架构
!theme plain
skinparam classAttributeIconSize 0

class FastAPI {
  + app: FastAPI
  + graph_store: GraphStore
  + sqlite_processor: SQLiteProcessor
  + duckdb_processor: DuckDBProcessor
  + startup_event()
  + shutdown_event()
}

class ServerEndpoints {
  + root(): Dict
  + collect_metadata(request: CollectRequest): Dict
  + query_metadata(request: QueryRequest): Dict
  + get_entities(...): Dict
  + get_relationships(...): Dict
  + visualize_graph(...): Dict
  + get_statistics(): Dict
  + get_entity_distribution(): Dict
  + get_relationship_patterns(): Dict
  + get_central_entities(top_n: int): Dict
  + get_entity_detail(entity_id: str): Dict
  + search_entities(...): Dict
  + sync_data(incremental: bool): Dict
}

class TaskRouter {
  + create_collect_task(...): Dict
  + get_task(task_id: str): Dict
  + get_task_progress(task_id: str): Dict
  + list_tasks(...): Dict
  + update_task(...): Dict
  + delete_task(task_id: str): Dict
  + rerun_task(task_id: str): Dict
}

class ExportRouter {
  + export_json(...): Response
  + export_csv(...): Response
  + export_graphml(...): Response
}

class WebSocketRouter {
  + websocket_endpoint(websocket: WebSocket)
  + broadcast_task_update(task_id: str, update: Dict)
}

class TaskManager {
  - storage_path: Path
  - tasks: Dict[str, Task]
  + create_task(type: TaskType, config: Dict): Task
  + get_task(task_id: str): Optional[Task]
  + update_task_status(task_id: str, status: TaskStatus, message: str)
  + update_task_progress(task_id: str, progress: float, message: str)
  + set_task_result(task_id: str, result: Dict)
  + list_tasks(...): List[Task]
  + delete_task(task_id: str): bool
  - _load_tasks()
  - _save_tasks()
}

FastAPI --> ServerEndpoints
FastAPI --> TaskRouter
FastAPI --> ExportRouter
FastAPI --> WebSocketRouter
TaskRouter --> TaskManager
WebSocketRouter --> TaskManager

@enduml
```

### 6.2 API请求处理流程

```plantuml
@startuml API请求处理流程
!theme plain

start

:接收HTTP请求;

if (请求类型?) then (采集请求)
  :创建采集任务;
  :后台执行采集;
  :返回任务ID;
elseif (查询请求) then
  :解析查询参数;
  :执行图查询;
  :返回查询结果;
elseif (可视化请求) then
  :构建Cypher查询;
  :执行查询;
  :转换为可视化格式;
  :返回图形数据;
elseif (任务管理) then
  :操作任务管理器;
  :更新任务状态;
  :返回任务信息;
elseif (WebSocket) then
  :建立WebSocket连接;
  :监听任务更新;
  :推送实时状态;
endif

stop

@enduml
```

## 7. 任务管理系统

### 7.1 任务管理类图

```plantuml
@startuml 任务管理系统
!theme plain
skinparam classAttributeIconSize 0

enum TaskStatus {
  PENDING
  RUNNING
  COMPLETED
  FAILED
  CANCELLED
}

enum TaskType {
  COLLECT_RELATIONAL
  COLLECT_GRAPHDB
  COLLECT_CODE
  COLLECT_FILESYSTEM
  SYNC_DATA
  EXPORT_DATA
}

class Task {
  - id: str
  - type: TaskType
  - status: TaskStatus
  - config: Dict[str, Any]
  - progress: float
  - message: Optional[str]
  - result: Optional[Dict[str, Any]]
  - error: Optional[str]
  - created_at: datetime
  - started_at: Optional[datetime]
  - completed_at: Optional[datetime]
}

class TaskManager {
  - storage_path: Path
  - tasks: Dict[str, Task]
  + create_task(type: TaskType, config: Dict): Task
  + get_task(task_id: str): Optional[Task]
  + update_task_status(task_id: str, status: TaskStatus, message: str)
  + update_task_progress(task_id: str, progress: float, message: str)
  + set_task_result(task_id: str, result: Dict)
  + list_tasks(status, type, limit): List[Task]
  + delete_task(task_id: str): bool
  + update_task_config(task_id: str, config: Dict): bool
  - _load_tasks()
  - _save_tasks()
}

Task --> TaskStatus
Task --> TaskType
TaskManager "1" --> "*" Task : 管理

@enduml
```

### 7.2 任务执行流程

```plantuml
@startuml 任务执行流程
!theme plain

start

:创建采集任务;
:任务状态: PENDING;

:后台任务启动;
:任务状态: RUNNING;
:进度: 0%;

:初始化采集器;
:进度: 10%;

:执行采集;
:进度: 30%;

if (采集成功?) then (是)
  :存储到FalkorDB;
  :进度: 60%;
  
  :存储到SQLite;
  :进度: 80%;
  
  :同步到DuckDB;
  :进度: 90%;
  
  :任务状态: COMPLETED;
  :进度: 100%;
  :保存任务结果;
else (否)
  :任务状态: FAILED;
  :记录错误信息;
endif

:通知WebSocket客户端;

stop

@enduml
```

## 8. 数据查询与分析

### 8.1 查询处理流程

```plantuml
@startuml 查询处理流程
!theme plain

start

:接收查询请求;

if (查询类型?) then (Cypher图查询)
  :构建Cypher查询语句;
  :执行FalkorDB查询;
  :解析查询结果;
  :提取节点和边;
  :返回QueryResult;
elseif (SQL关系查询) then
  :构建SQL查询;
  :执行SQLite查询;
  :返回实体/关系列表;
elseif (分析查询) then
  :构建分析SQL;
  :执行DuckDB查询;
  :返回分析结果DataFrame;
elseif (可视化查询) then
  :构建路径查询;
  :执行图查询;
  :转换为可视化格式;
  :应用布局算法;
  :返回图形数据;
endif

stop

@enduml
```

### 8.2 分析功能

系统提供以下分析功能：

1. **实体分布分析**：统计各类型实体的数量和分布
2. **关系模式分析**：分析不同类型关系的使用频率和模式
3. **中心实体发现**：找出连接度最高的实体（度中心性）

## 9. 前端架构

### 9.1 前端组件结构

```plantuml
@startuml 前端组件架构
!theme plain
skinparam componentStyle rectangle

package "前端应用" {
  [App.tsx] as App
  [MainLayout] as Layout
}

package "页面组件" {
  [Dashboard] as Dashboard
  [GraphView] as GraphView
  [EntityBrowser] as EntityBrowser
  [Collection] as Collection
  [Analytics] as Analytics
}

package "共享组件" {
  [ForceDirectedGraph] as GraphComponent
}

package "服务层" {
  [API Service] as APIService
  [WebSocket Service] as WSService
}

package "状态管理" {
  [Zustand Store] as Store
}

App --> Layout
Layout --> Dashboard
Layout --> GraphView
Layout --> EntityBrowser
Layout --> Collection
Layout --> Analytics

GraphView --> GraphComponent
Dashboard --> APIService
GraphView --> APIService
EntityBrowser --> APIService
Collection --> APIService
Analytics --> APIService

Collection --> WSService
GraphView --> WSService

APIService --> Store
WSService --> Store

@enduml
```

### 9.2 前端数据流

```plantuml
@startuml 前端数据流
!theme plain

start

:用户操作;

if (操作类型?) then (创建采集任务)
  :调用API创建任务;
  :建立WebSocket连接;
  :监听任务状态更新;
  :更新UI显示;
elseif (查询元数据) then
  :调用查询API;
  :接收查询结果;
  :更新状态管理;
  :渲染组件;
elseif (可视化图谱) then
  :调用可视化API;
  :接收图形数据;
  :应用布局算法;
  :渲染图形;
elseif (查看分析) then
  :调用分析API;
  :接收分析数据;
  :生成图表;
  :显示统计信息;
endif

stop

@enduml
```

## 10. 关键技术实现

### 10.1 图数据库操作

系统使用FalkorDB作为图数据库，主要特点：

- 使用Cypher查询语言
- 支持节点和关系的创建、查询、更新、删除
- 支持MERGE操作实现增量更新
- 自动处理属性类型转换（复杂类型转为JSON字符串）

### 10.2 数据同步机制

系统实现了SQLite到DuckDB的数据同步：

- **全量同步**：首次同步所有数据
- **增量同步**：只同步新增或更新的数据
- 使用时间戳判断数据变更

### 10.3 任务管理

- 任务状态持久化到JSON文件
- 支持任务进度实时更新
- WebSocket推送任务状态变更
- 支持任务重跑（增量采集模式）

### 10.4 可视化处理

- 使用Graphiti进行图形可视化
- 支持多种布局算法（spring, force-directed等）
- 支持子图提取和类型过滤
- 前端使用ReactFlow渲染交互式图形

## 11. 系统扩展点

### 11.1 添加新采集器

1. 继承`BaseCollector`基类
2. 实现`collect()`方法
3. 返回`CollectionResult`对象
4. 在API中注册新的采集器类型

### 11.2 添加新存储后端

1. 实现存储接口（参考`GraphStore`、`SQLiteProcessor`）
2. 实现CRUD操作
3. 在启动时初始化存储实例
4. 在API中使用新的存储后端

### 11.3 添加新分析功能

1. 在`DuckDBProcessor`中添加分析方法
2. 在API中添加对应的端点
3. 在前端添加可视化组件

## 12. 性能优化策略

### 12.1 批量操作

- 使用批量插入减少数据库交互
- 批量添加实体和关系

### 12.2 索引优化

- 在常用查询字段上创建索引
- 图数据库自动索引节点和关系

### 12.3 缓存策略

- 缓存常用查询结果
- 缓存统计信息

### 12.4 异步处理

- 长时间运行的采集任务使用后台任务
- WebSocket实时推送任务状态

## 13. 总结

Zen Metadata系统通过以下方式实现了统一元数据管理：

1. **统一的数据模型**：所有元数据统一表示为实体和关系
2. **可扩展的采集器架构**：易于添加新的数据源
3. **多存储支持**：满足不同场景的查询和分析需求
4. **完整的API服务**：提供RESTful API和WebSocket实时通信
5. **丰富的可视化**：支持交互式图谱展示和分析

系统设计遵循了可扩展性、统一性和语义化的核心原则，为元数据管理和LLM集成提供了坚实的基础。

