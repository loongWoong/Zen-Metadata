/**
 * 角色管理页面
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
  Popconfirm,
  Checkbox,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const { Option } = Select;
const { TextArea } = Input;

interface Permission {
  resource: string;
  action: string;
  scope: string;
}

interface Role {
  name: string;
  description?: string;
  permissions: Permission[];
}

const RESOURCES = ['entity', 'relationship', 'collector', 'job', 'version', 'user', 'role', 'menu', 'api', '*'];
const ACTIONS = ['read', 'write', 'delete', 'execute', 'approve', '*'];
const SCOPES = ['all', 'team', 'own'];

const RoleManagement: React.FC = () => {
  const { t } = useTranslation();
  const [roles, setRoles] = useState<Role[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | null>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadRoles();
  }, []);

  const loadRoles = async () => {
    setLoading(true);
    try {
      const response = await api.auth.listRoles();
      setRoles(response.data.roles);
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('roles.loadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingRole(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (role: Role) => {
    setEditingRole(role);
    form.setFieldsValue({
      name: role.name,
      description: role.description,
      permissions: role.permissions,
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingRole) {
        await api.auth.updateRole(editingRole.name, {
          description: values.description,
          permissions: values.permissions || [],
        });
        message.success(t('roles.updateSuccess'));
      } else {
        await api.auth.createRole({
          name: values.name,
          description: values.description,
          permissions: values.permissions || [],
        });
        message.success(t('roles.createSuccess'));
      }
      form.resetFields();
      setModalVisible(false);
      loadRoles();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('roles.operationFailed'));
    }
  };

  const handleDelete = async (roleName: string) => {
    try {
      await api.auth.deleteRole(roleName);
      message.success(t('roles.deleteSuccess'));
      loadRoles();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('roles.deleteFailed'));
    }
  };

  const columns = [
    {
      title: t('roles.roleName'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('common.description'),
      dataIndex: 'description',
      key: 'description',
    },
    {
      title: t('roles.permissions'),
      dataIndex: 'permissions',
      key: 'permissions',
      render: (permissions: Permission[]) => (
        <Space wrap>
          {permissions.map((p, idx) => (
            <Tag key={idx} color="blue">
              {p.resource}:{p.action}:{p.scope}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: t('common.actions'),
      key: 'action',
      render: (_: any, record: Role) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            {t('common.edit')}
          </Button>
          {record.name !== 'admin' && (
            <Popconfirm
              title={t('roles.confirmDelete')}
              onConfirm={() => handleDelete(record.name)}
            >
              <Button type="link" danger icon={<DeleteOutlined />}>
                {t('common.delete')}
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={t('roles.title')}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
        >
          {t('roles.create')}
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={roles}
        rowKey="name"
        loading={loading}
        pagination={{ pageSize: 20 }}
      />
      <Modal
        title={editingRole ? t('roles.edit') : t('roles.create')}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={800}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          {!editingRole && (
            <Form.Item
              name="name"
              label={t('roles.roleName')}
              rules={[{ required: true, message: t('roles.pleaseInputRoleName') }]}
            >
              <Input placeholder={t('roles.roleName')} />
            </Form.Item>
          )}
          <Form.Item name="description" label={t('common.description')}>
            <TextArea rows={3} placeholder={t('roles.roleDescription')} />
          </Form.Item>
          <Form.Item name="permissions" label={t('roles.permissions')}>
            <Form.List name="permissions">
              {(fields, { add, remove }) => (
                <>
                  {fields.map(({ key, name, ...restField }) => (
                    <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                      <Form.Item
                        {...restField}
                        name={[name, 'resource']}
                        rules={[{ required: true, message: t('roles.pleaseSelectResource') }]}
                      >
                        <Select placeholder={t('roles.resource')} style={{ width: 150 }}>
                          {RESOURCES.map((r) => (
                            <Option key={r} value={r}>
                              {r}
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'action']}
                        rules={[{ required: true, message: t('roles.pleaseSelectAction') }]}
                      >
                        <Select placeholder={t('roles.action')} style={{ width: 150 }}>
                          {ACTIONS.map((a) => (
                            <Option key={a} value={a}>
                              {a}
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'scope']}
                        rules={[{ required: true, message: t('roles.pleaseSelectScope') }]}
                      >
                        <Select placeholder={t('roles.scope')} style={{ width: 120 }}>
                          {SCOPES.map((s) => (
                            <Option key={s} value={s}>
                              {s}
                            </Option>
                          ))}
                        </Select>
                      </Form.Item>
                      <Button type="link" danger onClick={() => remove(name)}>
                        {t('common.delete')}
                      </Button>
                    </Space>
                  ))}
                  <Form.Item>
                    <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                      {t('roles.addPermission')}
                    </Button>
                  </Form.Item>
                </>
              )}
            </Form.List>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              {editingRole ? t('common.update') : t('common.create')}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default RoleManagement;


