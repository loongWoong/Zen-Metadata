/**
 * API管理页面
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  message,
  Space,
  Tag,
  Row,
  Col,
  Switch,
} from 'antd';
import { EditOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const { Option } = Select;
const { TextArea } = Input;

interface APIRoute {
  id: string;
  path: string;
  method: string;
  summary?: string;
  description?: string;
  required_roles: string[];
  required_permissions: Array<{ resource: string; action: string; scope: string }>;
  is_public: boolean;
}

const APIManagement: React.FC = () => {
  const { t } = useTranslation();
  const [routes, setRoutes] = useState<APIRoute[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRoute, setEditingRoute] = useState<APIRoute | null>(null);
  const [form] = Form.useForm();
  const [statistics, setStatistics] = useState<any>(null);
  const [roles, setRoles] = useState<Array<{ name: string; description?: string }>>([]);

  useEffect(() => {
    loadRoutes();
    loadStatistics();
    loadRoles();
  }, []);

  const loadRoutes = async () => {
    setLoading(true);
    try {
      const response = await api.apiManagement.listRoutes();
      setRoutes(response.data.routes);
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('api.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const loadStatistics = async () => {
    try {
      const response = await api.apiManagement.getStatistics();
      setStatistics(response.data);
    } catch (error: any) {
      console.error('加载统计信息失败:', error);
    }
  };

  const loadRoles = async () => {
    try {
      const response = await api.auth.listRoles();
      setRoles(response.data.roles);
    } catch (error) {
      console.error('加载角色列表失败:', error);
    }
  };

  const handleEdit = (route: APIRoute) => {
    setEditingRoute(route);
    form.setFieldsValue({
      summary: route.summary,
      description: route.description,
      required_roles: route.required_roles,
      is_public: route.is_public,
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values: any) => {
    if (!editingRoute) return;
    
    try {
      await api.apiManagement.updateRoute(editingRoute.id, {
        summary: values.summary,
        description: values.description,
        required_roles: values.required_roles || [],
        is_public: values.is_public,
      });
      message.success(t('api.updateSuccess'));
      form.resetFields();
      setModalVisible(false);
      loadRoutes();
      loadStatistics();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('api.operationFailed'));
    }
  };

  const getMethodColor = (method: string) => {
    const colors: Record<string, string> = {
      GET: 'blue',
      POST: 'green',
      PUT: 'orange',
      DELETE: 'red',
      PATCH: 'purple',
    };
    return colors[method] || 'default';
  };

  const columns = [
    {
      title: t('api.method'),
      dataIndex: 'method',
      key: 'method',
      width: 100,
      render: (method: string) => (
        <Tag color={getMethodColor(method)}>{method}</Tag>
      ),
    },
    {
      title: t('api.path'),
      dataIndex: 'path',
      key: 'path',
    },
    {
      title: t('api.summary'),
      dataIndex: 'summary',
      key: 'summary',
    },
    {
      title: t('api.requiredRoles'),
      dataIndex: 'required_roles',
      key: 'required_roles',
      render: (roles: string[]) => (
        <Space wrap>
          {roles.length > 0 ? (
            roles.map((r) => (
              <Tag key={r} color="blue">
                {r}
              </Tag>
            ))
          ) : (
            <Tag color="default">{t('common.none')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('api.public'),
      dataIndex: 'is_public',
      key: 'is_public',
      width: 80,
      render: (isPublic: boolean) => (
        <Tag color={isPublic ? 'green' : 'red'}>{isPublic ? t('common.yes') : t('common.no')}</Tag>
      ),
    },
    {
      title: t('common.actions'),
      key: 'action',
      width: 100,
      render: (_: any, record: APIRoute) => (
        <Button
          type="link"
          icon={<EditOutlined />}
          onClick={() => handleEdit(record)}
        >
          {t('common.edit')}
        </Button>
      ),
    },
  ];

  return (
    <div>
      {statistics && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('api.totalRoutes')}</span>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{statistics.total_routes}</span>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('api.publicRoutes')}</span>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{statistics.public_routes}</span>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('api.protectedRoutes')}</span>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{statistics.protected_routes}</span>
              </div>
            </Card>
          </Col>
          <Col span={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('api.httpMethods')}</span>
                <span style={{ fontSize: 20, fontWeight: 600 }}>
                  {Object.keys(statistics.methods).length} {t('api.types')}
                </span>
              </div>
            </Card>
          </Col>
        </Row>
      )}
      <Card title={t('api.title')}>
        <Table
          columns={columns}
          dataSource={routes}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 50 }}
        />
        <Modal
          title={t('api.editRoute')}
          open={modalVisible}
          onCancel={() => {
            setModalVisible(false);
            form.resetFields();
          }}
          footer={null}
          width={600}
        >
          {editingRoute && (
            <div style={{ marginBottom: 16 }}>
              <Space>
                <Tag color={getMethodColor(editingRoute.method)}>{editingRoute.method}</Tag>
                <span>{editingRoute.path}</span>
              </Space>
            </div>
          )}
          <Form form={form} onFinish={handleSubmit} layout="vertical">
            <Form.Item name="summary" label={t('api.summary')}>
              <Input placeholder={t('api.summaryPlaceholder')} />
            </Form.Item>
            <Form.Item name="description" label={t('common.description')}>
              <TextArea rows={3} placeholder={t('api.descriptionPlaceholder')} />
            </Form.Item>
            <Form.Item name="required_roles" label={t('api.requiredRoles')}>
              <Select mode="multiple" placeholder={t('api.selectRequiredRoles')}>
                {roles.map((r) => (
                  <Option key={r.name} value={r.name}>
                    {r.name} - {r.description}
                  </Option>
                ))}
              </Select>
            </Form.Item>
            <Form.Item name="is_public" label={t('api.publicAccess')} valuePropName="checked">
              <Switch checkedChildren={t('common.yes')} unCheckedChildren={t('common.no')} />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" block>
                {t('common.update')}
              </Button>
            </Form.Item>
          </Form>
        </Modal>
      </Card>
    </div>
  );
};

export default APIManagement;

