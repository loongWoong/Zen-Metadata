# 采集器元模型文件说明

本目录包含从现有采集器代码生成的元模型文件。这些文件遵循 `GitRepository.yaml` 的格式，定义了实体类型、关系类型和采集器插件。

## 文件列表

### 1. CodeMetadata.yaml
**代码元数据元模型**

- **实体类型**:
  - `CodeProject`: 代码项目/目录
  - `CodeFile`: 源代码文件
  - `CodeClass`: 代码类定义
  - `CodeFunction`: 代码函数/方法
  - `CodeModule`: 被导入的模块

- **关系类型**:
  - `CONTAINS`: 包含关系（项目→文件→类→函数）
  - `IMPORTS`: 导入关系（文件→模块）
  - `INHERITS`: 继承关系（类→类）
  - `IMPLEMENTS`: 实现关系（类→接口）
  - `CALLS`: 调用关系（函数→函数）
  - `BELONGS_TO`: 属于关系

- **采集器插件**: `code_collector.py`
- **配置参数**: `source_path`, `languages`, `exclude_patterns`

### 2. RelationalDatabase.yaml
**关系型数据库元模型**

- **实体类型**:
  - `Database`: 数据库
  - `Table`: 数据表
  - `Column`: 数据列
  - `Index`: 索引

- **关系类型**:
  - `CONTAINS`: 包含关系（数据库→表→列/索引）
  - `REFERENCES`: 引用关系（表/列之间的外键）
  - `BELONGS_TO`: 属于关系

- **采集器插件**: `relational_collector.py`
- **配置参数**: `connection_string`, `type`, `host`, `port`, `database`, `username`, `password`, `schema`

### 3. GraphDatabase.yaml
**图数据库元模型**

- **实体类型**:
  - `GraphDatabase`: 图数据库（Neo4j, FalkorDB等）
  - `NodeLabel`: 节点标签
  - `RelationshipType`: 关系类型

- **关系类型**:
  - `CONTAINS`: 包含关系（数据库→标签/关系类型）
  - `BELONGS_TO`: 属于关系

- **采集器插件**: `graphdb_collector.py`
- **配置参数**: `db_type`, `uri`, `username`, `password`, `host`, `port`, `graph_name`

### 4. FileSystem.yaml
**文件系统元模型**

- **实体类型**:
  - `Directory`: 目录
  - `File`: 文件

- **关系类型**:
  - `CONTAINS`: 包含关系（目录→目录/文件）
  - `BELONGS_TO`: 属于关系（文件→目录）

- **采集器插件**: `filesystem_collector.py`
- **配置参数**: `scan_paths`, `exclude_patterns`, `max_depth`

## 使用方式

### 1. 部署元模型包

将这些YAML文件复制到 `metamodels/` 目录下，系统会自动加载：

```bash
# 创建元模型目录结构
mkdir -p metamodels/code_metadata
mkdir -p metamodels/relational_database
mkdir -p metamodels/graph_database
mkdir -p metamodels/filesystem

# 复制文件
cp CodeMetadata.yaml metamodels/code_metadata/
cp RelationalDatabase.yaml metamodels/relational_database/
cp GraphDatabase.yaml metamodels/graph_database/
cp FileSystem.yaml metamodels/filesystem/
```

### 2. 通过API创建采集任务

```python
# 代码元数据采集
POST /api/tasks/collect
{
    "collector_type": "code_project",  # 或 "code_metadata"
    "config": {
        "source": "my_project",
        "source_path": "/path/to/project",
        "languages": ["python", "javascript"]
    }
}

# 关系型数据库采集
POST /api/tasks/collect
{
    "collector_type": "database",  # 或 "relational"
    "config": {
        "source": "my_db",
        "connection_string": "postgresql://user:pass@host:port/db"
    }
}

# 图数据库采集
POST /api/tasks/collect
{
    "collector_type": "graph_database",  # 或 "graphdb"
    "config": {
        "source": "my_graph",
        "db_type": "neo4j",
        "uri": "bolt://localhost:7687",
        "username": "neo4j",
        "password": "password"
    }
}

# 文件系统采集
POST /api/tasks/collect
{
    "collector_type": "directory",  # 或 "filesystem"
    "config": {
        "source": "my_filesystem",
        "scan_paths": ["/path/to/dir1", "/path/to/dir2"],
        "exclude_patterns": ["__pycache__", ".git"]
    }
}
```

### 3. 直接使用工厂模式

```python
from src.collectors.factory import CollectorFactory
from src.core.metamodel_registry import MetaRegistry

# 加载元模型
meta_registry = MetaRegistry()
meta_registry.load_all()

# 创建工厂
factory = CollectorFactory(meta_registry)

# 创建采集器
collector = factory.create_collector_by_collector_type(
    "code_project",
    "my_source",
    {
        "source_path": "/path/to/project",
        "languages": ["python"]
    }
)

# 执行采集
result = collector.collect()
```

## 注意事项

1. **插件代码**: 每个元模型文件中的 `plugins` 部分包含了采集器插件的代码。这些代码会被自动加载到系统中。

2. **实体类型映射**: 采集器工厂会自动尝试多种命名转换方式，例如：
   - `code_project` → `CodeProject`
   - `relational_database` → `RelationalDatabase`
   - `graph_database` → `GraphDatabase`
   - `filesystem` → `Directory` 或 `FileSystem`

3. **向后兼容**: 现有的硬编码采集器（`relational`, `graphdb`, `code`, `filesystem`）仍然支持，系统会优先尝试从元模型创建采集器。

4. **配置验证**: 每个元模型都定义了 `config_schema`，用于前端表单生成和配置验证。

## 后续工作

1. 将这些文件移动到统一的元模型存储目录
2. 根据实际使用情况调整实体类型和关系类型
3. 完善插件代码，确保与原始采集器功能一致
4. 添加更多质量规则和验证逻辑


