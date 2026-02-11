import { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Spin, Alert, Button, Space, Steps, Divider, Typography } from 'antd';
import {
  DatabaseOutlined,
  NodeIndexOutlined,
  LinkOutlined,
  CloudUploadOutlined,
  ApartmentOutlined,
  SyncOutlined,
  SearchOutlined,
  BarChartOutlined,
  RightOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import ReactECharts from 'echarts-for-react';
import api from '../../services/api';
import type { Statistics } from '../../types';

const { Title } = Typography;

export default function Dashboard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [entityDistribution, setEntityDistribution] = useState<any[]>([]);

  useEffect(() => {
    loadStatistics();
    loadEntityDistribution();
  }, []);

  const loadStatistics = async () => {
    try {
      setLoading(true);
      const response = await api.statistics.get();
      setStatistics(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.message || t('dashboard.loadStatisticsError'));
    } finally {
      setLoading(false);
    }
  };

  const loadEntityDistribution = async () => {
    try {
      const response = await api.statistics.entityDistribution();
      setEntityDistribution(response.data?.data || []);
    } catch (err) {
      console.error(t('dashboard.loadEntityDistributionError'), err);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return <Alert message={t('common.error')} description={error} type="error" showIcon />;
  }

  const entityCount = statistics?.sqlite?.entity_count || 0;
  const relationshipCount = statistics?.sqlite?.relationship_count || 0;
  const nodeCount = statistics?.graph?.node_count || 0;
  const edgeCount = statistics?.graph?.edge_count || 0;

  // 主流程步骤配置
  const mainFlowSteps = [
    {
      title: t('dashboard.step1Title'),
      description: t('dashboard.step1Description'),
      icon: <ApartmentOutlined />,
      path: '/metamodel',
      status: 'process' as const,
      action: t('dashboard.step1Action'),
    },
    {
      title: t('dashboard.step2Title'),
      description: t('dashboard.step2Description'),
      icon: <CloudUploadOutlined />,
      path: '/collection',
      status: 'process' as const,
      action: t('dashboard.step2Action'),
    },
    {
      title: t('dashboard.step3Title'),
      description: t('dashboard.step3Description'),
      icon: <SyncOutlined />,
      path: '/entities',
      status: 'process' as const,
      action: t('dashboard.step3Action'),
    },
    {
      title: t('dashboard.step4Title'),
      description: t('dashboard.step4Description'),
      icon: <NodeIndexOutlined />,
      path: '/graph',
      status: 'process' as const,
      action: t('dashboard.step4Action'),
    },
    {
      title: t('dashboard.step5Title'),
      description: t('dashboard.step5Description'),
      icon: <BarChartOutlined />,
      path: '/analytics',
      status: 'process' as const,
      action: t('dashboard.step5Action'),
    },
  ];

  // 根据当前状态判断流程进度
  const getStepStatus = (index: number) => {
    if (index === 0) return 'finish'; // 元模型定义总是可用的
    if (index === 1 && entityCount > 0) return 'finish'; // 有实体说明已采集
    if (index === 2 && relationshipCount > 0) return 'finish'; // 有关系说明已同步
    if (index === 3 && nodeCount > 0) return 'finish'; // 有节点说明已可视化
    if (index === 4 && statistics) return 'finish'; // 有统计说明可分析
    return 'wait';
  };

  // 实体分布饼图配置
  const distributionOption = {
    tooltip: {
      trigger: 'item',
      formatter: '{a} <br/>{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      left: 'left',
      top: 'middle',
      textStyle: {
        fontSize: 12,
      },
    },
    series: [
      {
        name: t('dashboard.entityType'),
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 8,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          fontSize: 11,
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
          },
        },
        data: entityDistribution.map((item: any) => ({
          value: item.count,
          name: item.type || t('common.unknown'),
        })),
      },
    ],
  };

  // 统计对比柱状图配置
  const comparisonOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow',
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      data: [t('dashboard.entity'), t('dashboard.relationship'), t('dashboard.node'), t('dashboard.edge')],
      axisLabel: {
        fontSize: 12,
      },
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        fontSize: 12,
      },
    },
    series: [
      {
        name: t('dashboard.count'),
        type: 'bar',
        barWidth: '60%',
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#83bff6' },
              { offset: 0.5, color: '#188df0' },
              { offset: 1, color: '#188df0' },
            ],
          },
          borderRadius: [4, 4, 0, 0],
        },
        data: [entityCount, relationshipCount, nodeCount, edgeCount],
        label: {
          show: true,
          position: 'top',
          fontSize: 11,
        },
      },
    ],
  };

  return (
    <div style={{ padding: '0 24px' }}>
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>
          {t('dashboard.title')}
        </Title>
      </div>

      {/* 统计信息卡片 - 优化尺寸 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            style={{
              height: '100%',
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <Statistic
              title={t('dashboard.entityCount')}
              value={entityCount}
              prefix={<DatabaseOutlined style={{ fontSize: 24 }} />}
              valueStyle={{ color: '#3f8600', fontSize: 28, fontWeight: 'bold' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            style={{
              height: '100%',
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <Statistic
              title={t('dashboard.relationshipCount')}
              value={relationshipCount}
              prefix={<LinkOutlined style={{ fontSize: 24 }} />}
              valueStyle={{ color: '#1890ff', fontSize: 28, fontWeight: 'bold' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            style={{
              height: '100%',
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <Statistic
              title={t('dashboard.nodeCount')}
              value={nodeCount}
              prefix={<NodeIndexOutlined style={{ fontSize: 24 }} />}
              valueStyle={{ color: '#722ed1', fontSize: 28, fontWeight: 'bold' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card
            hoverable
            style={{
              height: '100%',
              borderRadius: 8,
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            }}
          >
            <Statistic
              title={t('dashboard.edgeCount')}
              value={edgeCount}
              prefix={<LinkOutlined style={{ fontSize: 24 }} />}
              valueStyle={{ color: '#eb2f96', fontSize: 28, fontWeight: 'bold' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 主流程快捷菜单 - 优化布局 */}
      <Card
        title={t('dashboard.mainFlow')}
        style={{ marginBottom: 24, borderRadius: 8 }}
        extra={<Button onClick={loadStatistics}>{t('common.refresh')}</Button>}
      >
        <Steps
          current={mainFlowSteps.findIndex((_, idx) => getStepStatus(idx) === 'wait')}
          items={mainFlowSteps.map((step, index) => ({
            title: step.title,
            description: step.description,
            icon: step.icon,
            status: getStepStatus(index),
          }))}
          style={{ marginBottom: 32 }}
          responsive={false}
        />

        <Divider />

        <div
          style={{
            display: 'flex',
            gap: '12px',
            flexWrap: 'nowrap',
            overflowX: 'auto',
            paddingBottom: '8px',
          }}
        >
          {mainFlowSteps.map((step, index) => (
            <Card
              key={index}
              hoverable
              style={{
                textAlign: 'center',
                borderRadius: 8,
                border: getStepStatus(index) === 'finish' ? '2px solid #52c41a' : '1px solid #d9d9d9',
                transition: 'all 0.3s',
                minHeight: 180,
                flex: '1 1 0',
                minWidth: 0,
              }}
              bodyStyle={{ padding: '16px 12px' }}
              onClick={() => navigate(step.path)}
            >
              <div
                style={{
                  fontSize: 36,
                  marginBottom: 10,
                  color: getStepStatus(index) === 'finish' ? '#52c41a' : '#1890ff',
                  transition: 'transform 0.3s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'scale(1.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'scale(1)';
                }}
              >
                {step.icon}
              </div>
              <h3 style={{ margin: '6px 0', fontSize: 14, fontWeight: 600 }}>{step.title}</h3>
              <p style={{ color: '#8c8c8c', fontSize: 11, marginBottom: 12, minHeight: 28 }}>
                {step.description}
              </p>
              <Button
                type={getStepStatus(index) === 'finish' ? 'default' : 'primary'}
                icon={getStepStatus(index) === 'finish' ? <CheckCircleOutlined /> : <RightOutlined />}
                block
                size="small"
              >
                {step.action}
              </Button>
            </Card>
          ))}
        </div>
      </Card>

      {/* 图表展示区域 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} lg={12}>
          <Card
            title={t('dashboard.entityDistribution')}
            style={{ borderRadius: 8, height: '100%' }}
            bodyStyle={{ padding: '20px' }}
          >
            {entityDistribution.length > 0 ? (
              <ReactECharts
                option={distributionOption}
                style={{ height: '350px', width: '100%' }}
                opts={{ renderer: 'svg' }}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#8c8c8c' }}>
                {t('common.noData')}
              </div>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={t('dashboard.comparison')}
            style={{ borderRadius: 8, height: '100%' }}
            bodyStyle={{ padding: '20px' }}
          >
            <ReactECharts
              option={comparisonOption}
              style={{ height: '350px', width: '100%' }}
              opts={{ renderer: 'svg' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 快速操作和系统信息 - 优化布局 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={t('dashboard.quickActions')}
            style={{ borderRadius: 8, height: '100%' }}
            bodyStyle={{ padding: '20px' }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Button
                type="primary"
                block
                size="large"
                icon={<CloudUploadOutlined />}
                onClick={() => navigate('/collection')}
              >
                {t('dashboard.startCollection')}
              </Button>
              <Button
                block
                size="large"
                icon={<SearchOutlined />}
                onClick={() => navigate('/search')}
              >
                {t('dashboard.searchMetadata')}
              </Button>
              <Button
                block
                size="large"
                icon={<NodeIndexOutlined />}
                onClick={() => navigate('/graph')}
              >
                {t('dashboard.viewGraph')}
              </Button>
              <Button
                block
                size="large"
                icon={<DatabaseOutlined />}
                onClick={() => navigate('/entities')}
              >
                {t('dashboard.viewEntities')}
              </Button>
            </Space>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title={t('dashboard.systemInfo')}
            style={{ borderRadius: 8, height: '100%' }}
            bodyStyle={{ padding: '20px' }}
          >
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#8c8c8c' }}>{t('dashboard.sourceCount')}</span>
                <span style={{ fontSize: 18, fontWeight: 600 }}>
                  {statistics?.sqlite?.source_count || 0}
                </span>
              </div>
              <Divider style={{ margin: '12px 0' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#8c8c8c' }}>{t('dashboard.entityTypeCount')}</span>
                <span style={{ fontSize: 18, fontWeight: 600 }}>
                  {statistics?.sqlite?.entity_type_count || 0}
                </span>
              </div>
              <Divider style={{ margin: '12px 0' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#8c8c8c' }}>{t('dashboard.relationshipTypeCount')}</span>
                <span style={{ fontSize: 18, fontWeight: 600 }}>
                  {statistics?.sqlite?.relationship_type_count || 0}
                </span>
              </div>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
}






