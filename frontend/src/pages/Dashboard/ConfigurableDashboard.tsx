/**
 * 可配置仪表盘组件
 * 支持用户自定义布局与组件
 */
import { useState, useEffect } from 'react';
import { Card, Row, Col, Button, Modal, Select, Space, message, Input } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import ReactECharts from 'echarts-for-react';
import api from '../../services/api';

interface DashboardWidget {
  id: string;
  type: 'statistic' | 'chart' | 'table' | 'custom';
  title: string;
  config: any;
  position: { x: number; y: number; w: number; h: number };
}

interface ConfigurableDashboardProps {
  role?: 'data_engineer' | 'data_governance' | 'business_analyst' | 'management';
}

export default function ConfigurableDashboard({ role = 'data_engineer' }: ConfigurableDashboardProps) {
  const { t } = useTranslation();
  const [widgets, setWidgets] = useState<DashboardWidget[]>([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingWidget, setEditingWidget] = useState<DashboardWidget | null>(null);

  useEffect(() => {
    loadDashboard();
  }, [role]);

  const loadDashboard = async () => {
    // 加载默认模板
    const defaultWidgets = getDefaultWidgets(role);
    setWidgets(defaultWidgets);
  };

  const handleAddWidget = () => {
    setEditingWidget(null);
    setModalVisible(true);
  };

  const handleSaveWidget = (widget: DashboardWidget) => {
    if (editingWidget) {
      setWidgets(widgets.map((w) => (w.id === widget.id ? widget : w)));
    } else {
      setWidgets([...widgets, widget]);
    }
    setModalVisible(false);
    setEditingWidget(null);
  };

  const handleDeleteWidget = (id: string) => {
    setWidgets(widgets.filter((w) => w.id !== id));
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button icon={<PlusOutlined />} onClick={handleAddWidget}>
          {t('dashboard.addWidget')}
        </Button>
        <Button onClick={() => message.success(t('dashboard.layoutSaved'))}>{t('dashboard.saveLayout')}</Button>
      </div>
      <Row gutter={[16, 16]}>
        {widgets.map((widget) => {
          const titleMap: Record<string, string> = {
            'entity_count': t('dashboard.entityCount'),
            'relationship_count': t('dashboard.relationshipCount'),
            'quality_trend': t('dashboard.qualityTrend'),
          };
          const displayTitle = titleMap[widget.title] || widget.title;
          return (
          <Col key={widget.id} xs={24} sm={12} lg={widget.position.w === 2 ? 12 : 6}>
            <Card
              title={displayTitle}
              extra={
                <Space>
                  <Button
                    type="text"
                    icon={<EditOutlined />}
                    onClick={() => {
                      setEditingWidget(widget);
                      setModalVisible(true);
                    }}
                  />
                  <Button
                    type="text"
                    danger
                    icon={<DeleteOutlined />}
                    onClick={() => handleDeleteWidget(widget.id)}
                  />
                </Space>
              }
            >
              {renderWidget(widget)}
            </Card>
          </Col>
          );
        })}
      </Row>
      <WidgetConfigModal
        visible={modalVisible}
        widget={editingWidget}
        onSave={handleSaveWidget}
        onCancel={() => {
          setModalVisible(false);
          setEditingWidget(null);
        }}
      />
    </div>
  );
}

function renderWidget(widget: DashboardWidget) {
  switch (widget.type) {
    case 'statistic':
      return <StatisticWidget config={widget.config} />;
    case 'chart':
      return <ChartWidget config={widget.config} />;
    case 'table':
      return <TableWidget config={widget.config} />;
    default:
      return <div>{t('dashboard.unknownWidgetType')}</div>;
  }
}

function StatisticWidget({ config }: { config: any }) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    // 加载统计数据
    loadStatistic(config.metric).then(setValue);
  }, [config]);

  return <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{value}</div>;
}

function ChartWidget({ config }: { config: any }) {
  const [data, setData] = useState<any[]>([]);

  useEffect(() => {
    loadChartData(config.chartType).then(setData);
  }, [config]);

  const option = {
    title: { text: config.title },
    tooltip: {},
    xAxis: { data: data.map((d) => d.name) },
    yAxis: {},
    series: [
      {
        type: config.chartType || 'bar',
        data: data.map((d) => d.value),
      },
    ],
  };

  return <ReactECharts option={option} style={{ height: '300px' }} />;
}

function TableWidget({ config }: { config: any }) {
  const { t } = useTranslation();
  return <div>{t('dashboard.tableWidget')}</div>;
}

function WidgetConfigModal({
  visible,
  widget,
  onSave,
  onCancel,
}: {
  visible: boolean;
  widget: DashboardWidget | null;
  onSave: (widget: DashboardWidget) => void;
  onCancel: () => void;
}) {
  const [widgetType, setWidgetType] = useState(widget?.type || 'statistic');
  const [title, setTitle] = useState(widget?.title || '');

  const handleSave = () => {
    const newWidget: DashboardWidget = {
      id: widget?.id || `widget_${Date.now()}`,
      type: widgetType as any,
      title,
      config: {},
      position: widget?.position || { x: 0, y: 0, w: 1, h: 1 },
    };
    onSave(newWidget);
  };

  const { t } = useTranslation();
  return (
    <Modal title={t('dashboard.configWidget')} open={visible} onOk={handleSave} onCancel={onCancel}>
      <Select
        value={widgetType}
        onChange={setWidgetType}
        style={{ width: '100%', marginBottom: 16 }}
      >
        <Select.Option value="statistic">{t('dashboard.statistic')}</Select.Option>
        <Select.Option value="chart">{t('dashboard.chart')}</Select.Option>
        <Select.Option value="table">{t('dashboard.table')}</Select.Option>
      </Select>
      <input
        type="text"
        placeholder={t('dashboard.widgetTitle')}
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        style={{ width: '100%', padding: '8px' }}
      />
    </Modal>
  );
}

function getDefaultWidgets(role: string): DashboardWidget[] {
  // Note: This function is called before component render, so we can't use useTranslation here
  // The titles will be translated in the component render
  const baseWidgets: DashboardWidget[] = [
    {
      id: 'entity_count',
      type: 'statistic',
      title: 'entity_count', // Will be translated in render
      config: { metric: 'entity_count' },
      position: { x: 0, y: 0, w: 1, h: 1 },
    },
    {
      id: 'relationship_count',
      type: 'statistic',
      title: 'relationship_count', // Will be translated in render
      config: { metric: 'relationship_count' },
      position: { x: 1, y: 0, w: 1, h: 1 },
    },
  ];

  if (role === 'data_governance') {
    return [
      ...baseWidgets,
      {
        id: 'quality_trend',
        type: 'chart',
        title: 'quality_trend', // Will be translated in render
        config: { chartType: 'line' },
        position: { x: 0, y: 1, w: 2, h: 1 },
      },
    ];
  }

  return baseWidgets;
}

async function loadStatistic(metric: string): Promise<number> {
  const response = await api.statistics.get();
  return (response.data as any)[metric] || 0;
}

async function loadChartData(chartType: string): Promise<any[]> {
  // 根据图表类型加载数据
  return [];
}

