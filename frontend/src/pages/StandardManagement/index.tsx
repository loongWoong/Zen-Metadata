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
  Switch,
  Tabs,
  InputNumber,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CheckCircleOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';

const { Option } = Select;
const { TextArea } = Input;
const { TabPane } = Tabs;

export default function StandardManagement() {
  const { t } = useTranslation();
  const [standards, setStandards] = useState<any[]>([]);
  const [standardTypes, setStandardTypes] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingStandard, setEditingStandard] = useState<any>(null);
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState<string>('all');

  useEffect(() => {
    loadStandards();
    loadStandardTypes();
  }, []);

  const loadStandards = async (type?: string) => {
    setLoading(true);
    try {
      const response = await api.governance.listStandards(type ? { type } : {});
      setStandards(response.data.standards);
    } catch (error: any) {
      message.error(t('standards.loadFailed') + ': ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const loadStandardTypes = async () => {
    try {
      const response = await api.governance.getStandardTypes();
      setStandardTypes(response.data.types);
    } catch (error: any) {
      console.error('加载标准类型失败:', error);
    }
  };

  const handleCreate = () => {
    setEditingStandard(null);
    form.resetFields();
    form.setFieldsValue({ enabled: true, type: 'naming' });
    setModalVisible(true);
  };

  const handleEdit = (standard: any) => {
    setEditingStandard(standard);
    form.setFieldsValue({
      name: standard.name,
      type: standard.type,
      entity_type: standard.entity_type,
      description: standard.description,
      enabled: standard.enabled,
      rule: standard.rule,
    });
    setModalVisible(true);
  };

  const handleDelete = async (standardId: string) => {
    try {
      await api.governance.deleteStandard(standardId);
      message.success(t('standards.deleteSuccess'));
      loadStandards();
    } catch (error: any) {
      message.error(t('standards.deleteFailed') + ': ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingStandard) {
        await api.governance.updateStandard(editingStandard.id, values);
        message.success(t('standards.updateSuccess'));
      } else {
        await api.governance.createStandard(values);
        message.success(t('standards.createSuccess'));
      }
      setModalVisible(false);
      loadStandards();
    } catch (error: any) {
      message.error(t('standards.operationFailed') + ': ' + (error.response?.data?.detail || error.message));
    }
  };

  const renderRuleForm = () => {
    const type = form.getFieldValue('type');
    
    if (type === 'naming') {
      return (
        <>
          <Form.Item
            name={['rule', 'pattern']}
            label={t('standards.namingPattern')}
            rules={[{ required: true, message: t('standards.pleaseInputNamingPattern') }]}
          >
            <Input placeholder={t('standards.namingPatternPlaceholder')} />
          </Form.Item>
          <Form.Item name={['rule', 'severity']} label={t('standards.severity')} initialValue="medium">
            <Select>
              <Option value="low">{t('standards.low')}</Option>
              <Option value="medium">{t('standards.medium')}</Option>
              <Option value="high">{t('standards.high')}</Option>
            </Select>
          </Form.Item>
          <Form.Item name={['rule', 'suggestion']} label={t('standards.fixSuggestion')}>
            <TextArea rows={2} placeholder={t('standards.pleaseInputFixSuggestion')} />
          </Form.Item>
        </>
      );
    } else if (type === 'format') {
      return (
        <>
          <Form.Item
            name={['rule', 'field']}
            label={t('standards.fieldName')}
            rules={[{ required: true, message: t('standards.pleaseInputFieldName') }]}
          >
            <Input placeholder={t('standards.fieldNamePlaceholder')} />
          </Form.Item>
          <Form.Item
            name={['rule', 'format']}
            label={t('standards.formatRequirement')}
            rules={[{ required: true, message: t('standards.pleaseInputFormatRequirement') }]}
          >
            <Input placeholder={t('standards.formatRequirementPlaceholder')} />
          </Form.Item>
        </>
      );
    } else if (type === 'quality') {
      return (
        <>
          <Form.Item name={['rule', 'min_completeness']} label={t('standards.minCompleteness')}>
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name={['rule', 'min_accuracy']} label={t('standards.minAccuracy')}>
            <InputNumber min={0} max={100} style={{ width: '100%' }} />
          </Form.Item>
        </>
      );
    } else if (type === 'relationship') {
      return (
        <>
          <Form.Item
            name={['rule', 'allowed_types']}
            label={t('standards.allowedRelationshipTypes')}
            rules={[{ required: true, message: t('standards.pleaseInputAllowedRelationshipTypes') }]}
          >
            <Select mode="tags" placeholder={t('standards.allowedRelationshipTypesPlaceholder')} />
          </Form.Item>
        </>
      );
    }
    
    return (
      <Form.Item name={['rule', 'config']} label={t('standards.ruleConfig')}>
        <TextArea rows={4} placeholder={t('standards.ruleConfigPlaceholder')} />
      </Form.Item>
    );
  };

  const columns = [
    {
      title: t('common.name'),
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: t('common.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: t('standards.applicableEntityType'),
      dataIndex: 'entity_type',
      key: 'entity_type',
      render: (type: string) => type || t('common.all'),
    },
    {
      title: t('common.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'green' : 'red'}>
          {enabled ? t('standards.enabled') : t('standards.disabled')}
        </Tag>
      ),
    },
    {
      title: t('common.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
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
            title={t('standards.confirmDelete')}
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

  const filteredStandards = activeTab === 'all' 
    ? standards 
    : standards.filter(s => s.type === activeTab);

  return (
    <div>
      <Card
        title={t('standards.title')}
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            {t('standards.create')}
          </Button>
        }
      >
        <Tabs activeKey={activeTab} onChange={(key) => {
          setActiveTab(key);
          if (key !== 'all') {
            loadStandards(key);
          } else {
            loadStandards();
          }
        }}>
          <TabPane tab={t('common.all')} key="all" />
          {standardTypes.map((type) => (
            <TabPane tab={type.label} key={type.value} />
          ))}
        </Tabs>

        <Table
          columns={columns}
          dataSource={filteredStandards}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
        />
      </Card>

      <Modal
        title={editingStandard ? t('standards.edit') : t('standards.create')}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label={t('standards.standardName')}
            rules={[{ required: true, message: t('standards.pleaseInputStandardName') }]}
          >
            <Input placeholder={t('standards.pleaseInputStandardName')} />
          </Form.Item>

          <Form.Item
            name="type"
            label={t('standards.standardType')}
            rules={[{ required: true, message: t('standards.pleaseSelectStandardType') }]}
          >
            <Select placeholder={t('standards.pleaseSelectStandardType')}>
              {standardTypes.map((type) => (
                <Option key={type.value} value={type.value}>
                  {type.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item name="entity_type" label={t('standards.applicableEntityType')}>
            <Input placeholder={t('standards.applicableEntityTypePlaceholder')} />
          </Form.Item>

          <Form.Item name="description" label={t('common.description')}>
            <TextArea rows={2} placeholder={t('common.pleaseInput')} />
          </Form.Item>

          <Form.Item name="enabled" label={t('standards.enabled')} valuePropName="checked">
            <Switch />
          </Form.Item>

          {renderRuleForm()}
        </Form>
      </Modal>
    </div>
  );
}


