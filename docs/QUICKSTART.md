# 快速开始指南

## 1. 环境准备

### 1.1 Python 环境
确保 Python 3.10 或更高版本已安装：
```bash
python --version
```

### 1.2 安装依赖
```bash
pip install -r requirements.txt
```

### 1.3 安装 FalkorDB
FalkorDB 基于 Redis，需要先安装 Redis：

**Windows:**
- 下载 Redis for Windows 或使用 WSL
- 或使用 Docker: `docker run -d -p 6379:6379 redis/redis-stack`

**Linux/Mac:**
```bash
# 使用 Docker
docker run -d -p 6379:6379 redis/redis-stack

# 或安装 Redis
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis  # Mac
```

然后安装 FalkorDB Python 客户端：
```bash
pip install falkordb
```

## 2. 配置

编辑 `config/config.yaml` 文件，配置数据库连接和采集器：

```yaml
falkordb:
  host: localhost
  port: 6379
  password: ""
  graph_name: "zen_metadata"

sqlite:
  database: "data/zen_metadata.db"

duckdb:
  database: "data/zen_metadata_analytics.duckdb"
```

## 3. 启动服务

### 3.1 启动 API 服务
```bash
python run.py
```

或直接使用 uvicorn:
```bash
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

### 3.2 访问 API 文档
打开浏览器访问: http://localhost:8000/docs

## 4. 使用示例

### 4.1 采集文件系统元数据

使用 Python:
```python
from src.collectors.filesystem import FileSystemCollector
from src.core.graph import GraphStore

# 创建采集器
collector = FileSystemCollector(
    scan_paths=["/path/to/scan"],
    source="my_filesystem"
)

# 执行采集
result = collector.collect()

# 存储到图数据库
graph_store = GraphStore()
graph_store.batch_add_entities(result.entities)
graph_store.batch_add_relationships(result.relationships)
```

使用 API:
```bash
curl -X POST "http://localhost:8000/api/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "collector_type": "filesystem",
    "config": {
      "scan_paths": ["/path/to/scan"],
      "source": "my_filesystem"
    }
  }'
```

### 4.2 采集代码元数据

```python
from src.collectors.code import CodeMetadataCollector

collector = CodeMetadataCollector(
    source_path="./src",
    source="my_code",
    languages=["python"]
)

result = collector.collect()
```

### 4.3 查询元数据

使用 API:
```bash
# 查询所有实体
curl "http://localhost:8000/api/entities?limit=10"

# 查询特定类型的实体
curl "http://localhost:8000/api/entities?entity_type=file&limit=10"

# 执行 Cypher 查询
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 10"
  }'
```

### 4.4 可视化

访问可视化接口:
```bash
curl "http://localhost:8000/api/visualize?entity_type=file&depth=2"
```

## 5. 运行示例脚本

```bash
# 基本使用示例
python examples/basic_usage.py

# LLM 集成示例
python examples/llm_integration.py
```

## 6. 常见问题

### 6.1 FalkorDB 连接失败
- 确保 Redis/FalkorDB 服务正在运行
- 检查 `config/config.yaml` 中的连接配置
- 测试连接: `redis-cli ping`

### 6.2 导入错误
- 确保所有依赖已安装: `pip install -r requirements.txt`
- 检查 Python 版本: `python --version` (需要 3.10+)

### 6.3 权限错误
- 确保有写入 `data/` 目录的权限
- 检查文件系统采集器的扫描路径权限

## 7. 下一步

- 阅读 [ARCHITECTURE.md](ARCHITECTURE.md) 了解系统架构
- 查看 [examples/](examples/) 目录中的示例代码
- 探索 API 文档: http://localhost:8000/docs
- 自定义采集器: 继承 `BaseCollector` 实现新的采集器

## 8. 开发模式

启用开发模式（自动重载）:
```bash
python run.py
# 或设置 config.yaml 中 api.debug = true
```





