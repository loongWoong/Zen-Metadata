<div align="center">

![logo](./logo/ZenMetadata.png)

# Zen Metadata

**统一元数据管理系统 | 可自我演化的语义系统内核 | 基于图数据库的元数据管理平台**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-19-blue.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

[中文](README.md) • [English](README_EN.md)

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [文档](#-文档) • [贡献](#-贡献) • [许可证](#-许可证)

</div>

---

## 📖 简介

**Zen Metadata** 是一个基于图数据库的统一元数据管理系统，旨在实现万事万物的元数据统一管理，支撑大模型进行语义理解和交互。系统采用前后端分离架构，提供完整的元数据采集、存储、查询、分析和可视化能力。

### 🧠 核心愿景：可自我演化的语义系统内核

Zen Metadata 的核心目标是构建**一个可自我演化的语义系统内核**，作为平台与大模型深度集成的智能基础。这个内核不仅能够：

- **语义理解与推理**：基于图数据库的元数据关系图谱，实现深度的语义理解和关系推理
- **自我学习与优化**：通过与 LLM 的交互，不断学习和优化元数据的语义表示和关系映射
- **动态演化**：根据使用反馈和新的元数据输入，自动调整和扩展语义模型
- **智能推荐**：基于语义相似度和关系路径，为 LLM 提供智能的元数据推荐和上下文增强

这个语义系统内核将成为连接元数据世界与 AI 世界的桥梁，使大模型能够更深入地理解和利用结构化元数据。

### ✨ 核心价值

- 🎯 **统一管理**：一站式管理所有类型的元数据
- 🔍 **智能查询**：支持复杂的图查询和关系分析
- 📊 **可视化展示**：交互式元数据图谱展示
- 🤖 **LLM 友好**：为 LLM 提供结构化的元数据访问接口
- 🧠 **可自我演化**：构建可自我演化的语义系统内核，持续优化语义理解能力
- 🔌 **可扩展**：插件化的采集器框架，轻松扩展新数据源

---

## 🚀 功能特性

### 💾 数据存储

- **图数据库存储**：基于 FalkorDB 存储元数据关系图谱，支持复杂的图查询和关系分析
- **多数据源支持**：SQLite（关系型）和 DuckDB（分析型）数据处理，满足不同场景需求
- **数据同步**：自动同步图数据库与关系型数据库之间的数据

### 📥 元数据采集

- **可扩展采集器框架**：支持多种元数据源的采集
  - 关系型数据库采集器（PostgreSQL, MySQL, SQLite）
  - 图数据库采集器（Neo4j, FalkorDB）
  - 编程语言代码元数据采集器（Python, JavaScript, TypeScript, Java）
  - 文件系统元数据采集器
- **异步任务管理**：支持长时间运行的采集任务，提供任务状态跟踪和进度监控
- **WebSocket 实时通信**：实时推送任务状态和采集进度

### 📊 可视化与分析

- **Web 前端界面**：基于 React + TypeScript + Ant Design 的现代化前端界面
- **图形可视化**：基于 Graphiti 和 ReactFlow 的交互式元数据图谱展示
- **数据分析**：基于 DuckDB 的高性能数据分析和统计功能
- **多视图展示**：支持仪表盘、实体浏览、图谱视图、分析视图等多种展示方式

### 🔌 API 与集成

- **RESTful API**：完整的 FastAPI 后端服务，提供标准化的元数据访问接口
- **数据导出**：支持多种格式的数据导出（JSON, CSV, GraphML 等）
- **LLM 集成支持**：为 LLM 提供结构化的元数据访问接口，支持语义查询
- **可自我演化的语义系统内核**：构建智能语义内核，通过与大模型的交互实现自我学习和优化
  - 语义理解与推理引擎
  - 动态语义模型演化
  - 智能元数据推荐系统
  - 上下文感知的语义增强

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Graphiti 可视化层                      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    API 服务层                             │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│        可自我演化的语义系统内核 (LLM 集成层)                │
│  ├─ 语义理解与推理引擎                                     │
│  ├─ 动态语义模型演化                                       │
│  ├─ 智能元数据推荐系统                                     │
│  └─ 上下文感知的语义增强                                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  元数据采集器层 (可扩展)                                   │
│  ├─ 关系型数据库采集器                                     │
│  ├─ 图数据库采集器                                         │
│  ├─ 代码元数据采集器                                       │
│  └─ 文件系统元数据采集器                                   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   数据存储层                               │
│  ├─ FalkorDB (图数据库 - 元数据关系)                      │
│  ├─ SQLite (关系型数据)                                   │
│  └─ DuckDB (分析型数据)                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术栈

### 后端
- **Python 3.10+** - 主要开发语言
- **FalkorDB** - 图数据库，用于存储元数据关系图谱
- **SQLite** - 关系型数据库，用于结构化数据存储
- **DuckDB** - 分析型数据库，用于高性能数据分析
- **FastAPI** - 现代 Web 框架，提供 RESTful API
- **Pydantic** - 数据验证和序列化
- **Uvicorn** - ASGI 服务器
- **Tree-sitter** - 代码解析和元数据提取
- **SQLAlchemy** - 数据库 ORM 和连接管理

### 前端
- **React 19** - UI 框架
- **TypeScript** - 类型安全的 JavaScript
- **Ant Design** - 企业级 UI 组件库
- **ReactFlow** - 图形可视化组件
- **ECharts** - 数据可视化图表库
- **Zustand** - 状态管理
- **React Router** - 路由管理
- **Axios** - HTTP 客户端
- **Vite** - 构建工具

### 工具与库
- **Graphiti** - 图形可视化库
- **NetworkX** - 图分析库
- **Plotly** - 交互式图表库
- **Pandas** - 数据处理库
- **Redis** - 缓存和任务队列

---

## 📦 项目结构

```
zen-metadata/
├── README.md                 # 项目说明文档
├── ARCHITECTURE.md           # 系统架构文档
├── QUICKSTART.md            # 快速开始指南
├── PROJECT_STRUCTURE.md     # 项目结构说明
├── DEPLOYMENT.md            # 部署文档
├── IMPLEMENTATION_SUMMARY.md # 实现总结
├── requirements.txt         # Python 依赖
├── setup.py                 # 安装脚本
├── run.py                   # 快速启动脚本
├── .gitignore               # Git 忽略文件
│
├── config/                  # 配置文件目录
│   └── config.yaml          # 主配置文件
│
├── src/                     # 源代码目录
│   ├── core/                # 核心模块
│   │   ├── models.py        # 数据模型定义
│   │   ├── graph.py         # FalkorDB 图数据库操作
│   │   ├── storage.py        # 存储层抽象接口
│   │   └── tasks.py         # 任务管理
│   ├── collectors/          # 采集器模块
│   │   ├── base.py          # 采集器基类
│   │   ├── relational.py    # 关系型数据库采集器
│   │   ├── graphdb.py       # 图数据库采集器
│   │   ├── code.py          # 代码元数据采集器
│   │   └── filesystem.py    # 文件系统采集器
│   ├── processing/          # 数据处理模块
│   │   ├── sqlite.py        # SQLite 关系型数据处理
│   │   ├── duckdb.py        # DuckDB 分析型数据处理
│   │   └── sync.py          # 数据同步
│   ├── visualization/       # 可视化模块
│   │   └── graphiti.py      # Graphiti 可视化集成
│   └── api/                 # API 服务模块
│       ├── server.py        # FastAPI 主服务
│       ├── tasks.py         # 任务管理 API
│       ├── export.py        # 数据导出 API
│       └── websocket.py     # WebSocket 实时通信
│
├── frontend/                # 前端应用
│   ├── src/
│   │   ├── components/      # React 组件
│   │   │   └── Layout/      # 布局组件
│   │   ├── pages/           # 页面组件
│   │   │   ├── Dashboard/   # 仪表盘
│   │   │   ├── EntityBrowser/ # 实体浏览
│   │   │   ├── GraphView/   # 图谱视图
│   │   │   ├── Collection/  # 采集管理
│   │   │   └── Analytics/  # 数据分析
│   │   ├── services/        # API 服务
│   │   ├── store/           # 状态管理
│   │   └── types/           # TypeScript 类型定义
│   ├── package.json         # 前端依赖
│   └── vite.config.ts       # Vite 配置
│
├── examples/                # 示例代码
│   ├── basic_usage.py       # 基本使用示例
│   └── llm_integration.py   # LLM 集成示例
│
├── data/                    # 数据目录（自动创建）
│   ├── zen_metadata.db      # SQLite 数据库
│   └── zen_metadata_analytics.duckdb  # DuckDB 数据库
│
└── logs/                    # 日志目录（自动创建）
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10 或更高版本
- Node.js 16+ 和 npm（用于前端开发）
- Redis/FalkorDB 服务（用于图数据库）

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/your-username/zen-metadata.git
cd zen-metadata
```

#### 2. 安装后端依赖

```bash
pip install -r requirements.txt
```

#### 3. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

#### 4. 配置

编辑 `config/config.yaml` 设置数据库连接和采集器配置。详细配置说明请参考 [QUICKSTART.md](QUICKSTART.md)。

#### 5. 启动服务

**启动后端 API 服务：**

```bash
python run.py
```

或使用 uvicorn 直接启动：

```bash
uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload
```

**启动前端开发服务器：**

```bash
cd frontend
npm run dev
```

#### 6. 访问应用

- **API 文档**: http://localhost:8000/docs
- **前端应用**: http://localhost:5173（Vite 默认端口）

---

## 💡 使用示例

### 通过 API 采集元数据

```bash
# 采集文件系统元数据
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

### 通过 Python SDK 使用

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

# 查询元数据图谱
results = graph_store.query("MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 10")
```

### 更多示例

查看 [examples/](examples/) 目录中的示例代码：
- `basic_usage.py`: 基本使用示例
- `llm_integration.py`: LLM 集成示例

详细使用说明请参考 [QUICKSTART.md](QUICKSTART.md)。

---

## 📊 开发状态

### ✅ 已完成功能

- [x] 项目架构设计
- [x] 核心数据模型实现
- [x] 采集器框架实现
- [x] 各类型采集器实现
  - [x] 关系型数据库采集器
  - [x] 图数据库采集器
  - [x] 代码元数据采集器
  - [x] 文件系统采集器
- [x] 图数据库存储（FalkorDB）
- [x] 关系型数据库存储（SQLite）
- [x] 分析型数据库（DuckDB）
- [x] FastAPI RESTful API
- [x] 任务管理系统
- [x] WebSocket 实时通信
- [x] 数据导出功能
- [x] 前端基础框架（React + TypeScript）
- [x] 前端页面组件
  - [x] 仪表盘
  - [x] 实体浏览
  - [x] 图谱视图
  - [x] 采集管理
  - [x] 数据分析

### 🚧 开发计划

查看 [ROADMAP.md](ROADMAP.md) 了解详细的开发计划。

---

## 📚 文档

- [ARCHITECTURE.md](ARCHITECTURE.md) - 系统架构详细说明
- [QUICKSTART.md](QUICKSTART.md) - 快速开始指南
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 项目结构说明
- [DEPLOYMENT.md](DEPLOYMENT.md) - 部署指南
- [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) - 实现总结

---

## 🤝 贡献

我们欢迎所有形式的贡献！无论是报告问题、提出建议，还是提交代码，都非常感谢。

### 贡献方式

1. **报告问题**：在 [Issues](https://github.com/your-username/zen-metadata/issues) 中报告 bug 或提出功能建议
2. **提交代码**：Fork 项目，创建功能分支，提交 Pull Request
3. **改进文档**：帮助完善文档和示例代码

### 贡献指南

在开始贡献之前，请先阅读以下文档：
- [ARCHITECTURE.md](ARCHITECTURE.md) - 了解系统架构
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 了解项目结构
- [QUICKSTART.md](QUICKSTART.md) - 快速开始开发

### 开发流程

1. Fork 本仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 许可证。

```
MIT License

Copyright (c) 2024 Zen Metadata Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## ⭐ Star History

如果这个项目对你有帮助，请考虑给它一个 Star ⭐！

---

<div align="center">

**Made with ❤️ by Zen Metadata Team**

[⬆ 回到顶部](#-zen-metadata)

</div>
