import { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Button,
  Space,
  Tag,
  Progress,
  Statistic,
  Tabs,
  Form,
  Input,
  Select,
  Modal,
  message,
  Alert,
  Descriptions,
  Badge,
  Tree,
  Radio,
  Checkbox,
  Spin,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  PlusOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import type { ColumnsType } from 'antd/es/table';

const { TabPane } = Tabs;
const { TextArea } = Input;

interface QualityScore {
  entity_id: string;
  entity_type: string;
  completeness_score: number;
  accuracy_score: number;
  consistency_score: number;
  freshness_score: number;
  overall_score: number;
  quality_level: string;
  assessed_at: string;
}

interface QualityRule {
  name: string;
  dimension: string;
  severity: string;
  enabled: boolean;
  description: string;
}

interface QualityAlert {
  entity_id: string;
  rule_name: string;
  severity: string;
  score: any;
  timestamp: string;
}

export default function QualityManagement() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [metrics, setMetrics] = useState<any>(null);
  const [rules, setRules] = useState<QualityRule[]>([]);
  const [alerts, setAlerts] = useState<QualityAlert[]>([]);
  const [alertStats, setAlertStats] = useState<any>(null);
  const [scores, setScores] = useState<QualityScore[]>([]);
  const [scoresLoading, setScoresLoading] = useState(false);
  const [ruleModalVisible, setRuleModalVisible] = useState(false);
  const [assessModalVisible, setAssessModalVisible] = useState(false);
  const [assessMode, setAssessMode] = useState<'id' | 'type' | 'tree'>('id');
  const [entityTypes, setEntityTypes] = useState<string[]>([]);
  const [entityTree, setEntityTree] = useState<any[]>([]);
  const [selectedTreeKeys, setSelectedTreeKeys] = useState<React.Key[]>([]);
  const [treeLoading, setTreeLoading] = useState(false);
  const [form] = Form.useForm();
  const [assessForm] = Form.useForm();

  useEffect(() => {
    loadMetrics();
    loadRules();
    loadAlerts();
    loadAlertStatistics();
    loadEntityTypes();
    loadScores();
  }, []);

  const loadEntityTypes = async () => {
    try {
      // 从统计API获取实体类型
      const statsResponse = await api.statistics.get();
      if (statsResponse.data?.sqlite?.entity_type_count) {
        // 尝试从实体列表获取类型
        const entitiesResponse = await api.entities.list({ limit: 1000 });
        const types = new Set<string>();
        entitiesResponse.data.entities.forEach((entity: any) => {
          if (entity.type) {
            types.add(entity.type);
          }
        });
        setEntityTypes(Array.from(types));
      }
    } catch (err: any) {
      console.error('加载实体类型失败:', err);
    }
  };

  const loadEntityTree = async (entityType?: string) => {
    try {
      setTreeLoading(true);
      const response = await api.entities.list({
        entity_type: entityType,
        limit: 1000,
      });
      
      // 按类型组织实体树
      const treeData: any = {};
      response.data.entities.forEach((entity: any) => {
        const type = entity.type || 'unknown';
        if (!treeData[type]) {
          treeData[type] = {
            title: type,
            key: `type-${type}`,
            type: 'type',
            children: [],
          };
        }
        treeData[type].children.push({
          title: `${entity.name} (${entity.id})`,
          key: entity.id,
          type: 'entity',
          entity,
        });
      });
      
      setEntityTree(Object.values(treeData));
    } catch (err: any) {
      message.error('加载实体树失败: ' + err.message);
    } finally {
      setTreeLoading(false);
    }
  };

  const loadMetrics = async () => {
    try {
      setLoading(true);
      const response = await api.quality.getMetrics();
      setMetrics(response.data);
    } catch (err: any) {
      message.error('加载质量指标失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadRules = async () => {
    try {
      const response = await api.quality.getRules();
      setRules(response.data.rules || []);
    } catch (err: any) {
      message.error('加载规则失败: ' + err.message);
    }
  };

  const loadAlerts = async () => {
    try {
      const response = await api.quality.getAlerts({ limit: 100 });
      setAlerts(response.data.alerts || []);
    } catch (err: any) {
      message.error('加载告警失败: ' + err.message);
    }
  };

  const loadAlertStatistics = async () => {
    try {
      const response = await api.quality.getAlertStatistics(7);
      setAlertStats(response.data);
    } catch (err: any) {
      // 忽略错误
    }
  };

  const loadScores = async () => {
    try {
      setScoresLoading(true);
      const response = await api.quality.getScores({ limit: 100 });
      if (response.data.scores) {
        setScores(response.data.scores);
      }
    } catch (err: any) {
      // 如果评估结果未持久化，忽略错误
      console.log('加载评估结果:', err.message);
    } finally {
      setScoresLoading(false);
    }
  };

  const handleAssessEntity = async (values: any) => {
    try {
      setLoading(true);
      
      if (assessMode === 'id') {
        // 单个ID评估
        const response = await api.quality.assessEntity(values.entity_id);
        message.success('评估完成');
        
        // 保存评估结果到本地状态
        if (response.data.score) {
          setScores((prevScores) => {
            const scoreMap = new Map(prevScores.map(s => [s.entity_id, s]));
            scoreMap.set(response.data.score.entity_id, response.data.score);
            return Array.from(scoreMap.values());
          });
        }
        
        Modal.info({
          title: '质量评估结果',
          width: 600,
          content: (
            <Descriptions column={1} bordered>
              <Descriptions.Item label="综合评分">
                <Progress
                  percent={Math.round(response.data.score.overall_score * 100)}
                  status={response.data.score.overall_score >= 0.7 ? 'success' : 'exception'}
                />
                {response.data.score.overall_score.toFixed(2)}
              </Descriptions.Item>
              <Descriptions.Item label="质量等级">
                <Tag color={getQualityLevelColor(response.data.score.quality_level)}>
                  {response.data.score.quality_level}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="完整性">
                {(response.data.score.completeness_score * 100).toFixed(1)}%
              </Descriptions.Item>
              <Descriptions.Item label="准确性">
                {(response.data.score.accuracy_score * 100).toFixed(1)}%
              </Descriptions.Item>
              <Descriptions.Item label="一致性">
                {(response.data.score.consistency_score * 100).toFixed(1)}%
              </Descriptions.Item>
              <Descriptions.Item label="新鲜度">
                {(response.data.score.freshness_score * 100).toFixed(1)}%
              </Descriptions.Item>
              {response.data.alerts.length > 0 && (
                <Descriptions.Item label="告警">
                  <Alert
                    message={`发现 ${response.data.alerts.length} 个问题`}
                    type="warning"
                    showIcon
                  />
                </Descriptions.Item>
              )}
            </Descriptions>
          ),
        });
        loadScores();
      } else if (assessMode === 'type') {
        // 按类型批量评估
        const response = await api.quality.assessBatch({
          entity_type: values.entity_type,
          source: values.source,
        });
        message.success(`批量评估完成，共评估 ${response.data.count} 个实体`);
        
        // 保存评估结果到本地状态
        if (response.data.scores && response.data.scores.length > 0) {
          // 合并新的评估结果到现有列表（去重）
          setScores((prevScores) => {
            const scoreMap = new Map(prevScores.map(s => [s.entity_id, s]));
            response.data.scores.forEach((score: QualityScore) => {
              scoreMap.set(score.entity_id, score);
            });
            return Array.from(scoreMap.values());
          });
        }
        
        Modal.info({
          title: '批量评估结果',
          width: 600,
          content: (
            <Descriptions column={1} bordered>
              <Descriptions.Item label="评估数量">{response.data.count}</Descriptions.Item>
              <Descriptions.Item label="平均综合评分">
                {(response.data.metrics.average_overall * 100).toFixed(1)}%
              </Descriptions.Item>
              <Descriptions.Item label="优秀数量">{response.data.metrics.excellent_count}</Descriptions.Item>
              <Descriptions.Item label="良好数量">{response.data.metrics.good_count}</Descriptions.Item>
              <Descriptions.Item label="一般数量">{response.data.metrics.fair_count}</Descriptions.Item>
              <Descriptions.Item label="较差数量">{response.data.metrics.poor_count}</Descriptions.Item>
              <Descriptions.Item label="严重数量">{response.data.metrics.critical_count}</Descriptions.Item>
            </Descriptions>
          ),
        });
        loadMetrics();
        loadAlerts();
        loadScores();
      } else if (assessMode === 'tree') {
        // 树形选择评估
        const entityIds = selectedTreeKeys
          .filter((key) => {
            const keyStr = String(key);
            return !keyStr.startsWith('type-');
          })
          .map((key) => String(key));
        
        if (entityIds.length === 0) {
          message.warning('请至少选择一个实体');
          setLoading(false);
          return;
        }
        
        const response = await api.quality.assessBatch({
          entity_ids: entityIds,
        });
        message.success(`批量评估完成，共评估 ${response.data.count} 个实体`);
        
        // 保存评估结果到本地状态
        if (response.data.scores && response.data.scores.length > 0) {
          // 合并新的评估结果到现有列表（去重）
          setScores((prevScores) => {
            const scoreMap = new Map(prevScores.map(s => [s.entity_id, s]));
            response.data.scores.forEach((score: QualityScore) => {
              scoreMap.set(score.entity_id, score);
            });
            return Array.from(scoreMap.values());
          });
        }
        
        Modal.info({
          title: '批量评估结果',
          width: 600,
          content: (
            <Descriptions column={1} bordered>
              <Descriptions.Item label="评估数量">{response.data.count}</Descriptions.Item>
              <Descriptions.Item label="平均综合评分">
                {(response.data.metrics.average_overall * 100).toFixed(1)}%
              </Descriptions.Item>
              <Descriptions.Item label="优秀数量">{response.data.metrics.excellent_count}</Descriptions.Item>
              <Descriptions.Item label="良好数量">{response.data.metrics.good_count}</Descriptions.Item>
              <Descriptions.Item label="一般数量">{response.data.metrics.fair_count}</Descriptions.Item>
              <Descriptions.Item label="较差数量">{response.data.metrics.poor_count}</Descriptions.Item>
              <Descriptions.Item label="严重数量">{response.data.metrics.critical_count}</Descriptions.Item>
            </Descriptions>
          ),
        });
        loadMetrics();
        loadAlerts();
        loadScores();
      }
      
      setAssessModalVisible(false);
      assessForm.resetFields();
      setSelectedTreeKeys([]);
      // 刷新质量指标和告警
      loadMetrics();
      loadAlerts();
      loadScores();
    } catch (err: any) {
      message.error('评估失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleBatchAssess = async (values: any) => {
    try {
      setLoading(true);
      const response = await api.quality.assessBatch(values);
      message.success(`批量评估完成，共评估 ${response.data.count} 个实体`);
      loadMetrics();
    } catch (err: any) {
      message.error('批量评估失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleRule = async (ruleName: string, enabled: boolean) => {
    try {
      if (enabled) {
        await api.quality.enableRule(ruleName);
      } else {
        await api.quality.disableRule(ruleName);
      }
      message.success('规则状态已更新');
      loadRules();
    } catch (err: any) {
      message.error('更新规则状态失败: ' + err.message);
    }
  };

  const handleDeleteRule = async (ruleName: string) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除规则 "${ruleName}" 吗？`,
      onOk: async () => {
        try {
          await api.quality.deleteRule(ruleName);
          message.success('规则已删除');
          loadRules();
        } catch (err: any) {
          message.error('删除规则失败: ' + err.message);
        }
      },
    });
  };

  const getQualityLevelColor = (level: string) => {
    const colors: Record<string, string> = {
      excellent: 'green',
      good: 'blue',
      fair: 'orange',
      poor: 'volcano',
      critical: 'red',
    };
    return colors[level] || 'default';
  };

  const getSeverityColor = (severity: string) => {
    const colors: Record<string, string> = {
      critical: 'red',
      high: 'orange',
      medium: 'blue',
      low: 'default',
    };
    return colors[severity] || 'default';
  };

  const ruleColumns: ColumnsType<QualityRule> = [
    {
      title: t('quality.ruleName'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('quality.dimension'),
      dataIndex: 'dimension',
      key: 'dimension',
    },
    {
      title: t('quality.severity'),
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{severity}</Tag>
      ),
    },
    {
      title: t('common.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Badge status={enabled ? 'success' : 'default'} text={enabled ? t('common.enabled') : t('common.disabled')} />
      ),
    },
    {
      title: t('common.description'),
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: t('common.actions'),
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            onClick={() => handleToggleRule(record.name, !record.enabled)}
          >
            {record.enabled ? t('common.disabled') : t('common.enabled')}
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteRule(record.name)}
          >
            {t('quality.deleteRule')}
          </Button>
        </Space>
      ),
    },
  ];

  const alertColumns: ColumnsType<QualityAlert> = [
    {
      title: '实体ID',
      dataIndex: 'entity_id',
      key: 'entity_id',
      ellipsis: true,
    },
    {
      title: '规则名称',
      dataIndex: 'rule_name',
      key: 'rule_name',
    },
    {
      title: '严重程度',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{severity}</Tag>
      ),
    },
    {
      title: '综合评分',
      key: 'score',
      render: (_, record) => (
        <span>
          {record.score?.overall_score
            ? (record.score.overall_score * 100).toFixed(1) + '%'
            : '-'}
        </span>
      ),
    },
    {
      title: '时间',
      dataIndex: 'timestamp',
      key: 'timestamp',
      render: (timestamp: string) => new Date(timestamp).toLocaleString(),
    },
  ];

  const scoreColumns: ColumnsType<QualityScore> = [
    {
      title: t('quality.columns.entityId'),
      dataIndex: 'entity_id',
      key: 'entity_id',
      ellipsis: true,
    },
    {
      title: t('quality.columns.entityType'),
      dataIndex: 'entity_type',
      key: 'entity_type',
    },
    {
      title: t('quality.columns.overallScore'),
      dataIndex: 'overall_score',
      key: 'overall_score',
      render: (score: number) => (
        <Progress
          percent={Math.round(score * 100)}
          status={score >= 0.7 ? 'success' : 'exception'}
          format={(percent) => `${(score * 100).toFixed(1)}%`}
        />
      ),
      sorter: (a, b) => a.overall_score - b.overall_score,
    },
    {
      title: t('quality.columns.qualityLevel'),
      dataIndex: 'quality_level',
      key: 'quality_level',
      render: (level: string) => (
        <Tag color={getQualityLevelColor(level)}>{level}</Tag>
      ),
    },
    {
      title: t('quality.columns.completeness'),
      dataIndex: 'completeness_score',
      key: 'completeness_score',
      render: (score: number) => `${(score * 100).toFixed(1)}%`,
    },
    {
      title: t('quality.columns.accuracy'),
      dataIndex: 'accuracy_score',
      key: 'accuracy_score',
      render: (score: number) => `${(score * 100).toFixed(1)}%`,
    },
    {
      title: t('quality.columns.consistency'),
      dataIndex: 'consistency_score',
      key: 'consistency_score',
      render: (score: number) => `${(score * 100).toFixed(1)}%`,
    },
    {
      title: t('quality.columns.freshness'),
      dataIndex: 'freshness_score',
      key: 'freshness_score',
      render: (score: number) => `${(score * 100).toFixed(1)}%`,
    },
    {
      title: t('quality.columns.assessedAt'),
      dataIndex: 'assessed_at',
      key: 'assessed_at',
      render: (timestamp: string) => new Date(timestamp).toLocaleString(),
      sorter: (a, b) => new Date(a.assessed_at).getTime() - new Date(b.assessed_at).getTime(),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>{t('quality.title')}</h1>
        <Button icon={<ReloadOutlined />} onClick={loadMetrics}>
          {t('common.refresh')}
        </Button>
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={() => setAssessModalVisible(true)}
        >
          {t('quality.assess')}
        </Button>
      </Space>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('quality.averageOverallScore')}</span>
              <span style={{ fontSize: 20, fontWeight: 600, color: metrics?.average_overall >= 0.7 ? '#3f8600' : '#cf1322' }}>
                {metrics?.average_overall ? (metrics.average_overall * 100).toFixed(1) : 0}%
              </span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('quality.assessedCount')}</span>
              <span style={{ fontSize: 20, fontWeight: 600 }}>
                {metrics?.assessed_entities || 0} / {metrics?.total_entities || 0}
              </span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CheckCircleOutlined style={{ fontSize: 18, color: '#3f8600' }} />
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('quality.excellentCount')}</span>
              </div>
              <span style={{ fontSize: 20, fontWeight: 600, color: '#3f8600' }}>{metrics?.excellent_count || 0}</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <WarningOutlined style={{ fontSize: 18, color: '#cf1322' }} />
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('quality.criticalCount')}</span>
              </div>
              <span style={{ fontSize: 20, fontWeight: 600, color: '#cf1322' }}>{metrics?.critical_count || 0}</span>
            </div>
          </Card>
        </Col>
      </Row>

      <Tabs defaultActiveKey="metrics">
        <TabPane tab={t('quality.metrics')} key="metrics">
          {metrics && (
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={12}>
                <Card title={t('quality.metrics')}>
                  <Space direction="vertical" style={{ width: '100%' }} size="large">
                    <div>
                      <div style={{ marginBottom: 8 }}>{t('quality.completeness')}</div>
                      <Progress
                        percent={Math.round(metrics.average_completeness * 100)}
                        status={metrics.average_completeness >= 0.7 ? 'success' : 'exception'}
                      />
                    </div>
                    <div>
                      <div style={{ marginBottom: 8 }}>{t('quality.accuracy')}</div>
                      <Progress
                        percent={Math.round(metrics.average_accuracy * 100)}
                        status={metrics.average_accuracy >= 0.7 ? 'success' : 'exception'}
                      />
                    </div>
                    <div>
                      <div style={{ marginBottom: 8 }}>{t('quality.consistency')}</div>
                      <Progress
                        percent={Math.round(metrics.average_consistency * 100)}
                        status={metrics.average_consistency >= 0.7 ? 'success' : 'exception'}
                      />
                    </div>
                    <div>
                      <div style={{ marginBottom: 8 }}>{t('quality.freshness')}</div>
                      <Progress
                        percent={Math.round(metrics.average_freshness * 100)}
                        status={metrics.average_freshness >= 0.7 ? 'success' : 'exception'}
                      />
                    </div>
                  </Space>
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card title={t('quality.qualityLevel')}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Statistic title={t('quality.excellentCount')} value={metrics.excellent_count} valueStyle={{ color: '#3f8600' }} />
                    </Col>
                    <Col span={12}>
                      <Statistic title={t('quality.goodCount')} value={metrics.good_count} valueStyle={{ color: '#1890ff' }} />
                    </Col>
                    <Col span={12}>
                      <Statistic title={t('quality.fairCount')} value={metrics.fair_count} valueStyle={{ color: '#faad14' }} />
                    </Col>
                    <Col span={12}>
                      <Statistic title={t('quality.poorCount')} value={metrics.poor_count} valueStyle={{ color: '#fa8c16' }} />
                    </Col>
                    <Col span={12}>
                      <Statistic title={t('quality.criticalCount')} value={metrics.critical_count} valueStyle={{ color: '#cf1322' }} />
                    </Col>
                  </Row>
                </Card>
              </Col>
            </Row>
          )}
        </TabPane>

        <TabPane tab={t('quality.rules')} key="rules">
          <Card
            title={t('quality.rules')}
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setRuleModalVisible(true)}>
                {t('quality.createRule')}
              </Button>
            }
          >
            <Table
              columns={ruleColumns}
              dataSource={rules}
              rowKey="name"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={t('quality.scores')} key="scores">
          <Card
            title={t('quality.scores')}
            extra={
              <Button icon={<ReloadOutlined />} onClick={loadScores}>
                {t('common.refresh')}
              </Button>
            }
          >
            <Table
              columns={scoreColumns}
              dataSource={scores}
              rowKey="entity_id"
              loading={scoresLoading}
              pagination={{ pageSize: 20 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={t('quality.alerts')} key="alerts">
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col span={24}>
              {alertStats && (
                <Card title={t('quality.alerts')}>
                  <Row gutter={16}>
                    <Col span={6}>
                      <Statistic title={t('quality.alerts')} value={alertStats.total_alerts} />
                    </Col>
                    <Col span={18}>
                      <div style={{ marginTop: 16 }}>
                        <strong>{t('quality.severity')}:</strong>
                        {Object.entries(alertStats.severity_distribution || {}).map(([key, value]: [string, any]) => (
                          <Tag key={key} color={getSeverityColor(key)} style={{ marginLeft: 8 }}>
                            {key}: {value}
                          </Tag>
                        ))}
                      </div>
                    </Col>
                  </Row>
                </Card>
              )}
            </Col>
          </Row>
          <Card title={t('quality.alerts')}>
            <Table
              columns={alertColumns}
              dataSource={alerts}
              rowKey={(record, index) => `${record.entity_id}-${record.rule_name}-${index}`}
              loading={loading}
              pagination={{ pageSize: 20 }}
            />
          </Card>
        </TabPane>
      </Tabs>

      {/* 评估实体模态框 */}
      <Modal
        title={t('quality.assess')}
        open={assessModalVisible}
        onCancel={() => {
          setAssessModalVisible(false);
          assessForm.resetFields();
          setSelectedTreeKeys([]);
          setEntityTree([]);
        }}
        onOk={() => assessForm.submit()}
        confirmLoading={loading}
        width={800}
      >
        <Form form={assessForm} onFinish={handleAssessEntity} layout="vertical">
          <Form.Item label={t('quality.assessMode')}>
            <Radio.Group
              value={assessMode}
              onChange={(e) => {
                setAssessMode(e.target.value);
                assessForm.resetFields();
                setSelectedTreeKeys([]);
                if (e.target.value === 'tree') {
                  loadEntityTree();
                }
              }}
            >
              <Radio value="id">{t('quality.byId')}</Radio>
              <Radio value="type">{t('quality.byType')}</Radio>
              <Radio value="tree">{t('quality.byTree')}</Radio>
            </Radio.Group>
          </Form.Item>

          {assessMode === 'id' && (
            <Form.Item
              name="entity_id"
              label={t('quality.entityId')}
              rules={[{ required: true, message: t('quality.entityId') }]}
            >
              <Input placeholder={t('quality.entityId')} />
            </Form.Item>
          )}

          {assessMode === 'type' && (
            <>
              <Form.Item
                name="entity_type"
                label={t('quality.entityId')}
                rules={[{ required: true, message: t('quality.selectEntityType') }]}
              >
                <Select placeholder={t('quality.selectEntityType')} showSearch allowClear>
                  {entityTypes.map((type) => (
                    <Select.Option key={type} value={type}>
                      {type}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="source" label={t('quality.selectSource')}>
                <Input placeholder={t('quality.selectSource')} />
              </Form.Item>
            </>
          )}

          {assessMode === 'tree' && (
            <Form.Item label={t('quality.selectEntities')}>
              <div style={{ border: '1px solid #d9d9d9', borderRadius: 4, padding: 8, maxHeight: 400, overflow: 'auto' }}>
                <Spin spinning={treeLoading}>
                  {entityTree.length > 0 ? (
                    <Tree
                      checkable
                      checkedKeys={selectedTreeKeys}
                      onCheck={(checkedKeys, info) => {
                        setSelectedTreeKeys(checkedKeys as React.Key[]);
                      }}
                      treeData={entityTree}
                      defaultExpandAll={false}
                      checkStrictly={false}
                    />
                  ) : (
                    <div style={{ textAlign: 'center', padding: 20, color: '#999' }}>
                      {t('quality.loadEntityTreeFailed')}
                    </div>
                  )}
                </Spin>
              </div>
              <div style={{ marginTop: 8, color: '#666', fontSize: 12 }}>
                {t('common.selected')} {selectedTreeKeys.filter((k) => !String(k).startsWith('type-')).length} {t('common.entities')}
                {entityTree.length === 0 && (
                  <Button
                    type="link"
                    size="small"
                    onClick={() => loadEntityTree()}
                    style={{ marginLeft: 8 }}
                  >
                    {t('common.refresh')}
                  </Button>
                )}
              </div>
            </Form.Item>
          )}
        </Form>
      </Modal>

      {/* 添加规则模态框 */}
      <Modal
        title={t('quality.createRule')}
        open={ruleModalVisible}
        onCancel={() => {
          setRuleModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="type" label="规则类型" rules={[{ required: true }]}>
            <Select>
              <Select.Option value="required_field">必填字段</Select.Option>
              <Select.Option value="format">格式验证</Select.Option>
              <Select.Option value="value_range">值域验证</Select.Option>
              <Select.Option value="freshness">新鲜度</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="field_name" label="字段名">
            <Input />
          </Form.Item>
          <Form.Item name="dimension" label="质量维度">
            <Select>
              <Select.Option value="completeness">完整性</Select.Option>
              <Select.Option value="accuracy">准确性</Select.Option>
              <Select.Option value="consistency">一致性</Select.Option>
              <Select.Option value="freshness">新鲜度</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="severity" label="严重程度">
            <Select>
              <Select.Option value="critical">严重</Select.Option>
              <Select.Option value="high">高</Select.Option>
              <Select.Option value="medium">中</Select.Option>
              <Select.Option value="low">低</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

