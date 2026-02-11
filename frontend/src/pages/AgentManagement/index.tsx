/**
 * 采集代理管理页面
 * 可视化控制采集代理的启停、配置、监控
 */
import { useState, useEffect } from 'react';
import { Card, Table, Button, Space, Tag, Modal, Form, Input, Select, Switch, message, Row, Col } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined, ReloadOutlined, SettingOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

interface Agent {
  id: string;
  name: string;
  type: 'lightweight' | 'cluster' | 'cloud_native';
  status: 'running' | 'stopped' | 'error';
  host: string;
  port: number;
  last_heartbeat?: string;
  config: {
    collector_types: string[];
    frequency: number;
    incremental_watermark?: string;
  };
}

export default function AgentManagement() {
  const { t } = useTranslation();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadAgents();
    // 定期刷新代理状态
    const interval = setInterval(loadAgents, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadAgents = async () => {
    try {
      setLoading(true);
      // 这里应该调用实际的API
      // const response = await api.agents.list();
      // setAgents(response.data.agents);
      
      // 模拟数据
      setAgents([
        {
          id: 'agent_1',
          name: '主节点采集代理',
          type: 'lightweight',
          status: 'running',
          host: '192.168.1.100',
          port: 8080,
          last_heartbeat: new Date().toISOString(),
          config: {
            collector_types: ['filesystem', 'code'],
            frequency: 3600,
          },
        },
      ]);
    } catch (err) {
      message.error(t('agents.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async (agentId: string) => {
    try {
      // await api.agents.start(agentId);
      message.success(t('agents.startSuccess'));
      loadAgents();
    } catch (err) {
      message.error(t('agents.startFailed'));
    }
  };

  const handleStop = async (agentId: string) => {
    try {
      // await api.agents.stop(agentId);
      message.success(t('agents.stopSuccess'));
      loadAgents();
    } catch (err) {
      message.error(t('agents.stopFailed'));
    }
  };

  const handleEdit = (agent: Agent) => {
    setEditingAgent(agent);
    form.setFieldsValue(agent.config);
    setModalVisible(true);
  };

  const handleSaveConfig = async () => {
    try {
      const values = await form.validateFields();
      if (editingAgent) {
        // await api.agents.updateConfig(editingAgent.id, values);
        message.success(t('agents.configUpdated'));
        setModalVisible(false);
        setEditingAgent(null);
        loadAgents();
      }
    } catch (err) {
      console.error('保存配置失败:', err);
    }
  };

  const handleDelete = async (agentId: string) => {
    Modal.confirm({
      title: t('agents.confirmDelete'),
      content: t('agents.confirmDeleteMessage'),
      onOk: async () => {
        try {
          // await api.agents.delete(agentId);
          message.success(t('agents.deleteSuccess'));
          loadAgents();
        } catch (err) {
          message.error(t('agents.deleteFailed'));
        }
      },
    });
  };

  const columns = [
    {
      title: t('agents.agentName'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('common.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => {
        const typeMap: Record<string, { text: string; color: string }> = {
          lightweight: { text: t('agents.lightweight'), color: 'blue' },
          cluster: { text: t('agents.cluster'), color: 'green' },
          cloud_native: { text: t('agents.cloudNative'), color: 'purple' },
        };
        const info = typeMap[type] || { text: type, color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: t('common.status'),
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          running: { text: t('agents.running'), color: 'success' },
          stopped: { text: t('agents.stopped'), color: 'default' },
          error: { text: t('agents.error'), color: 'error' },
        };
        const info = statusMap[status] || { text: status, color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    {
      title: t('agents.address'),
      key: 'address',
      render: (_: any, record: Agent) => `${record.host}:${record.port}`,
    },
    {
      title: t('agents.lastHeartbeat'),
      dataIndex: 'last_heartbeat',
      key: 'last_heartbeat',
      render: (time: string) => (time ? new Date(time).toLocaleString() : '-'),
    },
    {
      title: t('common.actions'),
      key: 'action',
      render: (_: any, record: Agent) => (
        <Space>
          {record.status === 'running' ? (
            <Button
              size="small"
              icon={<PauseCircleOutlined />}
              onClick={() => handleStop(record.id)}
            >
              {t('agents.stop')}
            </Button>
          ) : (
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => handleStart(record.id)}
            >
              {t('agents.start')}
            </Button>
          )}
          <Button
            size="small"
            icon={<SettingOutlined />}
            onClick={() => handleEdit(record)}
          >
            {t('agents.config')}
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record.id)}
          >
            {t('common.delete')}
          </Button>
        </Space>
      ),
    },
  ];

  const runningCount = agents.filter((a) => a.status === 'running').length;
  const stoppedCount = agents.filter((a) => a.status === 'stopped').length;
  const errorCount = agents.filter((a) => a.status === 'error').length;

  return (
    <div>
      <Card title={t('agents.title')} extra={<Button icon={<ReloadOutlined />} onClick={loadAgents}>{t('common.refresh')}</Button>}>
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('agents.totalAgents')}</span>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{agents.length}</span>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('agents.running')}</span>
                <span style={{ fontSize: 20, fontWeight: 600, color: '#3f8600' }}>{runningCount}</span>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('agents.stopped')}</span>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{stoppedCount}</span>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('agents.error')}</span>
                <span style={{ fontSize: 20, fontWeight: 600, color: '#cf1322' }}>{errorCount}</span>
              </div>
            </Card>
          </Col>
        </Row>
        <Table
          columns={columns}
          dataSource={agents}
          rowKey="id"
          loading={loading}
        />
      </Card>
      <Modal
        title={t('agents.configAgent')}
        open={modalVisible}
        onOk={handleSaveConfig}
        onCancel={() => {
          setModalVisible(false);
          setEditingAgent(null);
        }}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="frequency"
            label={t('agents.collectionFrequency')}
            rules={[{ required: true, message: t('agents.pleaseInputFrequency') }]}
          >
            <Input type="number" />
          </Form.Item>
          <Form.Item
            name="collector_types"
            label={t('agents.collectorTypes')}
            rules={[{ required: true, message: t('agents.pleaseSelectCollectorTypes') }]}
          >
            <Select mode="multiple">
              <Select.Option value="filesystem">{t('agents.filesystem')}</Select.Option>
              <Select.Option value="code">{t('agents.code')}</Select.Option>
              <Select.Option value="relational">{t('agents.relational')}</Select.Option>
              <Select.Option value="graphdb">{t('agents.graphdb')}</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="incremental_watermark" label={t('agents.incrementalWatermark')}>
            <Input placeholder={t('agents.incrementalWatermarkPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}


