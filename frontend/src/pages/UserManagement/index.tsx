/**
 * 用户管理页面
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
  Switch,
  message,
  Space,
  Tag,
  Popconfirm,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const { Option } = Select;

interface User {
  id: string;
  username: string;
  email?: string;
  roles: string[];
  is_active: boolean;
  created_at: string;
}

const UserManagement: React.FC = () => {
  const { t } = useTranslation();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [roles, setRoles] = useState<Array<{ name: string; description?: string }>>([]);
  const [editingUser, setEditingUser] = useState<User | null>(null);

  useEffect(() => {
    loadUsers();
    loadRoles();
  }, []);

  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await api.auth.listUsers();
      setUsers(response.data.users);
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('users.loadFailed'));
    } finally {
      setLoading(false);
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

  const handleCreateUser = async (values: {
    username: string;
    email?: string;
    password?: string;
    roles?: string[];
    is_active?: boolean;
  }) => {
    try {
      await api.auth.createUser(values);
      message.success(t('users.createSuccess'));
      form.resetFields();
      setModalVisible(false);
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('users.createFailed'));
    }
  };

  const handleEdit = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue({
      username: user.username,
      email: user.email,
      roles: user.roles,
      is_active: user.is_active,
    });
    setModalVisible(true);
  };

  const handleUpdate = async (values: any) => {
    if (!editingUser) return;
    
    try {
      await api.auth.updateUser(editingUser.id, {
        username: values.username,
        email: values.email,
        password: values.password,
        roles: values.roles,
        is_active: values.is_active,
      });
      message.success(t('users.updateSuccess'));
      form.resetFields();
      setModalVisible(false);
      setEditingUser(null);
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('users.updateFailed'));
    }
  };

  const handleDelete = async (userId: string) => {
    try {
      await api.auth.deleteUser(userId);
      message.success(t('users.disableSuccess'));
      loadUsers();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('users.operationFailed'));
    }
  };

  const columns = [
    {
      title: t('users.username'),
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: t('users.email'),
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: t('users.roles'),
      dataIndex: 'roles',
      key: 'roles',
      render: (roles: string[]) => (
        <Space>
          {roles.map((role) => (
            <Tag key={role} color="blue">
              {role}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('common.status'),
      dataIndex: 'is_active',
      key: 'is_active',
      render: (isActive: boolean) => (
        <Tag color={isActive ? 'green' : 'red'}>
          {isActive ? t('users.active') : t('users.inactive')}
        </Tag>
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
      render: (_: any, record: User) => (
        <Space>
          <Button
            type="link"
            onClick={() => handleEdit(record)}
          >
            {t('common.edit')}
          </Button>
          <Popconfirm
            title={t('users.confirmDisable')}
            onConfirm={() => handleDelete(record.id)}
          >
            <Button type="link" danger>
              {t('users.disable')}
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={t('users.title')}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalVisible(true)}
        >
          {t('users.create')}
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={users}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
      <Modal
        title={editingUser ? t('users.edit') : t('users.create')}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setEditingUser(null);
        }}
        footer={null}
      >
        <Form form={form} onFinish={editingUser ? handleUpdate : handleCreateUser} layout="vertical">
          {!editingUser && (
            <Form.Item
              name="username"
              rules={[{ required: true, message: t('users.pleaseInputUsername') }]}
            >
              <Input placeholder={t('users.username')} />
            </Form.Item>
          )}
          {editingUser && (
            <Form.Item
              name="username"
              label={t('users.username')}
              rules={[{ required: true, message: t('users.pleaseInputUsername') }]}
            >
              <Input placeholder={t('users.username')} />
            </Form.Item>
          )}
          <Form.Item name="email" rules={[{ type: 'email', message: t('users.pleaseInputValidEmail') }]}>
            <Input placeholder={t('users.emailOptional')} />
          </Form.Item>
          {editingUser && (
            <Form.Item name="password" label={t('users.newPassword')}>
              <Input.Password placeholder={t('users.newPassword')} />
            </Form.Item>
          )}
          {!editingUser && (
            <Form.Item name="password">
              <Input.Password placeholder={t('users.passwordOptional')} />
            </Form.Item>
          )}
          <Form.Item name="roles">
            <Select mode="multiple" placeholder={t('users.selectRoles')}>
              {roles.map((role) => (
                <Option key={role.name} value={role.name}>
                  {role.name} - {role.description}
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="is_active" valuePropName="checked" initialValue={true}>
            <Switch checkedChildren={t('users.active')} unCheckedChildren={t('users.inactive')} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              {editingUser ? t('common.update') : t('common.create')}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default UserManagement;


