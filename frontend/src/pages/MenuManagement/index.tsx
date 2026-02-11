/**
 * 菜单管理页面
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
  Tree,
  Switch,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const { Option } = Select;

interface MenuItem {
  id: string;
  key: string;
  label: string;
  icon?: string;
  path?: string;
  parent_id?: string;
  order: number;
  required_roles: string[];
  required_permissions: Array<{ resource: string; action: string; scope: string }>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  children?: MenuItem[];
}

const MenuManagement: React.FC = () => {
  const { t } = useTranslation();
  const [menus, setMenus] = useState<MenuItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingMenu, setEditingMenu] = useState<MenuItem | null>(null);
  const [form] = Form.useForm();
  const [roles, setRoles] = useState<Array<{ name: string; description?: string }>>([]);

  useEffect(() => {
    loadMenus();
    loadRoles();
  }, []);

  const loadMenus = async () => {
    setLoading(true);
    try {
      const response = await api.menu.listAllItems();
      setMenus(response.data.menus);
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('menus.loadFailed'));
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

  const handleCreate = () => {
    setEditingMenu(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (menu: MenuItem) => {
    setEditingMenu(menu);
    form.setFieldsValue({
      key: menu.key,
      label: menu.label,
      icon: menu.icon,
      path: menu.path,
      parent_id: menu.parent_id,
      order: menu.order,
      required_roles: menu.required_roles,
      is_active: menu.is_active,
    });
    setModalVisible(true);
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingMenu) {
        await api.menu.updateItem(editingMenu.id, {
          label: values.label,
          icon: values.icon,
          path: values.path,
          parent_id: values.parent_id,
          order: values.order,
          required_roles: values.required_roles || [],
          is_active: values.is_active,
        });
        message.success(t('menus.updateSuccess'));
      } else {
        await api.menu.createItem({
          key: values.key,
          label: values.label,
          icon: values.icon,
          path: values.path,
          parent_id: values.parent_id,
          order: values.order || 0,
          required_roles: values.required_roles || [],
        });
        message.success(t('menus.createSuccess'));
      }
      form.resetFields();
      setModalVisible(false);
      loadMenus();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('menus.operationFailed'));
    }
  };

  const handleDelete = async (menuId: string) => {
    try {
      await api.menu.deleteItem(menuId);
      message.success(t('menus.deleteSuccess'));
      loadMenus();
    } catch (error: any) {
      message.error(error.response?.data?.detail || t('menus.deleteFailed'));
    }
  };

  const flattenMenus = (menus: MenuItem[]): MenuItem[] => {
    const result: MenuItem[] = [];
    const traverse = (items: MenuItem[]) => {
      items.forEach((item) => {
        result.push(item);
        if (item.children) {
          traverse(item.children);
        }
      });
    };
    traverse(menus);
    return result;
  };

  const flatMenus = flattenMenus(menus);

  const columns = [
    {
      title: t('menus.key'),
      dataIndex: 'key',
      key: 'key',
    },
    {
      title: t('menus.label'),
      dataIndex: 'label',
      key: 'label',
    },
    {
      title: t('menus.icon'),
      dataIndex: 'icon',
      key: 'icon',
    },
    {
      title: t('menus.path'),
      dataIndex: 'path',
      key: 'path',
    },
    {
      title: t('menus.order'),
      dataIndex: 'order',
      key: 'order',
    },
    {
      title: t('menus.requiredRoles'),
      dataIndex: 'required_roles',
      key: 'required_roles',
      render: (roles: string[]) => (
        <Space wrap>
          {roles.map((r) => (
            <Tag key={r} color="blue">
              {r}
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
        <Tag color={isActive ? 'green' : 'red'}>{isActive ? t('menus.enabled') : t('menus.disabled')}</Tag>
      ),
    },
    {
      title: t('common.actions'),
      key: 'action',
      render: (_: any, record: MenuItem) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            {t('common.edit')}
          </Button>
          <Popconfirm
            title={t('menus.confirmDelete')}
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
      title={t('menus.title')}
      extra={
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
        >
          {t('menus.create')}
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={flatMenus}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
        expandable={{
          defaultExpandAllRows: true,
        }}
      />
      <Modal
        title={editingMenu ? t('menus.edit') : t('menus.create')}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form form={form} onFinish={handleSubmit} layout="vertical">
          {!editingMenu && (
            <Form.Item
              name="key"
              label={t('menus.key')}
              rules={[{ required: true, message: t('menus.pleaseInputKey') }]}
            >
              <Input placeholder={t('menus.keyPlaceholder')} />
            </Form.Item>
          )}
          <Form.Item
            name="label"
            label={t('menus.label')}
            rules={[{ required: true, message: t('menus.pleaseInputLabel') }]}
          >
            <Input placeholder={t('menus.labelPlaceholder')} />
          </Form.Item>
          <Form.Item name="icon" label={t('menus.icon')}>
            <Input placeholder={t('menus.iconPlaceholder')} />
          </Form.Item>
          <Form.Item name="path" label={t('menus.path')}>
            <Input placeholder={t('menus.pathPlaceholder')} />
          </Form.Item>
          <Form.Item name="parent_id" label={t('menus.parentId')}>
            <Select placeholder={t('menus.selectParentMenu')} allowClear>
              {flatMenus.map((m) => (
                <Option key={m.id} value={m.id}>
                  {m.label} ({m.key})
                </Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item name="order" label={t('menus.order')}>
            <Input type="number" placeholder={t('menus.orderPlaceholder')} />
          </Form.Item>
          <Form.Item name="required_roles" label={t('menus.requiredRoles')}>
            <Select mode="multiple" placeholder={t('menus.selectRequiredRoles')}>
              {roles.map((r) => (
                <Option key={r.name} value={r.name}>
                  {r.name} - {r.description}
                </Option>
              ))}
            </Select>
          </Form.Item>
          {editingMenu && (
            <Form.Item name="is_active" label={t('common.status')} valuePropName="checked">
              <Switch checkedChildren={t('menus.enabled')} unCheckedChildren={t('menus.disabled')} />
            </Form.Item>
          )}
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              {editingMenu ? t('common.update') : t('common.create')}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
};

export default MenuManagement;


