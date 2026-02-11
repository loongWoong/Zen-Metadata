"""
元数据质量管理系统使用示例
"""
from src.core.quality_rules import QualityRuleEngine, RequiredFieldRule, FreshnessRule, RuleSeverity
from src.core.quality_assessor import QualityAssessor
from src.core.quality_monitor import QualityMonitor, AlertChannel
from src.core.graph import GraphStore
from src.core.models import MetadataEntity, MetadataType
from datetime import datetime, timedelta
import yaml
from pathlib import Path


def example_quality_assessment():
    """示例：质量评估"""
    print("=" * 60)
    print("示例 1: 质量评估")
    print("=" * 60)
    
    # 初始化规则引擎
    rule_engine = QualityRuleEngine()
    
    # 初始化评估器
    graph_store = GraphStore()  # 可选，用于获取关系信息
    assessor = QualityAssessor(rule_engine, graph_store)
    
    # 创建测试实体
    entity = MetadataEntity(
        id="table_users",
        type=MetadataType.TABLE,
        name="users",
        description="用户表",
        source="postgres",
        created_at=datetime.now() - timedelta(days=10),
        updated_at=datetime.now() - timedelta(days=5)
    )
    
    # 评估质量
    score = assessor.assess_entity(entity)
    
    print(f"实体ID: {score.entity_id}")
    print(f"完整性评分: {score.completeness_score:.2f}")
    print(f"准确性评分: {score.accuracy_score:.2f}")
    print(f"一致性评分: {score.consistency_score:.2f}")
    print(f"新鲜度评分: {score.freshness_score:.2f}")
    print(f"综合评分: {score.overall_score:.2f}")
    print(f"质量等级: {score.get_quality_level().value}")
    print()


def example_custom_rules():
    """示例：自定义规则"""
    print("=" * 60)
    print("示例 2: 自定义规则")
    print("=" * 60)
    
    # 初始化规则引擎
    rule_engine = QualityRuleEngine()
    
    # 添加自定义必填字段规则
    rule_engine.add_rule(RequiredFieldRule(
        field_name="description",
        severity=RuleSeverity.MEDIUM
    ))
    
    # 添加新鲜度规则
    rule_engine.add_rule(FreshnessRule(
        max_age_days=30,
        severity=RuleSeverity.MEDIUM
    ))
    
    # 创建测试实体（缺少描述）
    entity = MetadataEntity(
        id="table_orders",
        type=MetadataType.TABLE,
        name="orders",
        description=None,  # 缺少描述
        source="postgres",
        updated_at=datetime.now() - timedelta(days=45)  # 过期数据
    )
    
    # 评估
    assessor = QualityAssessor(rule_engine)
    issues = rule_engine.evaluate_entity(entity)
    
    print(f"实体: {entity.name}")
    print(f"发现问题数: {len(issues)}")
    for issue in issues:
        print(f"  - [{issue.severity}] {issue.message}")
    print()


def example_batch_assessment():
    """示例：批量评估"""
    print("=" * 60)
    print("示例 3: 批量评估")
    print("=" * 60)
    
    rule_engine = QualityRuleEngine()
    assessor = QualityAssessor(rule_engine)
    
    # 创建多个测试实体
    entities = [
        MetadataEntity(
            id=f"table_{i}",
            type=MetadataType.TABLE,
            name=f"table_{i}",
            description=f"表 {i} 的描述" if i % 2 == 0 else None,
            source="postgres",
            updated_at=datetime.now() - timedelta(days=i*5)
        )
        for i in range(1, 6)
    ]
    
    # 批量评估
    scores = assessor.assess_batch(entities)
    
    # 计算指标
    metrics = assessor.calculate_metrics(scores)
    
    print(f"评估实体数: {metrics.assessed_entities}")
    print(f"平均完整性: {metrics.average_completeness:.2f}")
    print(f"平均准确性: {metrics.average_accuracy:.2f}")
    print(f"平均一致性: {metrics.average_consistency:.2f}")
    print(f"平均新鲜度: {metrics.average_freshness:.2f}")
    print(f"平均综合评分: {metrics.average_overall:.2f}")
    print(f"优秀数量: {metrics.excellent_count}")
    print(f"良好数量: {metrics.good_count}")
    print(f"一般数量: {metrics.fair_count}")
    print(f"较差数量: {metrics.poor_count}")
    print(f"严重数量: {metrics.critical_count}")
    print()


def example_quality_monitoring():
    """示例：质量监控和告警"""
    print("=" * 60)
    print("示例 4: 质量监控和告警")
    print("=" * 60)
    
    rule_engine = QualityRuleEngine()
    assessor = QualityAssessor(rule_engine)
    monitor = QualityMonitor(assessor)
    
    # 创建低质量实体
    entity = MetadataEntity(
        id="table_low_quality",
        type=MetadataType.TABLE,
        name="low_quality_table",
        description=None,
        source="unknown",
        updated_at=datetime.now() - timedelta(days=100)
    )
    
    # 评估
    score = assessor.assess_entity(entity)
    
    # 监控（会自动触发告警）
    alerts = monitor.monitor_entity(entity.id, score)
    
    print(f"实体: {entity.name}")
    print(f"综合评分: {score.overall_score:.2f}")
    print(f"触发告警数: {len(alerts)}")
    for alert in alerts:
        print(f"  - [{alert['severity']}] {alert['rule_name']}")
    print()


def example_load_rules_from_config():
    """示例：从配置文件加载规则"""
    print("=" * 60)
    print("示例 5: 从配置文件加载规则")
    print("=" * 60)
    
    rule_engine = QualityRuleEngine()
    
    # 加载配置文件
    rules_file = Path("config/quality_rules.yaml")
    if rules_file.exists():
        with open(rules_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            rule_engine.load_rules_from_config(config)
        
        print(f"已加载规则数: {len(rule_engine.rules)}")
        print("规则列表:")
        for rule in rule_engine.rules:
            status = "启用" if rule.enabled else "禁用"
            print(f"  - [{status}] {rule.name}: {rule.description}")
    else:
        print(f"配置文件不存在: {rules_file}")
    print()


def example_quality_trend():
    """示例：质量趋势分析"""
    print("=" * 60)
    print("示例 6: 质量趋势分析")
    print("=" * 60)
    
    from src.core.quality_monitor import QualityTrendAnalyzer
    
    rule_engine = QualityRuleEngine()
    assessor = QualityAssessor(rule_engine)
    trend_analyzer = QualityTrendAnalyzer()
    
    entity_id = "table_trend"
    
    # 模拟历史评分记录
    for days_ago in range(30, 0, -5):
        entity = MetadataEntity(
            id=entity_id,
            type=MetadataType.TABLE,
            name="trend_table",
            description="趋势分析表",
            source="postgres",
            updated_at=datetime.now() - timedelta(days=days_ago)
        )
        
        score = assessor.assess_entity(entity)
        trend_analyzer.record_score(entity_id, score)
    
    # 获取趋势
    trend = trend_analyzer.get_trend(entity_id, days=30)
    
    print(f"实体ID: {trend['entity_id']}")
    print(f"趋势: {trend['trend']}")
    print(f"变化率: {trend['change_rate']:.2%}")
    print(f"当前评分: {trend['current_score']:.2f}")
    print(f"初始评分: {trend['initial_score']:.2f}")
    print(f"数据点数: {trend['data_points']}")
    print()


if __name__ == "__main__":
    print("\n元数据质量管理系统使用示例\n")
    
    try:
        example_quality_assessment()
        example_custom_rules()
        example_batch_assessment()
        example_quality_monitoring()
        example_load_rules_from_config()
        example_quality_trend()
        
        print("=" * 60)
        print("所有示例执行完成！")
        print("=" * 60)
    except Exception as e:
        print(f"执行示例时出错: {e}")
        import traceback
        traceback.print_exc()


