# 元数据质量管理系统实现方案

## 概述

本文档描述了 Zen Metadata 项目中元数据质量管理系统的完整实现方案。该系统提供了全面的元数据质量评估、规则引擎、监控告警和趋势分析功能。

## 架构设计

### 核心组件

1. **质量评分模型** (`src/core/quality.py`)
   - `MetadataQualityScore`: 质量评分数据模型
   - `QualityIssue`: 质量问题模型
   - `QualityMetrics`: 质量指标统计
   - `QualityDimension`: 质量维度枚举（完整性、准确性、一致性、新鲜度）
   - `QualityLevel`: 质量等级枚举

2. **规则引擎** (`src/core/quality_rules.py`)
   - `QualityRule`: 规则基类
   - `RequiredFieldRule`: 必填字段规则
   - `FieldFormatRule`: 字段格式验证规则
   - `FieldValueRangeRule`: 字段值域规则
   - `RelationshipConsistencyRule`: 关系一致性规则
   - `FreshnessRule`: 新鲜度规则
   - `CustomPythonRule`: 自定义 Python 表达式规则
   - `QualityRuleEngine`: 规则引擎管理器

3. **质量评估器** (`src/core/quality_assessor.py`)
   - `QualityAssessor`: 质量评估器
   - 计算各维度评分
   - 生成综合质量评分
   - 批量评估支持

4. **监控告警系统** (`src/core/quality_monitor.py`)
   - `QualityMonitor`: 质量监控器
   - `AlertRule`: 告警规则
   - `AlertChannel`: 告警渠道（邮件、Webhook、WebSocket、日志）
   - `QualityTrendAnalyzer`: 质量趋势分析器

5. **API 接口** (`src/api/quality.py`)
   - 质量评估 API
   - 规则管理 API
   - 告警管理 API
   - 趋势分析 API

## 功能特性

### 1. 质量评分体系

#### 四个质量维度

1. **完整性 (Completeness)**
   - 检查必填字段（name, type, source）的填充率
   - 检查描述字段是否存在
   - 权重：30%

2. **准确性 (Accuracy)**
   - 通过规则引擎验证数据格式
   - 验证字段值域
   - 权重：30%

3. **一致性 (Consistency)**
   - 检查实体间关系的逻辑一致性
   - 验证关系完整性
   - 权重：20%

4. **新鲜度 (Freshness)**
   - 基于 updated_at 时间戳评估数据更新频率
   - 使用指数衰减函数计算新鲜度
   - 权重：20%

#### 综合评分计算

```python
overall_score = (
    completeness_score * 0.3 +
    accuracy_score * 0.3 +
    consistency_score * 0.2 +
    freshness_score * 0.2
)
```

#### 质量等级

- **优秀 (Excellent)**: 0.9 - 1.0
- **良好 (Good)**: 0.7 - 0.9
- **一般 (Fair)**: 0.5 - 0.7
- **较差 (Poor)**: 0.3 - 0.5
- **严重 (Critical)**: 0.0 - 0.3

### 2. 质量规则引擎

#### 内置规则类型

1. **必填字段规则 (required_field)**
   ```yaml
   - type: required_field
     name: required_name
     dimension: completeness
     severity: critical
     field_name: name
   ```

2. **格式验证规则 (format)**
   ```yaml
   - type: format
     name: format_id
     dimension: accuracy
     pattern: "^[a-zA-Z0-9_\\-]+$"
     field_name: id
   ```

3. **值域规则 (value_range)**
   ```yaml
   - type: value_range
     name: value_range_age
     dimension: accuracy
     min_value: 0
     max_value: 150
     field_name: age
   ```

4. **关系一致性规则 (relationship)**
   ```yaml
   - type: relationship
     name: relationship_table_columns
     dimension: consistency
     relationship_type: contains
     required: false
   ```

5. **新鲜度规则 (freshness)**
   ```yaml
   - type: freshness
     name: freshness_30_days
     dimension: freshness
     max_age_days: 30
   ```

6. **自定义 Python 规则 (custom_python)**
   ```yaml
   - type: custom_python
     name: custom_description_length
     dimension: completeness
     expression: "entity.description and len(entity.description.strip()) >= 10"
   ```

#### 规则配置

规则可以通过 YAML 配置文件定义（`config/quality_rules.yaml`），支持：
- 规则启用/禁用
- 严重程度设置（critical, high, medium, low）
- 规则描述
- 动态加载和更新

### 3. 监控和告警

#### 告警规则

系统内置以下告警规则：
- 综合评分过低（< 0.5）
- 质量等级为严重
- 完整性评分过低（< 0.6）
- 数据过期（新鲜度 < 0.3）

#### 告警渠道

1. **日志告警** (默认启用)
   - 输出到控制台和日志文件

2. **邮件告警**
   ```python
   quality_monitor.configure_email(
       smtp_host="smtp.example.com",
       smtp_port=587,
       username="user@example.com",
       password="password",
       from_email="quality@example.com",
       to_emails=["admin@example.com"]
   )
   ```

3. **Webhook 告警**
   ```python
   quality_monitor.configure_webhook(
       url="https://your-webhook-url.com/alerts",
       method="POST",
       headers={"Authorization": "Bearer token"}
   )
   ```

4. **WebSocket 告警**
   - 实时推送告警到前端

### 4. 趋势分析

系统支持质量趋势分析：
- 单个实体的质量变化趋势
- 聚合质量趋势（所有实体）
- 质量改进/退化检测
- 历史数据记录

## API 接口

### 质量评估

#### 评估单个实体
```http
POST /api/quality/assess/entity
Content-Type: application/json

{
  "entity_id": "entity_123"
}
```

#### 批量评估
```http
POST /api/quality/assess/batch
Content-Type: application/json

{
  "entity_ids": ["entity_1", "entity_2"],
  "entity_type": "table",
  "source": "postgres"
}
```

#### 获取质量指标
```http
GET /api/quality/metrics?entity_type=table&source=postgres
```

### 规则管理

#### 获取所有规则
```http
GET /api/quality/rules
```

#### 添加规则
```http
POST /api/quality/rules
Content-Type: application/json

{
  "type": "required_field",
  "name": "required_description",
  "dimension": "completeness",
  "severity": "medium",
  "field_name": "description"
}
```

#### 启用/禁用规则
```http
PUT /api/quality/rules/{rule_name}/enable
PUT /api/quality/rules/{rule_name}/disable
```

#### 删除规则
```http
DELETE /api/quality/rules/{rule_name}
```

### 告警管理

#### 获取告警历史
```http
GET /api/quality/alerts?entity_id=entity_123&severity=critical&limit=100
```

#### 获取告警统计
```http
GET /api/quality/alerts/statistics?days=7
```

#### 配置告警
```http
POST /api/quality/alerts/configure
Content-Type: application/json

{
  "email": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "username": "user@example.com",
    "password": "password",
    "from_email": "quality@example.com",
    "to_emails": ["admin@example.com"]
  },
  "webhook": {
    "url": "https://webhook.example.com/alerts",
    "method": "POST"
  }
}
```

### 趋势分析

#### 获取实体质量趋势
```http
GET /api/quality/trend/{entity_id}?days=30
```

## 配置说明

### 主配置文件 (`config/config.yaml`)

```yaml
quality:
  # 规则配置文件路径
  rules_file: "config/quality_rules.yaml"
  
  # 是否启用质量管理
  enabled: true
  
  # 自动评估配置
  auto_assess:
    enabled: true
    on_entity_update: true
    batch_assess_interval: 3600
  
  # 告警配置
  alerts:
    enabled: true
    channels:
      - log
```

### 规则配置文件 (`config/quality_rules.yaml`)

详见 `config/quality_rules.yaml` 文件，包含：
- 规则定义
- 告警配置
- 评分权重配置

## 使用示例

### Python 代码示例

```python
from src.core.quality_rules import QualityRuleEngine
from src.core.quality_assessor import QualityAssessor
from src.core.quality_monitor import QualityMonitor
from src.core.graph import GraphStore
from src.core.models import MetadataEntity

# 初始化
graph_store = GraphStore()
rule_engine = QualityRuleEngine()
assessor = QualityAssessor(rule_engine, graph_store)
monitor = QualityMonitor(assessor)

# 评估实体
entity = MetadataEntity(
    id="table_1",
    type="table",
    name="users",
    source="postgres"
)

score = assessor.assess_entity(entity)
print(f"综合评分: {score.overall_score:.2f}")
print(f"质量等级: {score.get_quality_level()}")

# 监控告警
alerts = monitor.monitor_entity(entity.id, score)
if alerts:
    print(f"发现 {len(alerts)} 个告警")

# 批量评估
entities = [entity1, entity2, entity3]
scores = assessor.assess_batch(entities)
metrics = assessor.calculate_metrics(scores)
print(f"平均评分: {metrics.average_overall:.2f}")
```

## 扩展性

### 添加自定义规则

1. **通过配置文件**
   ```yaml
   - type: custom_python
     name: my_custom_rule
     dimension: accuracy
     expression: "entity.properties.get('status') == 'active'"
   ```

2. **通过代码**
   ```python
   from src.core.quality_rules import QualityRule, QualityDimension, RuleSeverity

   class MyCustomRule(QualityRule):
       def evaluate(self, entity, context=None):
           # 自定义评估逻辑
           if some_condition:
               return QualityIssue(...)
           return None
   
   rule_engine.add_rule(MyCustomRule(...))
   ```

### 添加自定义告警渠道

```python
from src.core.quality_monitor import AlertChannel

# 注册 WebSocket 回调
def my_websocket_handler(alert):
    # 发送告警到 WebSocket
    pass

monitor.register_websocket_callback(my_websocket_handler)
```

## 性能考虑

1. **批量评估**: 支持批量评估以提高性能
2. **规则缓存**: 规则引擎缓存已编译的规则
3. **异步处理**: 告警发送支持异步处理
4. **增量评估**: 支持增量质量评估，只评估变更的实体

## 最佳实践

1. **规则设计**
   - 从关键规则开始，逐步细化
   - 合理设置规则严重程度
   - 定期审查和优化规则

2. **告警配置**
   - 避免告警风暴，合理设置阈值
   - 使用不同渠道处理不同级别的告警
   - 定期审查告警历史

3. **质量改进**
   - 定期分析质量趋势
   - 识别质量问题模式
   - 制定质量改进计划

## 未来改进

1. **机器学习集成**
   - 使用 ML 模型预测质量问题
   - 自动规则生成

2. **质量报告**
   - 生成质量报告（PDF/HTML）
   - 质量仪表板可视化

3. **质量工作流**
   - 质量问题跟踪
   - 质量改进任务管理

4. **数据质量修复建议**
   - 自动生成修复建议
   - 批量修复工具

## 总结

本质量管理系统提供了完整的元数据质量评估、监控和告警功能，支持灵活的规则配置和扩展，能够帮助用户及时发现和解决元数据质量问题，提升整体数据质量水平。

