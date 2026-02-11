import { useEffect, useState } from 'react';
import { Card, Row, Col, Spin, Alert, Button } from 'antd';
import { useTranslation } from 'react-i18next';
import ReactECharts from 'echarts-for-react';
import api from '../../services/api';

export default function Analytics() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [entityDistribution, setEntityDistribution] = useState<any[]>([]);
  const [relationshipPatterns, setRelationshipPatterns] = useState<any[]>([]);
  const [centralEntities, setCentralEntities] = useState<any[]>([]);

  useEffect(() => {
    loadAnalytics();
  }, []);

  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);
      const [distRes, relRes, centralRes] = await Promise.all([
        api.statistics.entityDistribution(),
        api.statistics.relationshipPatterns(),
        api.statistics.centralEntities(10),
      ]);
      // 安全地设置数据，处理空数组情况
      setEntityDistribution(distRes.data?.data || []);
      setRelationshipPatterns(relRes.data?.data || []);
      setCentralEntities(centralRes.data?.data || []);
    } catch (err: any) {
      const errorMessage = err?.response?.data?.detail || err?.message || t('analytics.loadFailed');
      setError(errorMessage);
      console.error('加载分析数据失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const entityDistributionOption = {
    title: {
      text: t('analytics.entityDistribution'),
      left: 'center',
    },
    tooltip: {
      trigger: 'item',
    },
    series: [
      {
        type: 'pie',
        radius: '50%',
        data: entityDistribution.map((item) => ({
          value: item.count,
          name: item.type,
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      },
    ],
  };

  const relationshipPatternsOption = {
    title: {
      text: t('analytics.relationshipDistribution'),
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
    },
    xAxis: {
      type: 'category',
      data: relationshipPatterns.map((item) => item.type),
    },
    yAxis: {
      type: 'value',
    },
    series: [
      {
        data: relationshipPatterns.map((item) => item.count),
        type: 'bar',
      },
    ],
  };

  const centralEntitiesOption = {
    title: {
      text: t('analytics.centralEntities'),
      left: 'center',
    },
    tooltip: {
      trigger: 'axis',
    },
    xAxis: {
      type: 'value',
    },
    yAxis: {
      type: 'category',
      data: centralEntities.map((item) => item.name),
    },
    series: [
      {
        data: centralEntities.map((item) => item.connection_count),
        type: 'bar',
        orientation: 'horizontal',
      },
    ],
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <h1>{t('analytics.title')}</h1>
        <Alert
          message={t('common.error')}
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={loadAnalytics}>
              {t('common.retry')}
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div>
      <h1>{t('analytics.title')}</h1>
      {entityDistribution.length === 0 && relationshipPatterns.length === 0 && centralEntities.length === 0 && (
        <Alert
          message={t('common.noData')}
          description={t('analytics.noDataDescription')}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card>
            {entityDistribution.length > 0 ? (
              <ReactECharts option={entityDistributionOption} style={{ height: '400px' }} />
            ) : (
              <div style={{ textAlign: 'center', padding: '100px 0' }}>{t('common.noData')}</div>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card>
            {relationshipPatterns.length > 0 ? (
              <ReactECharts option={relationshipPatternsOption} style={{ height: '400px' }} />
            ) : (
              <div style={{ textAlign: 'center', padding: '100px 0' }}>{t('common.noData')}</div>
            )}
          </Card>
        </Col>
        <Col xs={24}>
          <Card>
            {centralEntities.length > 0 ? (
              <ReactECharts option={centralEntitiesOption} style={{ height: '400px' }} />
            ) : (
              <div style={{ textAlign: 'center', padding: '100px 0' }}>{t('common.noData')}</div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}



