# 采集器类型从元模型获取的修复说明

## 问题分析

创建采集任务时，系统没有从元模型文件中获取采集器类型，而是使用了硬编码的逻辑。主要原因：

1. **`create_collector_by_collector_type` 方法没有优先使用 `collector_type_map`**
   - 该方法只尝试了多种命名转换方式，没有首先检查元模型中定义的 `collector_type` 映射

2. **`load_from_file` 中的变量作用域问题**
   - `entity_models_list` 变量在采集器类型加载时可能不在作用域内

3. **`execute_collect_task` 中的逻辑顺序问题**
   - 虽然尝试使用工厂模式，但没有优先使用 `collector_type_map` 中的直接映射

## 修复内容

### 1. 修复 `CollectorFactory.create_collector_by_collector_type` 方法

**修改前**：只尝试命名转换，没有使用 `collector_type_map`

**修改后**：
```python
# 首先尝试从collector_type_map中获取实体类型（优先使用元模型定义的映射）
entity_type = self.meta_registry.get_entity_type_by_collector_type(collector_type)
if entity_type:
    collector = self.create_collector(entity_type, source, config)
    if collector:
        return collector

# 如果collector_type_map中没有，再尝试命名转换（向后兼容）
```

### 2. 修复 `MetaRegistry.load_from_file` 方法

**修改前**：`entity_models_list` 变量作用域问题

**修改后**：
- 提前定义 `entity_models_list = data.get('entity_models', [])`
- 确保在采集器类型加载时可以使用该变量
- 添加了调试信息，打印已注册的采集器类型映射

### 3. 修复 `execute_collect_task` 方法

**修改前**：直接调用 `create_collector_by_collector_type`，没有优先使用直接映射

**修改后**：
```python
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
            # ...
```

### 4. 添加调试信息

- 在 `load_from_file` 中打印已注册的采集器类型映射
- 在 `load_all` 中打印所有已加载的采集器类型
- 在 `server.py` 启动时打印采集器类型数量

## 使用方式

### 1. 确保元模型文件包含 `collector_type` 字段

```yaml
collector_type: "code_metadata"  # 在文件顶部或metadata中

entity_models:
  - type: CodeProject
    # ...
```

### 2. 确保元模型文件在正确的位置

元模型文件应该放在 `metamodels/` 目录下（或配置的 `metamodels_dir` 目录）。

### 3. 创建采集任务

```json
POST /api/tasks/collect
{
    "collector_type": "code_metadata",  // 使用元模型中定义的collector_type
    "config": {
        "source": "my_project",
        "source_path": "/path/to/project"
    }
}
```

## 验证方法

1. **检查启动日志**：启动服务时应该看到类似输出：
   ```
   已注册采集器类型映射: code_metadata -> CodeProject (文件: CodeMetadata.yaml)
   已加载的采集器类型映射 (5 个):
     - code_metadata -> CodeProject
     - relational_database -> Database
     - graph_database -> GraphDatabase
     - filesystem -> Directory
     - git_repository -> GitRepository
   已加载元模型注册表，实体模型数: X, 关系模型数: Y, 采集器类型数: 5
   ```

2. **调用API获取采集器类型列表**：
   ```http
   GET /api/metamodel/collector-types
   ```

3. **创建采集任务**：使用元模型中定义的 `collector_type` 创建任务，应该使用元模型采集器而不是硬编码逻辑。

## 注意事项

1. **向后兼容**：如果元模型中没有找到对应的采集器类型，系统会回退到硬编码逻辑（relational, graphdb, code, filesystem）

2. **文件位置**：元模型文件必须放在 `metamodels/` 目录下才能被自动加载

3. **采集器类型唯一性**：每个元模型文件应该定义一个唯一的 `collector_type`，避免冲突


