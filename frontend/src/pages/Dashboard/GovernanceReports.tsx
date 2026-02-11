/**
 * 治理报表体系
 * 预定义的治理报表，可直接作为治理会议材料、架构评审依据、合规与审计输出
 */
import { useState, useEffect } from 'react';
import { Card, Tabs, Table, Button, Space, DatePicker, Select, Row, Col } from 'antd';
import { DownloadOutlined, PrinterOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ReactECharts from 'echarts-for-react';
import api from '../../services/api';

const { RangePicker } = DatePicker;

export default function GovernanceReports() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('overview');
  const [dateRange, setDateRange] = useState<[any, any] | null>(null);

  const tabItems = [
    {
      key: 'overview',
      label: t('reports.metadataOverview'),
      children: <MetadataOverviewReport />,
    },
    {
      key: 'quality',
      label: t('reports.qualityGovernance'),
      children: <QualityGovernanceReport dateRange={dateRange} />,
    },
    {
      key: 'usage',
      label: t('reports.usageBehavior'),
      children: <UsageBehaviorReport dateRange={dateRange} />,
    },
    {
      key: 'lineage',
      label: t('reports.lineageImpact'),
      children: <LineageImpactReport dateRange={dateRange} />,
    },
  ];

  return (
    <div>
      <Card
        title={t('reports.title')}
        extra={
          <Space>
            <RangePicker onChange={(dates) => setDateRange(dates as any)} />
            <Button icon={<DownloadOutlined />}>{t('reports.export')}</Button>
            <Button icon={<PrinterOutlined />}>{t('reports.print')}</Button>
          </Space>
        }
      >
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
    </div>
  );
}

/**
 * 元数据概览报表
 */
function MetadataOverviewReport() {
  const { t } = useTranslation();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    loadOverviewData();
  }, []);

  const loadOverviewData = async () => {
    try {
      const [statsRes, distRes] = await Promise.all([
        api.statistics.get(),
        api.statistics.entityDistribution(),
      ]);

      setData({
        statistics: statsRes.data,
        distribution: distRes.data?.data || [],
      });
    } catch (err) {
      console.error('加载概览数据失败:', err);
    }
  };

  if (!data) return <div>{t('common.loading')}</div>;

  const distributionOption = {
    title: { text: t('reports.entityTypeDistribution') },
    tooltip: { trigger: 'item' },
    series: [
      {
        type: 'pie',
        data: data.distribution.map((item: any) => ({
          value: item.count,
          name: item.type,
        })),
      },
    ],
  };

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <div>{t('reports.entityCount')}</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              {data.statistics?.sqlite?.entity_count || 0}
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div>{t('reports.relationshipCount')}</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              {data.statistics?.sqlite?.relationship_count || 0}
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div>{t('reports.systemCount')}</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              {data.statistics?.sqlite?.source_count || 0}
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <div>{t('reports.typeCount')}</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              {data.statistics?.sqlite?.entity_type_count || 0}
            </div>
          </Card>
        </Col>
      </Row>
      <Card title={t('reports.typeDistribution')} style={{ marginTop: 16 }}>
        <ReactECharts option={distributionOption} style={{ height: '400px' }} />
      </Card>
    </div>
  );
}

/**
 * 质量治理报表
 */
function QualityGovernanceReport({ dateRange }: { dateRange: any }) {
  const { t } = useTranslation();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    loadQualityData();
  }, [dateRange]);

  const loadQualityData = async () => {
    try {
      const [metricsRes, alertsRes] = await Promise.all([
        api.quality.getMetrics(),
        api.quality.getAlertStatistics(),
      ]);

      setData({
        metrics: metricsRes.data,
        alerts: alertsRes.data,
      });
    } catch (err) {
      console.error('加载质量数据失败:', err);
    }
  };

  if (!data) return <div>{t('common.loading')}</div>;

  const qualityTrendOption = {
    title: { text: t('reports.qualityScoreTrend') },
    tooltip: {},
    xAxis: { type: 'category', data: [] },
    yAxis: { type: 'value', max: 100 },
    series: [
      {
        type: 'line',
        data: [],
        name: t('reports.averageQualityScore'),
      },
    ],
  };

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={8}>
          <Card>
            <div>{t('reports.averageQualityScore')}</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              {data.metrics?.average_overall?.toFixed(2) || '0.00'}
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <div>{t('reports.excellentAssets')}</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#52c41a' }}>
              {data.metrics?.excellent_count || 0}
            </div>
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <div>{t('reports.highRiskAssets')}</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#f5222d' }}>
              {data.metrics?.critical_count || 0}
            </div>
          </Card>
        </Col>
      </Row>
      <Card title={t('reports.qualityTrend')} style={{ marginTop: 16 }}>
        <ReactECharts option={qualityTrendOption} style={{ height: '300px' }} />
      </Card>
      <Card title={t('reports.highFrequencyIssues')} style={{ marginTop: 16 }}>
        <Table
          dataSource={[]}
          columns={[
            { title: t('reports.issueType'), dataIndex: 'type' },
            { title: t('reports.count'), dataIndex: 'count' },
            { title: t('reports.severity'), dataIndex: 'severity' },
          ]}
        />
      </Card>
    </div>
  );
}

/**
 * 使用行为报表
 */
function UsageBehaviorReport({ dateRange }: { dateRange: any }) {
  const { t } = useTranslation();
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    loadUsageData();
  }, [dateRange]);

  const loadUsageData = async () => {
    try {
      const usageRes = await api.governance.getUsageAnalytics();
      setData(usageRes.data);
    } catch (err) {
      console.error('加载使用数据失败:', err);
    }
  };

  if (!data) return <div>{t('common.loading')}</div>;

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={12}>
          <Card title={t('reports.popularAssets')}>
            <Table
              dataSource={data.high_usage || []}
              columns={[
                { title: t('reports.assetName'), dataIndex: 'name' },
                { title: t('reports.usageCount'), dataIndex: 'usage_count' },
                { title: t('common.type'), dataIndex: 'type' },
              ]}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card title={t('reports.lowUsageAssets')}>
            <Table
              dataSource={data.low_usage || []}
              columns={[
                { title: t('reports.assetName'), dataIndex: 'name' },
                { title: t('reports.usageCount'), dataIndex: 'usage_count' },
                { title: t('common.type'), dataIndex: 'type' },
              ]}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}

/**
 * 血缘与影响报表
 */
function LineageImpactReport({ dateRange }: { dateRange: any }) {
  const { t } = useTranslation();
  return (
    <div>
      <Card title={t('reports.averageLineageDepth')}>
        <div style={{ fontSize: '24px', fontWeight: 'bold' }}>3.5</div>
      </Card>
      <Card title={t('reports.highImpactNodes')} style={{ marginTop: 16 }}>
        <Table
          dataSource={[]}
          columns={[
            { title: t('reports.nodeName'), dataIndex: 'name' },
            { title: t('reports.impactScope'), dataIndex: 'impact_scope' },
            { title: t('reports.downstreamCount'), dataIndex: 'downstream_count' },
          ]}
        />
      </Card>
    </div>
  );
}

