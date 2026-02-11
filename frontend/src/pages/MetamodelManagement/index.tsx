import { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Table,
  Button,
  Space,
  Tag,
  Modal,
  Form,
  Input,
  Select,
  Upload,
  message,
  Tabs,
  Descriptions,
  Badge,
  Alert,
  Collapse,
  Empty,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  ReloadOutlined,
  UploadOutlined,
  CodeOutlined,
  DatabaseOutlined,
  LinkOutlined,
  FolderOutlined,
} from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import type { OnMount } from '@monaco-editor/react';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import type { ColumnsType } from 'antd/es/table';
import type { UploadFile } from 'antd/es/upload/interface';

const { TabPane } = Tabs;
const { TextArea } = Input;

interface EntityModel {
  type: string;
  version: string;
  label: string;
  description?: string;
  properties: Record<string, any>;
  relationships: Array<any>;
  collector?: any;
  quality_rules?: any;
  enabled: boolean;
}

interface RelationshipModel {
  type: string;
  version: string;
  label: string;
  source_types: string[];
  target_types: string[];
  enabled: boolean;
}

interface PackageInfo {
  name: string;
  path: string;
  entity_models: string[];
  relationship_models: string[];
  metadata?: any;
  collector_type?: string;
  deployed_at?: string;
}

export default function MetamodelManagement() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [entityModels, setEntityModels] = useState<EntityModel[]>([]);
  const [relationshipModels, setRelationshipModels] = useState<RelationshipModel[]>([]);
  const [registryInfo, setRegistryInfo] = useState<any>(null);
  const [packages, setPackages] = useState<PackageInfo[]>([]);
  const [packageDetails, setPackageDetails] = useState<Record<string, any>>({});
  const [expandedPackages, setExpandedPackages] = useState<string[]>([]);
  const [entityViewMode, setEntityViewMode] = useState<'table' | 'package'>('table');
  const [selectedPackageFilter, setSelectedPackageFilter] = useState<string>('all');
  const [entityModalVisible, setEntityModalVisible] = useState(false);
  const [relationshipModalVisible, setRelationshipModalVisible] = useState(false);
  const [uploadModalVisible, setUploadModalVisible] = useState(false);
  const [selectedModel, setSelectedModel] = useState<EntityModel | null>(null);
  const [form] = Form.useForm();
  const [relForm] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [collectors, setCollectors] = useState<any[]>([]);
  const [collectorModalVisible, setCollectorModalVisible] = useState(false);
  const [editingCollector, setEditingCollector] = useState<any>(null);
  const [collectorForm] = Form.useForm();
  const [pluginEditorVisible, setPluginEditorVisible] = useState(false);
  const [editingPluginCollector, setEditingPluginCollector] = useState<any>(null);
  const [pluginCode, setPluginCode] = useState<string>('');
  const [pluginCodeLoading, setPluginCodeLoading] = useState(false);

  useEffect(() => {
    loadEntityModels();
    loadRelationshipModels();
    loadRegistryInfo();
    loadPackages();
    loadCollectors();
  }, []);

  const loadEntityModels = async () => {
    try {
      setLoading(true);
      const response = await api.metamodel.listEntityModels();
      setEntityModels(response.data.models || []);
    } catch (err: any) {
      message.error(t('metamodel.loadEntityModelsFailed') + ': ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadRelationshipModels = async () => {
    try {
      const response = await api.metamodel.listRelationshipModels();
      setRelationshipModels(response.data.models || []);
    } catch (err: any) {
      message.error(t('metamodel.loadRelationshipModelsFailed') + ': ' + err.message);
    }
  };

  const loadRegistryInfo = async () => {
    try {
      const response = await api.metamodel.getRegistryInfo();
      setRegistryInfo(response.data);
    } catch (err: any) {
      // 忽略错误
    }
  };

  const loadPackages = async () => {
    try {
      const response = await api.metamodel.listPackages();
      setPackages(response.data.packages || []);
    } catch (err: any) {
      message.error(t('metamodel.loadPackagesFailed') + ': ' + err.message);
    }
  };

  const loadCollectors = async () => {
    try {
      const response = await api.metamodel.listCollectorTypes();
      setCollectors(response.data.collector_types || []);
    } catch (err: any) {
      message.error(t('metamodel.loadCollectorsFailed') + ': ' + err.message);
    }
  };

  const loadPackageDetails = async (packageName: string) => {
    if (packageDetails[packageName]) {
      return; // 已经加载过
    }
    
    try {
      const response = await api.metamodel.getPackage(packageName);
      setPackageDetails((prev) => ({
        ...prev,
        [packageName]: response.data,
      }));
    } catch (err: any) {
      message.error(t('metamodel.loadPackageDetailsFailed', { packageName }) + ': ' + err.message);
    }
  };

  // 将实体元模型按包分组
  const groupEntityModelsByPackage = () => {
    const grouped: Record<string, EntityModel[]> = {};
    const ungrouped: EntityModel[] = [];
    
    // 创建实体类型到包的映射
    const entityTypeToPackage: Record<string, string> = {};
    packages.forEach((pkg) => {
      pkg.entity_models?.forEach((entityType: string) => {
        entityTypeToPackage[entityType] = pkg.name;
      });
    });
    
    // 分组实体元模型
    entityModels.forEach((model) => {
      const packageName = entityTypeToPackage[model.type];
      if (packageName) {
        if (!grouped[packageName]) {
          grouped[packageName] = [];
        }
        grouped[packageName].push(model);
      } else {
        ungrouped.push(model);
      }
    });
    
    return { grouped, ungrouped };
  };

  // 获取过滤后的实体元模型列表
  const getFilteredEntityModels = () => {
    if (selectedPackageFilter === 'all') {
      return entityModels;
    }
    
    if (selectedPackageFilter === 'ungrouped') {
      const { ungrouped } = groupEntityModelsByPackage();
      return ungrouped;
    }
    
    const { grouped } = groupEntityModelsByPackage();
    return grouped[selectedPackageFilter] || [];
  };

  const handleCreateEntityModel = async (values: any) => {
    try {
      setLoading(true);
      await api.metamodel.createEntityModel(values);
      message.success(t('metamodel.createSuccess'));
      setEntityModalVisible(false);
      form.resetFields();
      loadEntityModels();
      loadRegistryInfo();
    } catch (err: any) {
      message.error('创建失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateRelationshipModel = async (values: any) => {
    try {
      setLoading(true);
      await api.metamodel.createRelationshipModel(values);
      message.success(t('metamodel.relationshipCreateSuccess'));
      setRelationshipModalVisible(false);
      relForm.resetFields();
      loadRelationshipModels();
      loadRegistryInfo();
    } catch (err: any) {
      message.error('创建失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEntityModel = async (type: string, version: string) => {
    Modal.confirm({
      title: t('metamodel.confirmDelete'),
      content: t('metamodel.confirmDeleteMessage', { type, version }),
      onOk: async () => {
        try {
          await api.metamodel.deleteEntityModel(type, version);
          message.success(t('metamodel.deleteSuccess'));
          loadEntityModels();
          loadRegistryInfo();
        } catch (err: any) {
          message.error(t('metamodel.deleteFailed') + ': ' + err.message);
        }
      },
    });
  };

  const handleUploadPackage = async () => {
    if (fileList.length === 0) {
      message.warning(t('metamodel.pleaseSelectFile'));
      return;
    }

    try {
      setLoading(true);
      const file = fileList[0].originFileObj;
      if (!file) {
        message.error(t('metamodel.fileInvalid'));
        return;
      }
      const response = await api.metamodel.uploadPackage(file);
      if (response.data.success) {
        message.success(t('metamodel.uploadSuccess'));
        setUploadModalVisible(false);
        setFileList([]);
        loadEntityModels();
        loadRelationshipModels();
        loadRegistryInfo();
        // 触发元模型更新事件，通知其他页面刷新
        window.dispatchEvent(new Event('metamodel-updated'));
        // 重新加载包列表
        loadPackages();
      } else {
        message.warning(t('metamodel.uploadWarning') + ': ' + response.data.errors?.join(', '));
      }
    } catch (err: any) {
      message.error(t('metamodel.uploadFailed') + ': ' + err.message);
    } finally {
      setLoading(false);
    }
  };


  const handleReloadRegistry = async () => {
    try {
      setLoading(true);
      await api.metamodel.reloadRegistry();
      message.success(t('metamodel.reloadRegistrySuccess'));
      loadEntityModels();
      loadRelationshipModels();
      loadRegistryInfo();
      loadPackages();
      loadCollectors();
      // 清空已展开的包详情缓存
      setPackageDetails({});
      setExpandedPackages([]);
      // 触发元模型更新事件，通知其他页面刷新
      window.dispatchEvent(new Event('metamodel-updated'));
    } catch (err: any) {
      message.error(t('metamodel.reloadRegistryFailed') + ': ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditCollector = (collector: any) => {
    // 获取对应的实体元模型
    const entityModel = entityModels.find(m => m.type === collector.entity_type);
    if (!entityModel) {
      message.error('找不到对应的实体元模型');
      return;
    }
    
    setEditingCollector(collector);
    collectorForm.setFieldsValue({
      collector_type: collector.collector_type,
      entity_type: collector.entity_type,
      plugin: entityModel.collector?.plugin || '',
      entry: entityModel.collector?.entry || '',
      params: JSON.stringify(entityModel.collector?.params || {}, null, 2),
    });
    setCollectorModalVisible(true);
  };

  const handleUpdateCollector = async (values: any) => {
    try {
      setLoading(true);
      // 解析params JSON
      let params = {};
      try {
        params = JSON.parse(values.params || '{}');
      } catch (e) {
        message.error(t('metamodel.paramsJsonError'));
        return;
      }

      // 获取实体元模型
      const entityModel = entityModels.find(m => m.type === values.entity_type);
      if (!entityModel) {
        message.error('找不到对应的实体元模型');
        return;
      }

      // 更新实体元模型的collector配置
      const updatedModel = {
        ...entityModel,
        collector: {
          plugin: values.plugin,
          entry: values.entry,
          params: params,
        },
      };

      // 调用API更新
      await api.metamodel.updateEntityModelCollector(values.entity_type, entityModel.version, {
        collector: updatedModel.collector,
      });

      message.success(t('metamodel.updateCollectorSuccess'));
      setCollectorModalVisible(false);
      collectorForm.resetFields();
      setEditingCollector(null);
      loadEntityModels();
      loadCollectors();
      loadRegistryInfo();
      // 触发元模型更新事件
      window.dispatchEvent(new Event('metamodel-updated'));
    } catch (err: any) {
      message.error(t('metamodel.updateCollectorFailed') + ': ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleEditPlugin = async (collector: any) => {
    try {
      setPluginCodeLoading(true);
      setEditingPluginCollector(collector);
      
      // 获取插件代码
      const response = await api.metamodel.getCollectorPluginCode(collector.collector_type);
      setPluginCode(response.data.code || '');
      setPluginEditorVisible(true);
    } catch (err: any) {
      message.error(t('metamodel.getPluginCodeFailed') + ': ' + err.message);
    } finally {
      setPluginCodeLoading(false);
    }
  };

  const handleUpdatePluginCode = async () => {
    if (!editingPluginCollector) {
      return;
    }

    try {
      setLoading(true);
      
      // 先验证代码
      const validateResponse = await api.metamodel.validatePlugin(pluginCode);
      if (!validateResponse.data.is_safe) {
        message.error(t('metamodel.pluginCodeValidationFailed') + ': ' + validateResponse.data.error);
        return;
      }

      // 更新插件代码
      await api.metamodel.updateCollectorPluginCode(
        editingPluginCollector.collector_type,
        pluginCode
      );

      message.success(t('metamodel.updatePluginCodeSuccess'));
      setPluginEditorVisible(false);
      setEditingPluginCollector(null);
      setPluginCode('');
      loadCollectors();
      loadRegistryInfo();
      // 触发元模型更新事件
      window.dispatchEvent(new Event('metamodel-updated'));
    } catch (err: any) {
      message.error(t('metamodel.updatePluginCodeFailed') + ': ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const entityColumns: ColumnsType<EntityModel> = [
    {
      title: t('common.type'),
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: t('common.version'),
      dataIndex: 'version',
      key: 'version',
    },
    {
      title: t('common.label'),
      dataIndex: 'label',
      key: 'label',
    },
    {
      title: t('common.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Badge status={enabled ? 'success' : 'default'} text={enabled ? t('common.enabled') : t('common.disabled')} />
      ),
    },
    {
      title: t('metamodel.propertiesCount'),
      key: 'properties_count',
      render: (_, record) => Object.keys(record.properties || {}).length,
    },
    {
      title: t('metamodel.relationshipsCount'),
      key: 'relationships_count',
      render: (_, record) => (record.relationships || []).length,
    },
    {
      title: t('common.actions'),
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setSelectedModel(record);
            }}
          >
            {t('metamodel.viewDetails')}
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteEntityModel(record.type, record.version)}
          >
            {t('common.delete')}
          </Button>
        </Space>
      ),
    },
  ];

  const relationshipColumns: ColumnsType<RelationshipModel> = [
    {
      title: t('common.type'),
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: t('common.version'),
      dataIndex: 'version',
      key: 'version',
    },
    {
      title: t('common.label'),
      dataIndex: 'label',
      key: 'label',
    },
    {
      title: t('metamodel.sourceTypes'),
      dataIndex: 'source_types',
      key: 'source_types',
      render: (types: string[]) => (
        <Space>
          {types.length > 0 ? (
            types.map((type) => <Tag key={type}>{type}</Tag>)
          ) : (
            <Tag color="default">{t('common.all')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('metamodel.targetTypes'),
      dataIndex: 'target_types',
      key: 'target_types',
      render: (types: string[]) => (
        <Space>
          {types.length > 0 ? (
            types.map((type) => <Tag key={type}>{type}</Tag>)
          ) : (
            <Tag color="default">{t('common.all')}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: t('common.status'),
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Badge status={enabled ? 'success' : 'default'} text={enabled ? t('common.enabled') : t('common.disabled')} />
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>{t('metamodel.title')}</h1>
        <Button icon={<ReloadOutlined />} onClick={loadEntityModels}>
          {t('common.refresh')}
        </Button>
        <Button icon={<ReloadOutlined />} onClick={handleReloadRegistry}>
          {t('metamodel.reloadRegistry')}
        </Button>
        <Button type="primary" icon={<UploadOutlined />} onClick={() => setUploadModalVisible(true)}>
          {t('metamodel.uploadPackage')}
        </Button>
      </Space>

      {registryInfo && (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} sm={12} lg={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <DatabaseOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                  <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('metamodel.entityModelCount')}</span>
                </div>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{registryInfo.entity_models?.length || 0}</span>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <LinkOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                  <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('metamodel.relationshipModelCount')}</span>
                </div>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{registryInfo.relationship_models?.length || 0}</span>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <CodeOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                  <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('metamodel.collectorCount')}</span>
                </div>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{registryInfo.collectors?.length || 0}</span>
              </div>
            </Card>
          </Col>
          <Col xs={24} sm={12} lg={6}>
            <Card bodyStyle={{ padding: '12px 16px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('metamodel.typeVersionCount')}</span>
                <span style={{ fontSize: 20, fontWeight: 600 }}>{Object.keys(registryInfo.entity_type_versions || {}).length}</span>
              </div>
            </Card>
          </Col>
        </Row>
      )}

      <Tabs defaultActiveKey="entities">
        <TabPane tab={t('metamodel.entityModels')} key="entities">
          <Card
            title={t('metamodel.entityModels')}
            extra={
              <Space>
                <Select
                  value={entityViewMode}
                  onChange={setEntityViewMode}
                  style={{ width: 120 }}
                >
                  <Select.Option value="table">{t('metamodel.tableView')}</Select.Option>
                  <Select.Option value="package">{t('metamodel.packageView')}</Select.Option>
                </Select>
                {entityViewMode === 'package' && (
                  <Select
                    value={selectedPackageFilter}
                    onChange={setSelectedPackageFilter}
                    style={{ width: 200 }}
                    placeholder={t('metamodel.selectPackage')}
                  >
                    <Select.Option value="all">{t('metamodel.allPackages')}</Select.Option>
                    <Select.Option value="ungrouped">{t('metamodel.ungrouped')}</Select.Option>
                    {packages.map((pkg) => (
                      <Select.Option key={pkg.name} value={pkg.name}>
                        {pkg.name} ({pkg.entity_models?.length || 0})
                      </Select.Option>
                    ))}
                  </Select>
                )}
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setEntityModalVisible(true)}>
                  {t('metamodel.createEntityModel')}
                </Button>
              </Space>
            }
          >
            {entityViewMode === 'table' ? (
              <Table
                columns={entityColumns}
                dataSource={getFilteredEntityModels()}
                rowKey={(record) => `${record.type}@${record.version}`}
                loading={loading}
                pagination={{ pageSize: 10 }}
              />
            ) : (
              (() => {
                // 将实体元模型按包分组
                const { grouped, ungrouped } = groupEntityModelsByPackage();
                
                // 根据筛选器决定显示哪些包
                const displayPackages = selectedPackageFilter === 'all' 
                  ? packages 
                  : selectedPackageFilter === 'ungrouped'
                  ? []
                  : packages.filter(pkg => pkg.name === selectedPackageFilter);

                return (
                  <div>
                    {selectedPackageFilter === 'ungrouped' && ungrouped.length > 0 && (
                      <Card style={{ marginBottom: 16 }}>
                        <Card.Meta
                          title={
                            <Space>
                              <Tag color="default">{t('metamodel.ungrouped')}</Tag>
                              <span>{ungrouped.length} {t('metamodel.entitiesCount')}</span>
                            </Space>
                          }
                        />
                        <Table
                          columns={entityColumns}
                          dataSource={ungrouped}
                          rowKey={(record) => `${record.type}@${record.version}`}
                          pagination={{ pageSize: 10 }}
                          size="small"
                        />
                      </Card>
                    )}

                    <Collapse
                      activeKey={expandedPackages}
                      onChange={(keys) => {
                        const keyArray = Array.isArray(keys) ? keys : [keys];
                        setExpandedPackages(keyArray as string[]);
                        keyArray.forEach((key) => {
                          if (key && !packageDetails[key]) {
                            loadPackageDetails(key);
                          }
                        });
                      }}
                    >
                      {displayPackages.map((pkg) => {
                        const models = grouped[pkg.name] || [];
                        
                        return (
                          <Collapse.Panel
                            key={pkg.name}
                            header={
                              <Space>
                                <FolderOutlined />
                                <strong>{pkg.name}</strong>
                                {pkg.collector_type && (
                                  <Tag color="blue">{t('metamodel.collectorLabel')}: {pkg.collector_type}</Tag>
                                )}
                                <Tag>{models.length} {t('metamodel.entitiesLabel')}</Tag>
                              </Space>
                            }
                          >
                            {models.length === 0 ? (
                              <Empty description={t('metamodel.noEntityModelsInPackage')} image={Empty.PRESENTED_IMAGE_SIMPLE} />
                            ) : (
                              <Table
                                columns={entityColumns}
                                dataSource={models}
                                rowKey={(record) => `${record.type}@${record.version}`}
                                pagination={{ pageSize: 10 }}
                                size="small"
                              />
                            )}
                          </Collapse.Panel>
                        );
                      })}
                    </Collapse>

                    {displayPackages.length === 0 && selectedPackageFilter !== 'ungrouped' && (
                      <Empty description={t('metamodel.noMatchingPackages')} />
                    )}
                  </div>
                );
              })()
            )}
          </Card>
        </TabPane>

        <TabPane tab={t('metamodel.relationshipModels')} key="relationships">
          <Card
            title={t('metamodel.relationshipModels')}
            extra={
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setRelationshipModalVisible(true)}>
                {t('metamodel.createRelationshipModel')}
              </Button>
            }
          >
            <Table
              columns={relationshipColumns}
              dataSource={relationshipModels}
              rowKey={(record) => `${record.type}@${record.version}`}
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>


        <TabPane tab={t('metamodel.collectors')} key="collectors">
          <Card
            title={t('metamodel.collectors')}
            extra={
              <Button icon={<ReloadOutlined />} onClick={loadCollectors}>
                {t('common.refresh')}
              </Button>
            }
          >
            <Table
              columns={[
                {
                  title: t('metamodel.collectorType'),
                  dataIndex: 'collector_type',
                  key: 'collector_type',
                },
                {
                  title: t('metamodel.entityType'),
                  dataIndex: 'entity_type',
                  key: 'entity_type',
                },
                {
                  title: t('common.label'),
                  dataIndex: 'label',
                  key: 'label',
                },
                {
                  title: t('common.version'),
                  dataIndex: 'version',
                  key: 'version',
                },
                {
                  title: t('common.status'),
                  dataIndex: 'enabled',
                  key: 'enabled',
                  render: (enabled: boolean) => (
                    <Badge status={enabled ? 'success' : 'default'} text={enabled ? t('common.enabled') : t('common.disabled')} />
                  ),
                },
                {
                  title: t('common.actions'),
                  key: 'action',
                  render: (_, record) => (
                    <Space>
                      <Button
                        size="small"
                        onClick={() => handleEditCollector(record)}
                      >
                        {t('common.edit')}
                      </Button>
                      <Button
                        size="small"
                        icon={<CodeOutlined />}
                        onClick={() => handleEditPlugin(record)}
                      >
                        {t('metamodel.pluginEdit')}
                      </Button>
                    </Space>
                  ),
                },
              ]}
              dataSource={collectors}
              rowKey="collector_type"
              loading={loading}
              pagination={{ pageSize: 10 }}
            />
          </Card>
        </TabPane>

        <TabPane tab={t('metamodel.registryInfo')} key="registry">
          {registryInfo && (
            <Row gutter={[16, 16]}>
              <Col span={24}>
                <Card title={t('metamodel.registryOverview')}>
                  <Descriptions column={2} bordered>
                    <Descriptions.Item label={t('metamodel.entityModelCount')}>
                      {registryInfo.entity_models?.length || 0}
                    </Descriptions.Item>
                    <Descriptions.Item label={t('metamodel.relationshipModelCount')}>
                      {registryInfo.relationship_models?.length || 0}
                    </Descriptions.Item>
                    <Descriptions.Item label={t('metamodel.collectorCount')}>
                      {registryInfo.collectors?.length || 0}
                    </Descriptions.Item>
                    <Descriptions.Item label={t('metamodel.typeVersionCount')}>
                      {Object.keys(registryInfo.entity_type_versions || {}).length}
                    </Descriptions.Item>
                  </Descriptions>
                </Card>
              </Col>
              <Col span={12}>
                <Card title={t('metamodel.entityTypeVersions')}>
                  {Object.entries(registryInfo.entity_type_versions || {}).map(([type, versions]: [string, any]) => (
                    <div key={type} style={{ marginBottom: 8 }}>
                      <strong>{type}:</strong>{' '}
                      {Array.isArray(versions) ? versions.join(', ') : 'N/A'}
                    </div>
                  ))}
                </Card>
              </Col>
              <Col span={12}>
                <Card title={t('metamodel.relationshipTypeVersions')}>
                  {Object.entries(registryInfo.relationship_type_versions || {}).map(
                    ([type, versions]: [string, any]) => (
                      <div key={type} style={{ marginBottom: 8 }}>
                        <strong>{type}:</strong>{' '}
                        {Array.isArray(versions) ? versions.join(', ') : 'N/A'}
                      </div>
                    )
                  )}
                </Card>
              </Col>
            </Row>
          )}
        </TabPane>
      </Tabs>

      {/* 创建实体元模型模态框 */}
      <Modal
        title={t('metamodel.createEntityModelTitle')}
        open={entityModalVisible}
        onCancel={() => {
          setEntityModalVisible(false);
          form.resetFields();
        }}
        onOk={() => form.submit()}
        confirmLoading={loading}
        width={800}
      >
        <Form form={form} onFinish={handleCreateEntityModel} layout="vertical">
          <Form.Item name="type" label={t('common.type')} rules={[{ required: true }]}>
            <Input placeholder={t('metamodel.typePlaceholder')} />
          </Form.Item>
          <Form.Item name="version" label={t('common.version')} initialValue="v1">
            <Input />
          </Form.Item>
          <Form.Item name="label" label={t('common.label')} rules={[{ required: true }]}>
            <Input placeholder={t('metamodel.labelPlaceholder')} />
          </Form.Item>
          <Form.Item name="description" label={t('common.description')}>
            <TextArea rows={3} />
          </Form.Item>
          <Alert
            message={t('metamodel.tip')}
            description={t('metamodel.tipDescription')}
            type="info"
            showIcon
            style={{ marginBottom: 16 }}
          />
        </Form>
      </Modal>

      {/* 创建关系元模型模态框 */}
      <Modal
        title={t('metamodel.createRelationshipModelTitle')}
        open={relationshipModalVisible}
        onCancel={() => {
          setRelationshipModalVisible(false);
          relForm.resetFields();
        }}
        onOk={() => relForm.submit()}
        confirmLoading={loading}
        width={600}
      >
        <Form form={relForm} onFinish={handleCreateRelationshipModel} layout="vertical">
          <Form.Item name="type" label={t('metamodel.relationshipType')} rules={[{ required: true }]}>
            <Input placeholder={t('metamodel.relationshipTypePlaceholder')} />
          </Form.Item>
          <Form.Item name="version" label={t('common.version')} initialValue="v1">
            <Input />
          </Form.Item>
          <Form.Item name="label" label={t('common.label')} rules={[{ required: true }]}>
            <Input placeholder={t('metamodel.relationshipLabelPlaceholder')} />
          </Form.Item>
          <Form.Item name="description" label={t('common.description')}>
            <TextArea rows={3} />
          </Form.Item>
          <Form.Item name="source_types" label={t('metamodel.sourceTypesEmpty')}>
            <Select mode="tags" placeholder={t('metamodel.sourceTypesPlaceholder')} />
          </Form.Item>
          <Form.Item name="target_types" label={t('metamodel.targetTypesEmpty')}>
            <Select mode="tags" placeholder={t('metamodel.targetTypesPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 上传包模态框 */}
      <Modal
        title={t('metamodel.uploadPackageTitle')}
        open={uploadModalVisible}
        onCancel={() => {
          setUploadModalVisible(false);
          setFileList([]);
        }}
        onOk={handleUploadPackage}
        confirmLoading={loading}
      >
        <Alert
          message={t('metamodel.uploadDescription')}
          description={t('metamodel.uploadDescription')}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Upload
          fileList={fileList}
          beforeUpload={() => false}
          onChange={({ fileList }) => setFileList(fileList)}
          accept=".yaml,.yml,.json"
        >
          <Button icon={<UploadOutlined />}>{t('metamodel.selectFile')}</Button>
        </Upload>
      </Modal>

      {/* 查看模型详情模态框 */}
      <Modal
        title={`${t('metamodel.entityModelDetails')}: ${selectedModel?.type}@${selectedModel?.version}`}
        open={!!selectedModel}
        onCancel={() => setSelectedModel(null)}
        footer={null}
        width={800}
      >
        {selectedModel && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label={t('common.type')}>{selectedModel.type}</Descriptions.Item>
            <Descriptions.Item label={t('common.version')}>{selectedModel.version}</Descriptions.Item>
            <Descriptions.Item label={t('common.label')}>{selectedModel.label}</Descriptions.Item>
            <Descriptions.Item label={t('common.description')}>{selectedModel.description || '-'}</Descriptions.Item>
            <Descriptions.Item label={t('common.status')}>
              <Badge status={selectedModel.enabled ? 'success' : 'default'} text={selectedModel.enabled ? t('common.enabled') : t('common.disabled')} />
            </Descriptions.Item>
            <Descriptions.Item label={t('metamodel.propertiesCount')}>
              <pre style={{ maxHeight: 200, overflow: 'auto' }}>
                {JSON.stringify(selectedModel.properties, null, 2)}
              </pre>
            </Descriptions.Item>
            <Descriptions.Item label={t('metamodel.relationshipsCount')}>
              <pre style={{ maxHeight: 200, overflow: 'auto' }}>
                {JSON.stringify(selectedModel.relationships, null, 2)}
              </pre>
            </Descriptions.Item>
            {selectedModel.quality_rules && (
              <Descriptions.Item label={t('quality.rules')}>
                <pre style={{ maxHeight: 200, overflow: 'auto' }}>
                  {JSON.stringify(selectedModel.quality_rules, null, 2)}
                </pre>
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>

      {/* 编辑采集器模态框 */}
      <Modal
        title={`${t('metamodel.editCollector')}: ${editingCollector?.collector_type || ''}`}
        open={collectorModalVisible}
        onCancel={() => {
          setCollectorModalVisible(false);
          collectorForm.resetFields();
          setEditingCollector(null);
        }}
        onOk={() => collectorForm.submit()}
        confirmLoading={loading}
        width={800}
      >
        <Form form={collectorForm} onFinish={handleUpdateCollector} layout="vertical">
          <Form.Item name="collector_type" label={t('metamodel.collectorType')}>
            <Input disabled />
          </Form.Item>
          <Form.Item name="entity_type" label={t('metamodel.entityType')}>
            <Input disabled />
          </Form.Item>
          <Form.Item name="plugin" label={t('metamodel.pluginFile')}>
            <Input placeholder={t('metamodel.pluginFilePlaceholder')} />
          </Form.Item>
          <Form.Item name="entry" label={t('metamodel.entryFunction')}>
            <Input placeholder={t('metamodel.entryFunctionPlaceholder')} />
          </Form.Item>
          <Form.Item
            name="params"
            label={t('metamodel.paramsConfig')}
            rules={[
              {
                validator: (_, value) => {
                  if (!value) return Promise.resolve();
                  try {
                    JSON.parse(value);
                    return Promise.resolve();
                  } catch (e) {
                    return Promise.reject(new Error(t('metamodel.paramsJsonInvalid')));
                  }
                },
              },
            ]}
          >
            <TextArea rows={10} placeholder={t('metamodel.paramsConfigPlaceholder')} />
          </Form.Item>
        </Form>
      </Modal>

      {/* 插件编辑模态框 */}
      <Modal
        title={`${t('metamodel.editPlugin')}: ${editingPluginCollector?.collector_type || ''}`}
        open={pluginEditorVisible}
        onCancel={() => {
          setPluginEditorVisible(false);
          setEditingPluginCollector(null);
          setPluginCode('');
        }}
        onOk={handleUpdatePluginCode}
        confirmLoading={loading}
        width={1200}
        style={{ top: 20 }}
        bodyStyle={{ padding: '6px', paddingBottom: '4px' }}
      >
        <Alert
          message={t('metamodel.pluginCodeEdit')}
          description={t('metamodel.pluginCodeEditDescription')}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <div style={{ border: '1px solid #d9d9d9', borderRadius: '4px', overflow: 'hidden', marginBottom: 16 }}>
          <Editor
            height="calc(100vh - 380px)"
            defaultLanguage="python"
            language="python"
            value={pluginCode}
            onChange={(value) => setPluginCode(value || '')}
            theme="vs"
            loading={pluginCodeLoading}
            options={{
              minimap: { enabled: true },
              fontSize: 14,
              lineNumbers: 'on',
              roundedSelection: false,
              scrollBeyondLastLine: false,
              readOnly: false,
              automaticLayout: true,
              tabSize: 4,
              wordWrap: 'on',
              formatOnPaste: true,
              formatOnType: true,
              suggestOnTriggerCharacters: true,
              acceptSuggestionOnEnter: 'on',
              quickSuggestions: true,
              suggestSelection: 'first',
              wordBasedSuggestions: 'allDocuments',
              // 显示错误和警告
              renderValidationDecorations: 'on',
              // 代码折叠
              folding: true,
              foldingStrategy: 'auto',
              showFoldingControls: 'always',
              // 括号匹配
              matchBrackets: 'always',
              // 自动缩进
              autoIndent: 'full',
              // 显示空白字符（可选）
              renderWhitespace: 'selection',
            }}
            onMount={((_editor, monacoInstance) => {
              // 配置 Python 语言服务以提供更好的语法支持
              if (monacoInstance) {
                monacoInstance.languages.setLanguageConfiguration('python', {
                  comments: {
                    lineComment: '#',
                    blockComment: ['"""', '"""'],
                  },
                  brackets: [
                    ['{', '}'],
                    ['[', ']'],
                    ['(', ')'],
                  ],
                  autoClosingPairs: [
                    { open: '{', close: '}' },
                    { open: '[', close: ']' },
                    { open: '(', close: ')' },
                    { open: '"', close: '"' },
                    { open: "'", close: "'" },
                  ],
                  surroundingPairs: [
                    { open: '{', close: '}' },
                    { open: '[', close: ']' },
                    { open: '(', close: ')' },
                    { open: '"', close: '"' },
                    { open: "'", close: "'" },
                  ],
                });
              }
            }) as OnMount}
          />
        </div>
      </Modal>
    </div>
  );
}

