# 前端采集器类型显示修复说明

## 问题描述

元模型导入并更新注册表后，在创建采集任务时，采集器类型下拉框中没有显示元模型导入文件定义的采集器类型。

## 问题分析

1. **前端没有使用 `collector_type` API**：前端在 `loadCollectorOptions` 中是从实体模型的 `collector.plugin` 名称推断采集器类型，而不是使用元模型中定义的 `collector_type` 字段。

2. **API 缺少 `collector_type` 提取**：`upload_package` API 在解析 YAML 文件时没有提取 `collector_type` 字段。

## 修复内容

### 1. 添加 `listCollectorTypes` API 到前端服务

在 `frontend/src/services/api.ts` 中添加：

```typescript
listCollectorTypes: () =>
  apiClient.get<{
    collector_types: Array<{
      collector_type: string;
      entity_type: string;
      label: string;
      description?: string;
      version: string;
      enabled: boolean;
    }>;
    count: number;
  }>('/api/metamodel/collector-types'),
```

### 2. 更新前端 `loadCollectorOptions` 函数

**修改前**：从插件名称推断采集器类型
```typescript
const pluginName = model.collector.plugin.replace('.py', '');
const collectorType = pluginName.replace('_collector', '');
```

**修改后**：优先从 `/api/metamodel/collector-types` API 获取
```typescript
// 优先从API获取元模型中定义的采集器类型
const collectorTypesResponse = await api.metamodel.listCollectorTypes();

if (collectorTypesResponse.data?.collector_types) {
  // 批量获取实体模型详情以获取config_schema
  const entityTypePromises = collectorTypesResponse.data.collector_types
    .filter((ct: any) => ct.enabled !== false && !defaultCollectors.find(c => c.value === ct.collector_type))
    .map(async (ct: any) => {
      // 获取实体模型详情
      const entityResponse = await api.metamodel.getEntityModel(ct.entity_type);
      return {
        value: ct.collector_type,  // 使用元模型定义的collector_type
        label: ct.label || ct.collector_type,
        isDefault: false,
        isMetamodel: true,
        configSchema: entityResponse.data?.collector?.config_schema || [],
        entityType: ct.entity_type,
      };
    });
  
  const collectors = await Promise.all(entityTypePromises);
  metamodelCollectors.push(...collectors);
}
```

### 3. 修复 `upload_package` API

在 `src/api/metamodel.py` 中，确保从 YAML 文件中提取 `collector_type`：

```python
package = MetaModelPackage(
    entity_models=entity_models,
    relationship_models=relationship_models,
    plugins=data.get('plugins', {}),
    metadata=data.get('metadata', {}),
    collector_type=data.get('collector_type') or (data.get('metadata', {}).get('collector_type') if isinstance(data.get('metadata'), dict) else None)
)
```

## 工作流程

1. **元模型导入**：
   - 用户上传 YAML 文件到元模型管理页面
   - 后端解析文件，提取 `collector_type` 字段
   - 部署到注册表，建立 `collector_type` -> `entity_type` 映射

2. **前端加载采集器类型**：
   - 调用 `/api/metamodel/collector-types` API
   - 获取所有已注册的采集器类型
   - 批量获取实体模型详情以获取配置 schema
   - 显示在下拉框中

3. **元模型更新事件**：
   - 当元模型部署成功后，触发 `metamodel-updated` 事件
   - 采集任务页面监听该事件，自动重新加载采集器选项

## 验证方法

1. **导入元模型**：
   - 在元模型管理页面上传包含 `collector_type` 的 YAML 文件
   - 确认部署成功

2. **检查采集器类型**：
   - 打开采集任务创建页面
   - 查看采集器类型下拉框
   - 应该能看到元模型中定义的采集器类型（如 `code_metadata`, `relational_database` 等）

3. **检查控制台**：
   - 打开浏览器开发者工具
   - 查看 Network 标签，确认调用了 `/api/metamodel/collector-types`
   - 查看 Console，确认没有错误

## 注意事项

1. **向后兼容**：如果 API 调用失败，前端会回退到旧方法（从插件名称推断）

2. **性能优化**：使用 `Promise.all` 批量获取实体模型详情，提高加载速度

3. **事件监听**：确保在元模型更新后触发 `metamodel-updated` 事件，以便采集任务页面自动刷新

4. **采集器类型唯一性**：每个元模型文件应该定义一个唯一的 `collector_type`，避免冲突


