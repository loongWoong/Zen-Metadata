# 元模型管理系统实现文档

## 概述

本文档描述了 Zen Metadata 项目中元模型管理系统的完整实现。该系统允许用户动态定义和管理元数据类型、关系类型以及采集逻辑，实现了从"平台工程"到"元数据操作系统"的演进。

## 核心设计

### 架构组件

1. **元模型数据模型** (`src/core/metamodel.py`)
   - `EntityMetaModel`: 实体元模型
   - `RelationshipMetaModel`: 关系元模型
   - `MetaModelPackage`: 元模型包（用于上传和部署）

2. **元模型注册表** (`src/core/metamodel_registry.py`)
   - `MetaRegistry`: 元模型注册表核心类
   - 管理所有已注册的元模型
   - 支持版本管理
   - 热部署支持

3. **插件加载器** (`src/core/plugin_loader.py`)
   - `PluginLoader`: 插件加载器
   - 代码安全验证（AST分析）
   - 动态加载Python插件

4. **API接口** (`src/api/metamodel.py`)
   - 实体元模型CRUD
   - 关系元模型CRUD
   - 插件管理
   - 包上传和部署

## 功能特性

### 1. 实体元模型

实体元模型定义了：
- **类型标识**: 唯一类型名称和版本
- **属性结构**: 属性定义（类型、必填、枚举值等）
- **关系规则**: 允许的关系类型和目标类型
- **采集器配置**: 关联的采集器插件
- **质量规则**: 类型特定的质量评估规则

示例：
```yaml
type: BusinessMetric
version: v1
label: 业务指标
properties:
  formula:
    type: string
    required: true
  granularity:
    type: enum
    values: [day, week, month]
relationships:
  - type: DEPENDS_ON
    target: Table
collector:
  plugin: business_metric_collector.py
quality_rules:
  completeness:
    required_properties: [formula, owner]
  freshness:
    ttl_days: 7
```

### 2. 关系元模型

关系元模型定义了：
- **类型标识**: 关系类型和版本
- **类型约束**: 允许的源类型和目标类型
- **关系属性**: 关系可以携带的属性
- **推理能力**: 是否可推理/派生

示例：
```yaml
type: DERIVED_FROM
version: v1
label: 派生自
source_types: [BusinessMetric]
target_types: [Column, Table]
properties:
  confidence:
    type: float
inferable: true
```

### 3. 插件系统

#### 插件安全验证

- **AST分析**: 使用AST解析代码，检查禁止的导入和函数调用
- **白名单机制**: 只允许安全的模块导入
- **继承检查**: 确保插件类继承自 `BaseCollector`

#### 插件结构

```python
from src.collectors.base import BaseCollector
from src.core.models import CollectionResult

class MyCollector(BaseCollector):
    def collect(self) -> CollectionResult:
        # 采集逻辑
        entities = []
        relationships = []
        return CollectionResult(
            entities=entities,
            relationships=relationships
        )
```

### 4. 热部署

支持前端上传元模型包，系统自动：
1. 验证插件代码安全性
2. 保存元模型配置
3. 加载插件
4. 注册到元模型注册表
5. 无需重启服务

### 5. 与质量系统集成

元模型可以定义类型特定的质量规则：

```yaml
quality_rules:
  completeness:
    required_properties: [formula, owner]
  freshness:
    ttl_days: 7
  connectivity:
    min_relationships: 2
```

质量评估器会根据元模型自动加载这些规则。

## API接口

### 实体元模型

#### 列出所有实体元模型
```http
GET /api/metamodel/entities
```

#### 获取实体元模型
```http
GET /api/metamodel/entities/{entity_type}?version=v1
```

#### 创建实体元模型
```http
POST /api/metamodel/entities
Content-Type: application/json

{
  "type": "BusinessMetric",
  "version": "v1",
  "label": "业务指标",
  "properties": {...},
  "relationships": [...],
  "collector": {...},
  "quality_rules": {...}
}
```

#### 删除实体元模型
```http
DELETE /api/metamodel/entities/{entity_type}?version=v1
```

### 关系元模型

#### 列出所有关系元模型
```http
GET /api/metamodel/relationships
```

#### 创建关系元模型
```http
POST /api/metamodel/relationships
Content-Type: application/json

{
  "type": "DERIVED_FROM",
  "version": "v1",
  "label": "派生自",
  "source_types": ["BusinessMetric"],
  "target_types": ["Column", "Table"]
}
```

### 插件管理

#### 列出所有插件
```http
GET /api/metamodel/plugins
```

#### 验证插件代码
```http
POST /api/metamodel/plugins/validate
Content-Type: application/json

{
  "code": "from src.collectors.base import BaseCollector\n..."
}
```

### 包部署

#### 上传并部署元模型包
```http
POST /api/metamodel/upload
Content-Type: multipart/form-data

file: <yaml_or_json_file>
```

#### 部署元模型包（JSON）
```http
POST /api/metamodel/deploy
Content-Type: application/json

{
  "entity_models": [...],
  "relationship_models": [...],
  "plugins": {
    "collector.py": "code here..."
  },
  "metadata": {...}
}
```

### 注册表管理

#### 获取注册表信息
```http
GET /api/metamodel/registry
```

#### 重新加载注册表
```http
POST /api/metamodel/registry/reload
```

## 使用示例

### Python代码示例

```python
from src.core.metamodel_registry import MetaRegistry
from src.core.metamodel import EntityMetaModel

# 初始化注册表
registry = MetaRegistry(metamodels_dir="metamodels", plugins_dir="plugins")
registry.load_all()

# 获取实体元模型
entity_model = registry.get_entity_model("BusinessMetric")

# 验证实体属性
is_valid, error = entity_model.validate_property("formula", "SUM(revenue)")
if not is_valid:
    print(f"验证失败: {error}")

# 获取采集器
collector_class = registry.get_collector("BusinessMetric")
if collector_class:
    collector = collector_class(name="metric_collector", source="business")
    result = collector.collect()
```

### 部署元模型包

```python
from src.core.metamodel import MetaModelPackage, EntityMetaModel, RelationshipMetaModel

# 创建元模型包
package = MetaModelPackage(
    entity_models=[
        EntityMetaModel(
            type="BusinessMetric",
            version="v1",
            label="业务指标",
            properties={...}
        )
    ],
    relationship_models=[...],
    plugins={
        "business_metric_collector.py": "plugin code here..."
    }
)

# 部署
results = registry.deploy_package(package)
print(f"部署结果: {results}")
```

## 安全考虑

### 插件安全验证

1. **禁止的模块**: `os`, `subprocess`, `socket`, `sys`, `eval`, `exec` 等
2. **白名单导入**: 只允许安全的模块（`typing`, `datetime`, `json` 等）
3. **继承检查**: 必须继承自 `BaseCollector`
4. **AST分析**: 静态代码分析，防止危险代码执行

### 版本管理

- 支持多版本共存
- 已存在的实体保留旧版本元模型ID
- 新版本不影响已有数据

## 配置说明

### 主配置文件 (`config/config.yaml`)

```yaml
metamodel:
  # 元模型文件目录
  metamodels_dir: "metamodels"
  # 插件目录
  plugins_dir: "plugins"
  # 是否启用元模型管理
  enabled: true
  # 自动加载元模型
  auto_load: true
```

### 元模型文件结构

元模型文件应放在 `metamodels/` 目录下，支持 `.yaml`, `.yml`, `.json` 格式。

文件结构：
```yaml
entity_models:
  - type: BusinessMetric
    version: v1
    ...

relationship_models:
  - type: DERIVED_FROM
    version: v1
    ...

plugins:
  collector.py: |
    code here...

metadata:
  name: "Package Name"
  version: "1.0.0"
```

## 最佳实践

1. **版本管理**
   - 使用语义化版本（v1, v2, ...）
   - 修改已有类型时创建新版本
   - 保持向后兼容

2. **插件开发**
   - 只使用白名单中的模块
   - 继承 `BaseCollector`
   - 返回标准的 `CollectionResult`

3. **质量规则**
   - 在元模型中定义类型特定的质量规则
   - 合理设置必填字段和新鲜度要求

4. **关系定义**
   - 明确指定允许的源类型和目标类型
   - 使用 `inferable` 和 `derivable` 标记可推理的关系

## 与质量系统的集成

元模型中的质量规则会自动被质量评估器加载：

1. **完整性规则**: 根据 `required_properties` 自动生成必填字段规则
2. **新鲜度规则**: 根据 `ttl_days` 自动生成新鲜度规则
3. **连接性规则**: 根据 `min_relationships` 检查关系数量

这使得不同类型可以有不同的质量标准，实现"治理自动化"。

## 未来改进

1. **可视化编辑器**: 前端可视化编辑元模型
2. **模板系统**: 提供常用元模型模板
3. **版本对比**: 支持版本间的差异对比
4. **迁移工具**: 自动迁移旧版本数据到新