# 采集器模块 - 元模型动态配置指南

## 概述

采集器模块已重构为支持基于元模型的动态配置方式。现在可以通过元模型包来配置和创建采集任务，而不再需要硬编码采集器类型。

## 核心组件

### 1. CollectorFactory（采集器工厂）

`CollectorFactory` 根据元模型动态创建采集器实例。

```python
from src.collectors.factory import CollectorFactory
from src.core.metamodel_registry import MetaRegistry

# 初始化
meta_registry = MetaRegistry()
meta_registry.load_all()  # 加载所有元模型
factory = CollectorFactory(meta_registry)

# 创建采集器
collector = factory.create_collector_by_collector_type(
    collector_type="git_repository",  # 采集器类型
    source="my_git_repo",  # 数据源标识
    config={
        "repo_path": "/path/to/repo",
        "branch": "main"
    }
)

# 执行采集
result = collector.collect()
```

### 2. CollectionTaskConfig（采集任务配置）

`CollectionTaskConfig` 用于定义采集任务的配置。

```python
from src.collectors.task_config import CollectionTaskConfig

# 创建单个任务配置
config = CollectionTaskConfig(
    entity_type="GitRepository",
    source="my_git_repo",
    collector_config={
        "repo_path": "/path/to/repo",
        "branch": "main"
    },
    package_name="git_metamodel",  # 可选的包名
    incremental=False
)

# 从元模型包创建多个任务配置
configs = CollectionTaskConfig.from_metamodel_package(
    package_name="git_metamodel",
    entity_types=["GitRepository", "GitCommit", "GitBranch"],
    source="my_git_repo",
    collector_config={"repo_path": "/path/to/repo"}
)
```

### 3. BaseCollector（采集器基类）

所有采集器都继承自 `BaseCollector`，现在支持：

- 从配置中获取元模型信息
- 使用字符串类型创建实体（不仅限于MetadataType枚举）
- 使用字符串关系类型创建关系（不仅限于RelationshipType枚举）

```python
from src.collectors.base import BaseCollector

class MyCollector(BaseCollector):
    def collect(self):
        result = CollectionResult()
        
        # 使用字符串类型创建实体（支持元模型自定义类型）
        entity = self.create_entity(
            entity_type="GitRepository",  # 可以是字符串或MetadataType枚举
            name="my-repo",
            description="My Git Repository",
            properties={"url": "https://github.com/user/repo"}
        )
        result.entities.append(entity)
        
        # 使用字符串关系类型创建关系
        relationship = self.create_relationship(
            source_id=entity1.id,
            target_id=entity2.id,
            relationship_type="contains"  # 可以是字符串或RelationshipType枚举
        )
        result.relationships.append(relationship)
        
        return result
```

## 元模型配置示例

### 元模型包结构

```
metamodels/
  git_metamodel/
    GitRepository@v1.yaml
    GitCommit@v1.yaml
    plugins/
      git_collector.py
    package_info.yaml
```

### 元模型文件示例（GitRepository@v1.yaml）

```yaml
entity_models:
  - type: GitRepository
    version: v1
    label: Git仓库
    description: Git代码仓库元数据
    properties:
      url:
        type: string
        required: true
        description: 仓库URL
      branch:
        type: string
        required: false
        description: 默认分支
    relationships:
      - type: contains
        target_types: [GitCommit, GitBranch]
    collector:
      plugin: git_collector.py
      entry: GitRepositoryCollector
      params:
        repo_path: ""
        branch: "main"
    enabled: true
```

### 采集器插件示例（git_collector.py）

```python
from src.collectors.base import BaseCollector
from src.core.models import CollectionResult

class GitRepositoryCollector(BaseCollector):
    def collect(self):
        result = CollectionResult()
        
        # 从配置获取参数
        repo_path = self.get_config("repo_path")
        branch = self.get_config("branch", "main")
        
        # 获取元模型信息
        entity_model = self.get_entity_model()
        entity_type = self.get_entity_type()  # "GitRepository"
        
        # 创建实体
        repo_entity = self.create_entity(
            entity_type=entity_type,  # 使用元模型中的类型
            name=repo_path.split("/")[-1],
            description=f"Git repository at {repo_path}",
            properties={
                "url": f"file://{repo_path}",
                "branch": branch
            }
        )
        result.entities.append(repo_entity)
        
        # ... 采集其他实体和关系 ...
        
        return result
```

## API使用示例

### 通过API创建采集任务

```python
import requests

# 创建元模型采集任务
response = requests.post("http://localhost:8000/api/tasks/collect", json={
    "collector_type": "git_repository",  # 采集器类型（会自动匹配到GitRepository实体类型）
    "config": {
        "source": "my_git_repo",
        "repo_path": "/path/to/repo",
        "branch": "main"
    }
})

task_id = response.json()["task_id"]
```

### 通过元模型包创建多个任务

```python
from src.collectors.task_config import CollectionTaskConfig
from src.collectors.factory import CollectorFactory
from src.core.metamodel_registry import MetaRegistry

# 加载元模型
meta_registry = MetaRegistry()
meta_registry.load_all()

# 获取包信息
package = meta_registry.get_package("git_metamodel")
entity_types = package["entity_models"]  # ["GitRepository", "GitCommit", ...]

# 为每个实体类型创建采集任务配置
configs = CollectionTaskConfig.from_metamodel_package(
    package_name="git_metamodel",
    entity_types=entity_types,
    source="my_git_repo",
    collector_config={"repo_path": "/path/to/repo"}
)

# 创建采集器并执行
factory = CollectorFactory(meta_registry)
for config in configs:
    collector = factory.create_collector(
        config.entity_type,
        config.source,
        config.collector_config
    )
    if collector:
        result = collector.collect()
        # 处理结果...
```

## 迁移指南

### 从硬编码采集器迁移到元模型配置

1. **创建元模型文件**：为你的实体类型创建元模型YAML文件
2. **创建采集器插件**：将采集器逻辑提取为插件文件
3. **注册元模型**：将元模型文件放到 `metamodels/` 目录下
4. **更新API调用**：使用新的 `collector_type` 而不是硬编码的类型

### 向后兼容

现有的硬编码采集器（relational, graphdb, code, filesystem）仍然支持，系统会优先尝试从元模型创建采集器，如果失败则回退到硬编码方式。

## 优势

1. **动态配置**：无需修改代码即可添加新的采集器类型
2. **类型安全**：通过元模型定义确保类型一致性
3. **可扩展性**：通过插件机制轻松扩展采集器功能
4. **统一管理**：所有采集器配置集中在元模型包中

