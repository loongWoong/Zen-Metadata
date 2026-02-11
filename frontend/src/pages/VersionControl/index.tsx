/**
 * 版本控制与审计页面
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Tag,
  Space,
  Tabs,
  Alert,
  Spin,
  Descriptions,
  Modal,
  Form,
  InputNumber,
  Select,
  Typography,
  Row,
  Col,
  Statistic,
  Timeline,
  DatePicker,
} from 'antd';
import {
  HistoryOutlined,
  RollbackOutlined,
  FileTextOutlined,
  BarChartOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import type { MetadataEntity } from '../../types';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

interface Version {
  version: number;
  metamodel_version?: string;
  created_at: string;
  created_by?: string;
  change_reason?: string;
}

interface AuditEvent {
  event_id: string;
  entity_id: string;
  operation_type: string;
  operator?: string;
  changed_fields: string[];
  old_value?: any;
  new_value?: any;
  change_reason?: string;
  timestamp: string;
  metadata: any;
}

const VersionControl: React.FC = () => {
  const { t } = useTranslation();
  const [entityId, setEntityId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [versions, setVersions] = useState<Version[]>([]);
  const [currentVersion, setCurrentVersion] = useState<number>(0);
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [versionDiff, setVersionDiff] = useState<any>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [auditStats, setAuditStats] = useState<any>(null);
  const [createVersionModalVisible, setCreateVersionModalVisible] = useState(false);
  const [rollbackModalVisible, setRollbackModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 获取版本列表
  const handleGetVersions = async () => {
    if (!entityId.trim()) {
      return;
    }

    setLoading(true);
    try {
      const response = await api.version.getVersions(entityId);
      setVersions(response.data.versions || []);
      setCurrentVersion(response.data.current_version || 0);
    } catch (error: any) {
      console.error('获取版本列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 对比版本
  const handleDiffVersions = async (v1: number, v2: number) => {
    if (!entityId.trim()) {
      return;
    }

    setLoading(true);
    try {
      const response = await api.version.diffVersions(entityId, v1, v2);
      setVersionDiff(response.data);
      setSelectedVersion(v2);
    } catch (error: any) {
      console.error('对比版本失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 回滚版本
  const handleRollback = async (targetVersion: number) => {
    if (!entityId.trim()) {
      return;
    }

    setLoading(true);
    try {
      await api.version.rollback({
        entity_id: entityId,
        target_version: targetVersion,
      });
      setRollbackModalVisible(false);
      handleGetVersions();
    } catch (error: any) {
      console.error('回滚失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取审计事件
  const handleGetAuditEvents = async (params?: any) => {
    setLoading(true);
    try {
      const response = await api.version.getAuditEvents(params);
      setAuditEvents(response.data.events || []);
    } catch (error: any) {
      console.error('获取审计事件失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 获取审计统计
  const handleGetAuditStats = async (days: number = 30) => {
    setLoading(true);
    try {
      const response = await api.version.getAuditStatistics(days);
      setAuditStats(response.data);
    } catch (error: any) {
      console.error('获取审计统计失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleGetAuditStats(30);
  }, []);

  // 版本表格列
  const versionColumns = [
    {
      title: t('version.versionNumber'),
      dataIndex: 'version',
      key: 'version',
      width: 100,
      render: (version: number) => (
        <Tag color={version === currentVersion ? 'green' : 'default'}>{version}</Tag>
      ),
    },
    {
      title: t('version.metamodelVersion'),
      dataIndex: 'metamodel_version',
      key: 'metamodel_version',
      width: 150,
    },
    {
      title: t('common.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: t('version.createdBy'),
      dataIndex: 'created_by',
      key: 'created_by',
      width: 120,
    },
    {
      title: t('version.changeReason'),
      dataIndex: 'change_reason',
      key: 'change_reason',
    },
    {
      title: t('common.actions'),
      key: 'action',
      width: 200,
      render: (_: any, record: Version) => (
        <Space>
          <Button
            type="link"
            size="small"
            onClick={() => handleDiffVersions(record.version - 1, record.version)}
          >
            {t('version.compare')}
          </Button>
          {record.version < currentVersion && (
            <Button
              type="link"
              size="small"
              danger
              icon={<RollbackOutlined />}
              onClick={() => {
                setSelectedVersion(record.version);
                setRollbackModalVisible(true);
              }}
            >
              {t('version.rollback')}
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // 审计事件表格列
  const auditColumns = [
    {
      title: t('version.eventId'),
      dataIndex: 'event_id',
      key: 'event_id',
      width: 200,
    },
    {
      title: t('version.entityId'),
      dataIndex: 'entity_id',
      key: 'entity_id',
      width: 200,
    },
    {
      title: t('version.operationType'),
      dataIndex: 'operation_type',
      key: 'operation_type',
      width: 120,
      render: (type: string) => {
        const colorMap: Record<string, string> = {
          create: 'green',
          update: 'blue',
          delete: 'red',
        };
        return <Tag color={colorMap[type] || 'default'}>{type}</Tag>;
      },
    },
    {
      title: t('version.operator'),
      dataIndex: 'operator',
      key: 'operator',
      width: 120,
    },
    {
      title: t('version.changedFields'),
      dataIndex: 'changed_fields',
      key: 'changed_fields',
      render: (fields: string[]) => (
        <Space>
          {fields.map((field) => (
            <Tag key={field}>{field}</Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('version.changeReason'),
      dataIndex: 'change_reason',
      key: 'change_reason',
    },
    {
      title: t('common.time'),
      dataIndex: 'timestamp',
      key: 'timestamp',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss'),
      sorter: (a: AuditEvent, b: AuditEvent) =>
        dayjs(a.timestamp).unix() - dayjs(b.timestamp).unix(),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>{t('version.title')}</Title>

      <Card style={{ marginBottom: '24px' }}>
        <Space>
          <Input
            placeholder={t('version.inputEntityId')}
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
            style={{ width: '300px' }}
          />
          <Button type="primary" icon={<HistoryOutlined />} onClick={handleGetVersions} loading={loading}>
            {t('version.viewVersions')}
          </Button>
          <Button icon={<PlusOutlined />} onClick={() => setCreateVersionModalVisible(true)}>
            {t('version.createVersion')}
          </Button>
        </Space>
      </Card>

      <Spin spinning={loading}>
        <Tabs defaultActiveKey="versions">
          <TabPane tab={t('version.versionManagement')} key="versions">
            {versions.length > 0 ? (
              <Card>
                <Descriptions title={t('version.versionInfo')} bordered column={2} style={{ marginBottom: '16px' }}>
                  <Descriptions.Item label={t('version.entityId')}>{entityId}</Descriptions.Item>
                  <Descriptions.Item label={t('version.currentVersion')}>
                    <Tag color="green">{currentVersion}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label={t('version.totalVersions')}>{versions.length}</Descriptions.Item>
                  <Descriptions.Item label={t('version.latestVersionTime')}>
                    {versions[0]?.created_at ? dayjs(versions[0].created_at).format('YYYY-MM-DD HH:mm:ss') : '-'}
                  </Descriptions.Item>
                </Descriptions>

                <Table
                  dataSource={versions}
                  columns={versionColumns}
                  rowKey="version"
                  pagination={{ pageSize: 10 }}
                />

                {versionDiff && (
                  <Card title={t('version.versionCompare')} style={{ marginTop: '24px' }}>
                    <Descriptions bordered column={1}>
                      <Descriptions.Item label={t('version.compareVersions')}>
                        {versionDiff.version1} vs {versionDiff.version2}
                      </Descriptions.Item>
                      {Object.entries(versionDiff.changes || {}).map(([key, change]: [string, any]) => (
                        <Descriptions.Item key={key} label={key}>
                          <Space direction="vertical">
                            <Text type="secondary">{t('version.oldValue')}: {JSON.stringify(change.old)}</Text>
                            <Text>{t('version.newValue')}: {JSON.stringify(change.new)}</Text>
                          </Space>
                        </Descriptions.Item>
                      ))}
                    </Descriptions>
                  </Card>
                )}
              </Card>
            ) : (
              <Alert message={t('version.noVersionData')} type="info" />
            )}
          </TabPane>

          <TabPane tab={t('version.auditLog')} key="audit">
            <Card>
              <Space direction="vertical" style={{ width: '100%' }} size="large">
                <Row gutter={16}>
                  <Col span={6}>
                    <Input
                      placeholder={t('version.entityIdFilter')}
                      onChange={(e) => {
                        if (e.target.value) {
                          handleGetAuditEvents({ entity_id: e.target.value });
                        } else {
                          handleGetAuditEvents();
                        }
                      }}
                    />
                  </Col>
                  <Col span={6}>
                    <Select
                      placeholder={t('version.operationType')}
                      allowClear
                      onChange={(value) => {
                        handleGetAuditEvents(value ? { operation_type: value } : {});
                      }}
                      style={{ width: '100%' }}
                    >
                      <Select.Option value="create">{t('common.create')}</Select.Option>
                      <Select.Option value="update">{t('common.update')}</Select.Option>
                      <Select.Option value="delete">{t('common.delete')}</Select.Option>
                    </Select>
                  </Col>
                  <Col span={12}>
                    <RangePicker
                      showTime
                      onChange={(dates) => {
                        if (dates && dates[0] && dates[1]) {
                          handleGetAuditEvents({
                            start_time: dates[0].toISOString(),
                            end_time: dates[1].toISOString(),
                          });
                        } else {
                          handleGetAuditEvents();
                        }
                      }}
                    />
                  </Col>
                </Row>

                {auditStats && (
                  <Row gutter={16}>
                    <Col span={6}>
                      <Statistic
                        title={t('version.totalEvents')}
                        value={auditStats.total_events}
                        prefix={<FileTextOutlined />}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={t('version.statisticsPeriod')}
                        value={auditStats.period_days}
                        suffix={t('version.days')}
                      />
                    </Col>
                    {Object.entries(auditStats.operation_distribution || {}).map(([type, count]: [string, any]) => (
                      <Col span={6} key={type}>
                        <Statistic title={type} value={count} />
                      </Col>
                    ))}
                  </Row>
                )}

                <Table
                  dataSource={auditEvents}
                  columns={auditColumns}
                  rowKey="event_id"
                  pagination={{ pageSize: 20 }}
                />
              </Space>
            </Card>
          </TabPane>
        </Tabs>
      </Spin>

      {/* 创建版本模态框 */}
      <Modal
        title={t('version.createVersion')}
        open={createVersionModalVisible}
        onCancel={() => setCreateVersionModalVisible(false)}
        onOk={() => {
          form.validateFields().then((values) => {
            // TODO: 实现创建版本逻辑
            setCreateVersionModalVisible(false);
          });
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="entity" label={t('version.entityData')} rules={[{ required: true }]}>
            <TextArea rows={4} placeholder={t('version.inputEntityJson')} />
          </Form.Item>
          <Form.Item name="created_by" label={t('version.createdBy')}>
            <Input />
          </Form.Item>
          <Form.Item name="change_reason" label={t('version.changeReason')}>
            <TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 回滚版本模态框 */}
      <Modal
        title={t('version.rollback')}
        open={rollbackModalVisible}
        onCancel={() => setRollbackModalVisible(false)}
        onOk={() => {
          if (selectedVersion !== null) {
            handleRollback(selectedVersion);
          }
        }}
        okText={t('version.confirmRollback')}
        okButtonProps={{ danger: true }}
      >
        <Alert
          message={t('version.confirmRollbackMessage', { version: selectedVersion })}
          description={t('version.rollbackDescription')}
          type="warning"
          showIcon
        />
      </Modal>
    </div>
  );
};

export default VersionControl;



