# Zen Metadata 系统架构文档

## 1. 系统概述

Zen Metadata 是一个基于图数据库的统一元数据管理系统，旨在实现万事万物的元数据统一管理，支撑大模型进行语义理解和交互。

## 2. 核心设计原则

### 2.1 可扩展性
- 采集器采用插件化设计，易于添加新的数据源
- 存储层支持多种数据库后端
- API 层提供统一的接口抽象

### 2.2 统一性
- 所有元数据统一表示为实体和关系
- 使用标准的数据模型和关系类型
- 提供一致的查询接口

### 2.3 语义化
- 支持丰富的元数据类型和关系类型
- 为 LLM 提供结构化的语义信息
- 支持图查询和路径分析

## 3. 系统架构

### 3.1 分层架构

```
┌─────────────────────────────────────────┐
│         展示层 (Graphiti)                │
│     - 图形可视化                         │
│     - 交互式探索                         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│          API 服务层 (FastAPI)            │
│     - RESTful API                        │
│     - 查询接口                           │
│     - 采集接口                           │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         业务逻辑层                        │
│     - 采集器管理                         │
│     - 数据转换                           │
│     - 查询处理                           │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         数据存储层                        │
│     - FalkorDB (图数据库)                │
│     - SQLite (关系型)                    │
│     - DuckDB (分析型)                    │
└─────────────────────────────────────────┘
```

### 3.2 核心模块

#### 3.2.1 核心模块 (core)
- **models.py**: 定义统一的数据模型
  - MetadataEntity: 元数据实体
  - MetadataRelationship: 元数据关系
  - MetadataType: 实体类型枚举
  - RelationshipType: 关系类型枚举

- **graph.py**: FalkorDB 图数据库操作
  - GraphStore: 图存储管理器
  - 支持 Cypher 查询
  - 实体和关系的 CRUD 操作

- **storage.py**: 存储层抽象接口
  - StorageInterface: 统一存储接口

#### 3.2.2 采集器模块 (collectors)
- **base.py**: 采集器基类
  - BaseCollector: 所有采集器的基类
  - 提供通用的实体和关系创建方法

- **relational.py**: 关系型数据库采集器
  - 支持 PostgreSQL, MySQL, SQLite
  - 采集表、列、索引、外键等

- **graphdb.py**: 图数据库采集器
  - 支持 Neo4j, FalkorDB
  - 采集节点标签、关系类型等

- **code.py**: 代码元数据采集器
  - 支持 Python, JavaScript, TypeScript, Java
  - 使用 AST 和 tree-sitter 解析
  - 采集函数、类、模块、导入关系等

- **filesystem.py**: 文件系统采集器
  - 递归扫描目录
  - 采集文件和目录结构
  - 支持排除模式

#### 3.2.3 数据处理模块 (processing)
- **sqlite.py**: SQLite 关系型数据处理
  - 存储实体和关系
  - 支持复杂查询
  - 提供统计功能

- **duckdb.py**: DuckDB 分析型数据处理
  - 高性能分析查询
  - 实体分布分析
  - 关系模式分析
  - 中心实体发现

#### 3.2.4 可视化模块 (visualization)
- **graphiti.py**: Graphiti 可视化集成
  - 图数据转换
  - 布局计算
  - 子图提取
  - 类型过滤

#### 3.2.5 API 模块 (api)
- **server.py**: FastAPI 服务
  - RESTful API 端点
  - 采集接口
  - 查询接口
  - 可视化接口
  - 分析接口

## 4. 数据模型

### 4.1 实体类型 (MetadataType)
- DATABASE: 数据库
- TABLE: 表
- COLUMN: 列
- FUNCTION: 函数
- CLASS: 类
- FILE: 文件
- DIRECTORY: 目录
- PACKAGE: 包
- MODULE: 模块
- RELATIONSHIP: 关系
- SCHEMA: 模式
- INDEX: 索引
- CONSTRAINT: 约束

### 4.2 关系类型 (RelationshipType)
- CONTAINS: 包含
- DEPENDS_ON: 依赖
- REFERENCES: 引用
- IMPLEMENTS: 实现
- INHERITS: 继承
- CALLS: 调用
- IMPORTS: 导入
- USES: 使用
- BELONGS_TO: 属于
- RELATED_TO: 相关

## 5. 数据流

### 5.1 采集流程
1. 初始化采集器（配置数据源）
2. 执行采集（collect 方法）
3. 返回 CollectionResult（实体和关系列表）
4. 存储到图数据库（FalkorDB）
5. 存储到关系数据库（SQLite）
6. 可选：同步到分析数据库（DuckDB）

### 5.2 查询流程
1. 接收查询请求（Cypher 或 SQL）
2. 执行查询（图数据库或关系数据库）
3. 返回查询结果
4. 可选：转换为可视化格式

### 5.3 LLM 交互流程
1. LLM 发送语义查询
2. 系统解析查询意图
3. 转换为图查询或关系查询
4. 执行查询并获取结果
5. 生成语义摘要
6. 返回给 LLM

## 6. 扩展点

### 6.1 添加新采集器
1. 继承 BaseCollector
2. 实现 collect 方法
3. 返回 CollectionResult
4. 注册到采集器管理器

### 6.2 添加新存储后端
1. 实现 StorageInterface
2. 实现所有抽象方法
3. 在配置中启用

### 6.3 添加新可视化方式
1. 扩展 GraphitiVisualizer
2. 实现新的布局算法
3. 添加新的过滤和查询方法

## 7. 性能考虑

### 7.1 批量操作
- 使用批量插入减少数据库交互
- 批量添加实体和关系

### 7.2 索引优化
- 在常用查询字段上创建索引
- 图数据库自动索引节点和关系

### 7.3 缓存策略
- 缓存常用查询结果
- 缓存统计信息

## 8. 安全性

### 8.1 数据访问控制
- API 认证和授权
- 敏感信息过滤

### 8.2 数据验证
- 使用 Pydantic 进行数据验证
- 输入参数验证

## 9. 部署建议

### 9.1 开发环境
- 使用 SQLite 和内存模式 DuckDB
- 本地 FalkorDB 实例

### 9.2 生产环境
- 独立的 FalkorDB 服务器
- 持久化的 SQLite 和 DuckDB
- API 服务使用 Gunicorn 或 uvicorn
- 配置反向代理（Nginx）

## 10. 未来扩展

### 10.1 更多数据源
- NoSQL 数据库采集器
- API 元数据采集器
- 容器和 Kubernetes 元数据采集器

### 10.2 增强的 LLM 集成
- 自然语言查询接口
- 自动元数据标注
- 语义搜索

### 10.3 实时更新
- 增量采集
- 变更通知
- 版本管理





