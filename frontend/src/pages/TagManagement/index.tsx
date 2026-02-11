import { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  Space,
  Tag,
  Popconfirm,
  message,
  Card,
  Row,
  Col,
  ColorPicker,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const { Option } = Select;
const { TextArea } = Input;

export default function TagManagement() {
  const { t } = useTranslation();
  const [tags, setTags] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingTag, setEditingTag] = useState<any>(null);
  const [form] = Form.useForm();

  useEffect(() => {
    loadTags();
    loadCategories();
  }, []);

  const loadTags = async () => {
    setLoading(true);
    try {
      const response = await api.governance.listTags();
      setTags(response.data.tags);
    } catch (error: any) {
      message.error(t('tags.loadFailed') + ': ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const loadCategories = async () => {
    try {
      const response = await api.governance.getCategories();
      setCategories(response.data.categories);
    } catch (error: any) {
      console.error('加载分类失败:', error);
    }
  };

  const handleCreate = () => {
    setEditingTag(null);
    form.resetFields();
    form.setFieldsValue({ color: '#808080' });
    setModalVisible(true);
  };

  const handleEdit = (tag: any) => {
    setEditingTag(tag);
    form.setFieldsValue({
      name: tag.name,
      category: tag.category,
      description: tag.description,
      color: tag.color,
    });
    setModalVisible(true);
  };

  const handleDelete = async (tagId: string) => {
    try {
      await api.governance.deleteTag(tagId);
      message.success(t('tags.deleteSuccess'));
      loadTags();
    } catch (error: any) {
      message.error(t('tags.deleteFailed') + ': ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      // 处理颜色值：ColorPicker返回的是对象，需要转换为字符串
      if (values.color && typeof values.color !== 'string') {
        values.color = values.color.toHexString();
      }
      if (editingTag) {
        await api.governance.updateTag(editingTag.id, values);
        message.success(t('tags.updateSuccess'));
      } else {
        await api.governance.createTag(values);
        message.success(t('tags.createSuccess'));
      }
      setModalVisible(false);
      loadTags();
    } catch (error: any) {
      message.error(t('tags.operationFailed') + ': ' + (error.response?.data?.detail || error.message));
    }
  };

  const columns = [
    {
      title: t('common.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('tags.category'),
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => <Tag>{category}</Tag>,
    },
    {
      title: t('tags.color'),
      dataIndex: 'color',
      key: 'color',
      render: (color: string) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div
            style={{
              width: 20,
              height: 20,
              backgroundColor: color,
              border: '1px solid #d9d9d9',
              borderRadius: 4,
            }}
          />
          <span>{color}</span>
        </div>
      ),
    },
    {
      title: t('common.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('common.version'),
      dataIndex: 'version',
      key: 'version',
      width: 80,
    },
    {
      title: t('common.actions'),
      key: 'action',
      width: 150,
      render: (_: any, record: any) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            {t('common.edit')}
          </Button>
          <Popconfirm
            title={t('tags.confirmDelete')}
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
    <div>
      <Card
        title={t('tags.title')}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            {t('tags.create')}
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={tags}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={editingTag ? t('tags.edit') : t('tags.create')}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('tags.name')}
            rules={[{ required: true, message: t('tags.pleaseInputName') }]}
          >
            <Input placeholder={t('tags.pleaseInputName')} />
          </Form.Item>

          <Form.Item
            name="category"
            label={t('tags.category')}
            rules={[{ required: true, message: t('tags.pleaseSelectCategory') }]}
          >
            <Select placeholder={t('tags.pleaseSelectCategory')}>
              {categories.map((cat) => (
                <Option key={cat.value} value={cat.value}>
                  {cat.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="color" label={t('tags.color')} initialValue="#808080">
            <ColorPicker showText />
          </Form.Item>

          <Form.Item name="description" label={t('common.description')}>
            <TextArea rows={3} placeholder={t('common.pleaseInput')} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

