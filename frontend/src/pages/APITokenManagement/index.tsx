/**
 * API Token管理页面
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  InputNumber,
  message,
  Space,
  Tag,
  Popconfirm,
} from 'antd';
import { PlusOutlined, DeleteOutlined, CopyOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

interface APIToken {
  id: string;
  name: string;
  permissions: Array<{ resource: string; action: string; scope: string }>;
  expires_at?: string;
  last_used_at?: string;
  created_at: string;
  is_active: boolean;
}

const APITokenManagement: React.FC = () => {
  const { t } = useTranslation();
  const [tokens, setTokens] = useState<APIToken[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [newToken, setNewToken] = useState<string | null>(null);
  const [tokenModalVisible, setTokenModalVisible] = useState(false);

  useEffect(() => {
    loadTokens();
  }, []);

  const loadTokens = async () => {
    setLoading(true);
    try {
      const response = await api.auth.listAPITokens();
      setTokens(response.data.tokens);
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('apiTokens.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (values: any) => {
    try {
      const response = await api.auth.createAPIToken({
        name: values.name,
        permissions: values.permissions || [],
        expires_days: values.expires_days,
      });
      setNewToken(response.data.token);
      setTokenModalVisible(true);
      form.resetFields();
      setModalVisible(false);
      loadTokens();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('apiTokens.createFailed'));
    }
  };

  const handleDelete = async (tokenId: string) => {
    try {
      await api.auth.deleteAPIToken(tokenId);
      message.success(t('apiTokens.deleteSuccess'));
      loadTokens();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('apiTokens.deleteFailed'));
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    message.success(t('apiTokens.copiedToClipboard'));
  };

  const columns = [
    {
      title: t('common.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('apiTokens.permissions'),
      dataIndex: 'permissions',
      key: 'permissions',
      render: (permissions: Array<{ resource: string; action: string; scope: string }>) => (
        <Space wrap>
          {permissions.length > 0 ? (
            permissions.map((p, idx) => (
              <Tag key={idx} color="blue">
                {p.resource}:{p.action}:{p.scope}
              </Tag>
            ))
          ) : (
            <Tag color="default">{t('apiTokens.unlimited')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('apiTokens.expiresAt'),
      dataIndex: 'expires_at',
      key: 'expires_at',
      render: (text: string) => (text ? new Date(text).toLocaleString() : t('apiTokens.neverExpires')),
    },
    {
      title: t('apiTokens.lastUsed'),
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      render: (text: string) => (text ? new Date(text).toLocaleString() : t('apiTokens.neverUsed')),
    },
    {
      title: t('common.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>{isActive ? t('apiTokens.active') : t('apiTokens.deleted')}</Tag>
      ),
    },
    {
      title: t('common.createdAt'),
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: t('common.actions'),
      key: 'action',
      render: (_: any, record: APIToken) => (
        <Space>
          <Popconfirm
            title={t('apiTokens.confirmDelete')}
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              {t('common.delete')}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={t('apiTokens.title')}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalVisible(true)}
        >
          {t('apiTokens.create')}
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={tokens}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
      <Modal
        title={t('apiTokens.create')}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
      >
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item
            name="name"
            label={t('apiTokens.tokenName')}
            rules={[{ required: true, message: t('apiTokens.pleaseInputTokenName') }]}
          >
            <Input placeholder={t('apiTokens.tokenName')} />
          </Form.Item>
          <Form.Item name="expires_days" label={t('apiTokens.expiresDays')}>
            <InputNumber
              min={1}
              placeholder={t('apiTokens.expiresDaysPlaceholder')}
              style={{ width: '100%' }}
            />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              {t('common.create')}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title={t('apiTokens.createSuccess')}
        open={tokenModalVisible}
        onCancel={() => {
          setTokenModalVisible(false);
          setNewToken(null);
        }}
        footer={[
          <Button
            key="copy"
            icon={<CopyOutlined />}
            onClick={() => newToken && copyToClipboard(newToken)}
          >
            {t('apiTokens.copyToken')}
          </Button>,
          <Button key="close" onClick={() => {
            setTokenModalVisible(false);
            setNewToken(null);
          }}>
            {t('common.close')}
          </Button>,
        ]}
      >
        <div style={{ marginBottom: 16 }}>
          <p>{t('apiTokens.keepTokenSafe')}</p>
          <Input.TextArea
            value={newToken || ''}
            readOnly
            rows={4}
            style={{ fontFamily: 'monospace' }}
          />
        </div>
      </Modal>
    </Card>
  );
};

export default APITokenManagement;


