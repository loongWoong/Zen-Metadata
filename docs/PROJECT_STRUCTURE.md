# 项目结构

```
zen-metadata/
├── README.md                 # 项目说明文档
├── ARCHITECTURE.md           # 系统架构文档
├── QUICKSTART.md            # 快速开始指南
├── PROJECT_STRUCTURE.md     # 项目结构说明（本文件）
├── requirements.txt         # Python 依赖
├── setup.py                 # 安装脚本
├── run.py                   # 快速启动脚本
├── .gitignore               # Git 忽略文件
│
├── config/                  # 配置文件目录
│   └── config.yaml          # 主配置文件
│
├── src/                     # 源代码目录
│   ├── __init__.py
│   │
│   ├── core/                # 核心模块
│   │   ├── __init__.py
│   │   ├── models.py        # 数据模型定义
│   │   ├── graph.py         # FalkorDB 图数据库操作
│   │   └── storage.py       # 存储层抽象接口
│   │
│   ├── collectors/          # 采集器模块
│   │   ├── __init__.py
│   │   ├── base.py          # 采集器基类
│   │   ├── relational.py    # 关系型数据库采集器
│   │   ├── graphdb.py       # 图数据库采集器
│   │   ├── code.py          # 代码元数据采集器
│   │   └── filesystem.py    # 文件系统采集器
│   │
│   ├── processing/          # 数据处理模块
│   │   ├── __init__.py
│   │   ├── sqlite.py        # SQLite 关系型数据处理
│   │   └── duckdb.py        # DuckDB 分析型数据处理
│   │
│   ├── visualization/       # 可视化模块
│   │   ├── __init__.py
│   │   └── graphiti.py      # Graphiti 可视化集成
│   │
│   └── api/                 # API 服务模块
│       ├── __init__.py
│       └── server.py        # FastAPI 服务
│
├── examples/                 # 示例代码
│   ├── basic_usage.py       # 基本使用示例
│   └── llm_integration.py   # LLM 集成示例
│
├── data/                    # 数据目录（自动创建）
│   ├── zen_metadata.db      # SQLite 数据库
│   └── zen_metadata_analytics.duckdb  # DuckDB 数据库
│
└── logs/                    # 日志目录（自动创建）
    └── zen_metadata.log     # 应用日志
```

## 模块说明

### 核心模块 (core)
- **models.py**: 定义统一的元数据实体和关系模型
- **graph.py**: FalkorDB 图数据库的连接和操作封装
- **storage.py**: 存储层的抽象接口，便于扩展

### 采集器模块 (collectors)
- **base.py**: 所有采集器的基类，提供通用功能
- **relational.py**: 关系型数据库（PostgreSQL, MySQL, SQLite）元数据采集
- **graphdb.py**: 图数据库（Neo4j, FalkorDB）元数据采集
- **code.py**: 编程语言代码元数据采集（Python, JavaScript, TypeScript, Java）
- **filesystem.py**: 文件系统元数据采集

### 数据处理模块 (processing)
- **sqlite.py**: SQLite 关系型数据存储和查询
- **duckdb.py**: DuckDB 分析型数据处理和统计

### 可视化模块 (visualization)
- **graphiti.py**: Graphiti 图形可视化集成，支持图布局和转换

### API 模块 (api)
- **server.py**: FastAPI RESTful API 服务，提供元数据采集、查询、可视化接口

## 扩展指南

### 添加新采集器
1. 在 `src/collectors/` 目录创建新文件
2. 继承 `BaseCollector` 类
3. 实现 `collect()` 方法
4. 返回 `CollectionResult` 对象

### 添加新存储后端
1. 在 `src/processing/` 目录创建新文件
2. 实现存储和查询方法
3. 在 `src/api/server.py` 中集成

### 添加新可视化方式
1. 在 `src/visualization/` 目录创建新文件
2. 实现可视化转换方法
3. 在 API 中添加相应端点





