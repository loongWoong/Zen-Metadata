import { useEffect, useState } from 'react';
import {
  Table,
  Card,
  Input,
  Select,
  Button,
  Space,
  Tag,
  Modal,
  Descriptions,
  Spin,
  Alert,
  Dropdown,
  message,
  Form,
  Select as AntSelect,
  Tabs,
  List,
  Empty,
  Slider,
} from 'antd';

const { TextArea } = Input;
import {
  SearchOutlined,
  EyeOutlined,
  TagsOutlined,
  CommentOutlined,
  FileTextOutlined,
  CheckCircleOutlined,
  MoreOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import type { MetadataEntity, MetadataRelationship, GraphData } from '../../types';
import ForceDirectedGraph from '../../components/ForceDirectedGraph';

const { Search } = Input;
const { Option } = AntSelect;

export default function EntityBrowser() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [entities, setEntities] = useState<MetadataEntity[]>([]);
  const [total, setTotal] = useState(0);
  const [searchText, setSearchText] = useState('');
  const [entityType, setEntityType] = useState<string | undefined>();
  const [source, setSource] = useState<string | undefined>();
  const [entityTypes, setEntityTypes] = useState<string[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<MetadataEntity | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchModalVisible, setBatchModalVisible] = useState(false);
  const [batchActionType, setBatchActionType] = useState<'tag' | 'comment' | 'annotation' | 'approval' | null>(null);
  const [tags, setTags] = useState<any[]>([]);
  const [batchForm] = Form.useForm();
  const [relationships, setRelationships] = useState<{
    outgoing: MetadataRelationship[];
    incoming: MetadataRelationship[];
  } | null>(null);
  const [entityTags, setEntityTags] = useState<any[]>([]);
  const [entityComments, setEntityComments] = useState<any[]>([]);
  const [entityAnnotations, setEntityAnnotations] = useState<any[]>([]);
  const [entityApprovals, setEntityApprovals] = useState<any[]>([]);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [entityTagsMap, setEntityTagsMap] = useState<Record<string, any[]>>({});
  const [lineageData, setLineageData] = useState<GraphData | null>(null);
  const [loadingLineage, setLoadingLineage] = useState(false);
  const [lineageMaxDepth, setLineageMaxDepth] = useState(3);
  const [relatedEntitiesMap, setRelatedEntitiesMap] = useState<Record<string, MetadataEntity>>({});

  const loadEntities = async () => {
    try {
      setLoading(true);
      let entitiesList: MetadataEntity[] = [];
      if (searchText) {
        const response = await api.entities.search(searchText, {
          entity_type: entityType,
          source,
          limit: 100,
        });
        entitiesList = response.data.results;
        setTotal(response.data.count);
      } else {
        const response = await api.entities.list({
          entity_type: entityType,
          source,
          limit: 100,
        });
        entitiesList = response.data.entities;
        setTotal(response.data.count);
      }
      setEntities(entitiesList);
      
      // 批量加载标签（使用批量查询接口，避免N+1查询问题）
      if (entitiesList.length > 0) {
        try {
          const entityIds = entitiesList.map(entity => entity.id);
          const tagsRes = await api.governance.batchGetEntityTags(entityIds);
          setEntityTagsMap(tagsRes.data.tags_map || {});
        } catch (err) {
          console.error('批量加载标签失败:', err);
          // 如果批量查询失败，设置为空映射
          const emptyTagsMap: Record<string, any[]> = {};
          entitiesList.forEach(entity => {
            emptyTagsMap[entity.id] = [];
          });
          setEntityTagsMap(emptyTagsMap);
        }
      } else {
        setEntityTagsMap({});
      }
    } catch (err: any) {
      console.error('加载实体失败:', err);
      message.error(t('entityBrowser.loadEntitiesFailed'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEntities();
  }, [entityType, source]);

  useEffect(() => {
    loadEntityTypes();
    loadTags();
  }, []);

  const loadEntityTypes = async () => {
    try {
      const response = await api.statistics.entityDistribution();
      if (response.data?.data) {
        const types = response.data.data.map((item: any) => item.type).filter(Boolean);
        setEntityTypes(types);
      } else {
        const entitiesResponse = await api.entities.list({ limit: 1000 });
        const types = new Set<string>();
        entitiesResponse.data.entities.forEach((entity: any) => {
          if (entity.type) {
            types.add(entity.type);
          }
        });
        setEntityTypes(Array.from(types));
      }
    } catch (err: any) {
      console.error('加载实体类型失败:', err);
      message.error(t('entityBrowser.loadEntityTypesFailed'));
      setEntityTypes(['file', 'directory', 'function', 'class', 'table', 'column']);
    }
  };

  const loadTags = async () => {
    try {
      const response = await api.governance.listTags();
      setTags(response.data.tags);
    } catch (err: any) {
      console.error('加载标签失败:', err);
      message.error(t('entityBrowser.loadTagsFailed'));
    }
  };

  const loadLineage = async (entityId: string, maxDepth: number) => {
    setLoadingLineage(true);
    try {
      const response = await api.lineage.discover(entityId, { max_depth: maxDepth });
      if (response.data?.graph) {
        // 转换血缘图数据格式，保留方向信息
        const graph = response.data.graph;
        const nodes = (graph.nodes || []).map((node: any) => ({
          ...node,
          id: String(node.id || node.entity_id || node.id),
          label: node.name || node.label || node.id,
          type: node.type || 'unknown',
        }));
        const edges = (graph.edges || []).map((edge: any) => ({
          source: String(edge.source || edge.source_id),
          target: String(edge.target || edge.target_id),
          type: edge.type || 'related_to',
          direction: edge.direction || 'unknown', // 保留方向信息：upstream 或 downstream
        }));
        setLineageData({ nodes, edges });
      } else {
        setLineageData({ nodes: [], edges: [] });
      }
    } catch (err: any) {
      console.error('加载血缘失败:', err);
      message.error(t('entityBrowser.loadLineageAnalysisFailed') + ': ' + (err.response?.data?.detail || err.message));
      setLineageData({ nodes: [], edges: [] });
    } finally {
      setLoadingLineage(false);
    }
  };

  const loadRelatedEntities = async (relationships: { outgoing: MetadataRelationship[]; incoming: MetadataRelationship[] }) => {
    // 收集所有相关的实体ID
    const entityIds = new Set<string>();
    relationships.outgoing.forEach((rel) => {
      if (rel.target_id) entityIds.add(rel.target_id);
    });
    relationships.incoming.forEach((rel) => {
      if (rel.source_id) entityIds.add(rel.source_id);
    });

    // 批量获取实体信息
    const entitiesMap: Record<string, MetadataEntity> = {};
    await Promise.all(
      Array.from(entityIds).map(async (entityId) => {
        try {
          const response = await api.entities.get(entityId);
          entitiesMap[entityId] = response.data.entity;
        } catch (err) {
          console.error(`加载实体 ${entityId} 失败:`, err);
          message.error(t('entityBrowser.loadRelatedEntitiesFailed', { entityId }));
          // 如果加载失败，至少保存ID信息
          entitiesMap[entityId] = { id: entityId, name: entityId, type: 'unknown' } as MetadataEntity;
        }
      })
    );
    setRelatedEntitiesMap(entitiesMap);
  };

  const handleViewDetail = async (entity: MetadataEntity) => {
    setSelectedEntity(entity);
    setDetailVisible(true);
    setLoadingDetails(true);
    setLineageData(null);
    setRelatedEntitiesMap({});
    try {
      // 并行加载所有数据
      const [relationshipsRes, tagsRes, commentsRes, annotationsRes, approvalsRes] = await Promise.all([
        api.entities.getRelationships(entity.id).catch(() => ({ data: { outgoing: [], incoming: [] } })),
        api.governance.getEntityTags(entity.id).catch(() => ({ data: { tags: [], count: 0 } })),
        api.collaboration.getComments({ entity_id: entity.id }).catch(() => ({ data: { comments: [], count: 0 } })),
        api.collaboration.getAnnotations({ entity_id: entity.id }).catch(() => ({ data: { annotations: [], count: 0 } })),
        api.collaboration.getApprovals({ entity_id: entity.id }).catch(() => ({ data: { approvals: [], count: 0 } })),
      ]);
      
      setRelationships(relationshipsRes.data);
      setEntityTags(tagsRes.data.tags || []);
      setEntityComments(commentsRes.data.comments || []);
      setEntityAnnotations(annotationsRes.data.annotations || []);
      setEntityApprovals(approvalsRes.data.approvals || []);
      
      // 加载相关实体信息
      await loadRelatedEntities(relationshipsRes.data);
    } catch (err) {
      console.error('加载详情失败:', err);
      message.error(t('entityBrowser.loadDetailsFailed'));
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleBatchAction = (actionType: 'tag' | 'comment' | 'annotation' | 'approval') => {
    if (selectedRowKeys.length === 0) {
      message.warning(t('entityBrowser.pleaseSelectEntities'));
      return;
    }
    setBatchActionType(actionType);
    setBatchModalVisible(true);
    batchForm.resetFields();
  };

  const handleBatchSubmit = async () => {
    try {
      const values = await batchForm.validateFields();
      const entityIds = selectedRowKeys as string[];

      let response;
      switch (batchActionType) {
        case 'tag':
          response = await api.governance.batchAddEntityTags({
            entity_ids: entityIds,
            tag_id: values.tag_id,
            confidence: values.confidence || 1.0,
            is_auto: false,
          });
          break;
        case 'comment':
          response = await api.collaboration.batchCreateComments({
            entity_ids: entityIds,
            content: values.content,
            mentions: values.mentions || [],
          });
          break;
        case 'annotation':
          response = await api.collaboration.batchCreateAnnotations({
            entity_ids: entityIds,
            tag: values.tag,
            note: values.note,
            category: values.category,
          });
          break;
      case 'approval':
        let changeData = {};
        if (values.change_data) {
          try {
            changeData = typeof values.change_data === 'string' 
              ? JSON.parse(values.change_data) 
              : values.change_data;
          } catch (e) {
            message.error(t('entityBrowser.batchModal.changeDataFormatError'));
            return;
          }
        }
        response = await api.collaboration.batchCreateApprovals({
          entity_ids: entityIds,
          change_type: values.change_type,
          change_data: changeData,
          level: values.level,
        });
        break;
      }

      if (response.data.success) {
        message.success(
          t('entityBrowser.batchOperationSuccess') + `: ${response.data.succeeded}/${response.data.total}${t('entityBrowser.entitiesProcessed')}`
        );
        if (response.data.failed > 0) {
          message.warning(`${response.data.failed}${t('entityBrowser.entitiesFailed')}`);
        }
        setBatchModalVisible(false);
        setSelectedRowKeys([]);
        batchForm.resetFields();
      } else {
        message.error(t('entityBrowser.batchOperationFailed'));
      }
    } catch (error: any) {
      message.error(t('entityBrowser.batchOperationFailed') + ': ' + (error.response?.data?.detail || error.message));
    }
  };

  const rowSelection = {
    selectedRowKeys,
    onChange: (selectedKeys: React.Key[]) => {
      setSelectedRowKeys(selectedKeys);
    },
    getCheckboxProps: (record: MetadataEntity) => ({
      name: record.id,
    }),
  };

  const batchActionMenuItems = [
    {
      key: 'tag',
      label: t('entityBrowser.batchAddTags'),
      icon: <TagsOutlined />,
      onClick: () => handleBatchAction('tag'),
    },
    {
      key: 'comment',
      label: t('entityBrowser.batchCreateComments'),
      icon: <CommentOutlined />,
      onClick: () => handleBatchAction('comment'),
    },
    {
      key: 'annotation',
      label: t('entityBrowser.batchCreateAnnotations'),
      icon: <FileTextOutlined />,
      onClick: () => handleBatchAction('annotation'),
    },
    {
      key: 'approval',
      label: t('entityBrowser.batchCreateApprovals'),
      icon: <CheckCircleOutlined />,
      onClick: () => handleBatchAction('approval'),
    },
  ];

  const columns = [
    {
      title: t('entityBrowser.columns.id'),
      dataIndex: 'id',
      key: 'id',
      width: 200,
      ellipsis: true,
    },
    {
      title: t('entityBrowser.columns.name'),
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: t('entityBrowser.columns.type'),
      dataIndex: 'type',
      key: 'type',
      width: 120,
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: t('entityBrowser.columns.source'),
      dataIndex: 'source',
      key: 'source',
      width: 150,
    },
    {
      title: t('entityBrowser.columns.tags'),
      key: 'tags',
      width: 200,
      render: (_: any, record: MetadataEntity) => {
        const tags = entityTagsMap[record.id] || [];
        if (tags.length === 0) return <span style={{ color: '#999' }}>{t('common.none')}</span>;
        return (
          <Space wrap size={[4, 4]}>
            {tags.slice(0, 3).map((tag: any) => (
              <Tag
                key={tag.id || tag.tag_id}
                color={tag.color || '#1890ff'}
                style={{ margin: 0, fontSize: '12px' }}
              >
                {tag.name || tag.tag_name}
              </Tag>
            ))}
            {tags.length > 3 && (
              <Tag style={{ margin: 0, fontSize: '12px' }}>+{tags.length - 3}</Tag>
            )}
          </Space>
        );
      },
    },
    {
      title: t('entityBrowser.columns.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('entityBrowser.columns.actions'),
      key: 'action',
      width: 100,
      render: (_: any, record: MetadataEntity) => (
        <Button
          type="link"
          icon={<EyeOutlined />}
          onClick={() => handleViewDetail(record)}
        >
          {t('common.details')}
        </Button>
      ),
    },
  ];

  const renderBatchModalContent = () => {
    switch (batchActionType) {
      case 'tag':
        return (
          <>
            <Form.Item
              name="tag_id"
              label={t('entityBrowser.batchModal.tag')}
              rules={[{ required: true, message: t('entityBrowser.batchModal.selectTag') }]}
            >
              <AntSelect placeholder={t('entityBrowser.batchModal.selectTag')} showSearch>
                {tags.map((tag) => (
                  <Option key={tag.id} value={tag.id}>
                    <Space>
                      <div
                        style={{
                          width: 12,
                          height: 12,
                          backgroundColor: tag.color,
                          borderRadius: 2,
                          display: 'inline-block',
                        }}
                      />
                      {tag.name}
                    </Space>
                  </Option>
                ))}
              </AntSelect>
            </Form.Item>
            <Form.Item name="confidence" label={t('entityBrowser.batchModal.confidence')} initialValue={1.0}>
              <Input type="number" min={0} max={1} step={0.1} />
            </Form.Item>
          </>
        );
      case 'comment':
        return (
          <>
            <Form.Item
              name="content"
              label={t('entityBrowser.batchModal.comment')}
              rules={[{ required: true, message: t('entityBrowser.batchModal.inputComment') }]}
            >
              <TextArea rows={4} placeholder={t('entityBrowser.batchModal.inputComment')} />
            </Form.Item>
            <Form.Item name="mentions" label={t('entityBrowser.batchModal.mentionUsers')}>
              <AntSelect mode="tags" placeholder={t('entityBrowser.batchModal.inputUsernames')} />
            </Form.Item>
          </>
        );
      case 'annotation':
        return (
          <>
            <Form.Item
              name="tag"
              label={t('entityBrowser.batchModal.annotationTag')}
              rules={[{ required: true, message: t('entityBrowser.batchModal.inputAnnotationTag') }]}
            >
              <Input placeholder={t('entityBrowser.batchModal.inputAnnotationTag')} />
            </Form.Item>
            <Form.Item
              name="note"
              label={t('entityBrowser.batchModal.note')}
              rules={[{ required: true, message: t('common.pleaseInput') }]}
            >
              <TextArea rows={4} placeholder={t('common.pleaseInput')} />
            </Form.Item>
            <Form.Item name="category" label={t('entityBrowser.batchModal.category')}>
              <Input placeholder={t('common.optional')} />
            </Form.Item>
          </>
        );
      case 'approval':
        return (
          <>
            <Form.Item
              name="change_type"
              label={t('entityBrowser.batchModal.approvalChangeType')}
              rules={[{ required: true, message: t('common.pleaseSelect') }]}
            >
              <AntSelect placeholder={t('common.pleaseSelect')}>
                <Option value="update">{t('common.update')}</Option>
                <Option value="delete">{t('common.delete')}</Option>
                <Option value="create">{t('common.create')}</Option>
                <Option value="modify">{t('common.modify')}</Option>
              </AntSelect>
            </Form.Item>
            <Form.Item
              name="level"
              label={t('entityBrowser.batchModal.level')}
              rules={[{ required: true, message: t('common.pleaseSelect') }]}
            >
              <AntSelect placeholder={t('common.pleaseSelect')}>
                <Option value="low">{t('common.low')}</Option>
                <Option value="medium">{t('common.medium')}</Option>
                <Option value="high">{t('common.high')}</Option>
              </AntSelect>
            </Form.Item>
            <Form.Item
              name="change_data"
              label={t('entityBrowser.batchModal.changeData')}
              rules={[{ required: true, message: t('common.pleaseInput') }]}
            >
              <TextArea rows={4} placeholder='{"field": "value"}' />
            </Form.Item>
          </>
        );
      default:
        return null;
    }
  };

  return (
    <div>
      <Card
        title={t('entityBrowser.title')}
        extra={
          <Space>
            {selectedRowKeys.length > 0 && (
              <Dropdown menu={{ items: batchActionMenuItems }} trigger={['click']}>
                <Button type="primary" icon={<MoreOutlined />}>
                  {t('common.actions')} ({selectedRowKeys.length})
                </Button>
              </Dropdown>
            )}
            <Search
              placeholder={t('entityBrowser.searchPlaceholder')}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={loadEntities}
              style={{ width: 300 }}
              allowClear
            />
            <Select
              placeholder={t('entityBrowser.entityType')}
              value={entityType}
              onChange={setEntityType}
              style={{ width: 150 }}
              allowClear
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            >
              <Select.Option value={undefined} label={t('entityBrowser.allTypes')}>
                {t('entityBrowser.allTypes')}
              </Select.Option>
              {entityTypes.map((type) => (
                <Select.Option key={type} value={type} label={type}>
                  {type}
                </Select.Option>
              ))}
            </Select>
            <Button onClick={loadEntities}>{t('common.refresh')}</Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={entities}
          loading={loading}
          rowKey="id"
          rowSelection={rowSelection}
            pagination={{
              total,
              pageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `${t('common.all')} ${total}`,
            }}
        />
      </Card>

      <Modal
        title={t('entityBrowser.detail.title')}
        open={detailVisible}
        onCancel={() => {
          setDetailVisible(false);
          setSelectedEntity(null);
          setRelationships(null);
          setEntityTags([]);
          setEntityComments([]);
          setEntityAnnotations([]);
          setEntityApprovals([]);
          setLineageData(null);
          setRelatedEntitiesMap({});
        }}
        footer={null}
        width={900}
      >
        {selectedEntity && (
          <Spin spinning={loadingDetails}>
            <Tabs
              defaultActiveKey="basic"
              items={[
                {
                  key: 'basic',
                  label: t('entityBrowser.detail.basicInfo'),
                  children: (
                    <div>
                      <Descriptions bordered column={2}>
                        <Descriptions.Item label={t('common.id')}>{selectedEntity.id}</Descriptions.Item>
                        <Descriptions.Item label={t('common.name')}>{selectedEntity.name}</Descriptions.Item>
                        <Descriptions.Item label={t('common.type')}>{selectedEntity.type}</Descriptions.Item>
                        <Descriptions.Item label={t('common.source')}>{selectedEntity.source}</Descriptions.Item>
                        <Descriptions.Item label={t('common.description')} span={2}>
                          {selectedEntity.description || t('common.none')}
                        </Descriptions.Item>
                        <Descriptions.Item label={t('common.createdAt')} span={2}>
                          {selectedEntity.created_at}
                        </Descriptions.Item>
                      </Descriptions>

                      {relationships && (
                        <div style={{ marginTop: 24 }}>
                          <h3>{t('entityBrowser.detail.outgoing')} ({relationships.outgoing.length})</h3>
                          <Table
                            dataSource={relationships.outgoing}
                            rowKey={(r, i) => `${r.source_id}-${r.target_id}-${i}`}
                            pagination={false}
                            size="small"
                            columns={[
                              {
                                title: '目标实体',
                                key: 'target',
                                width: 180,
                                ellipsis: true,
                                render: (_: any, record: MetadataRelationship) => {
                                  const targetEntity = relatedEntitiesMap[record.target_id];
                                  if (targetEntity) {
                                    return (
                                      <a
                                        href="#"
                                        onClick={(e) => {
                                          e.preventDefault();
                                          handleViewDetail(targetEntity);
                                        }}
                                        title={targetEntity.name || targetEntity.id}
                                      >
                                        {targetEntity.name || targetEntity.id}
                                      </a>
                                    );
                                  }
                                  return <span title={record.target_id}>{record.target_id}</span>;
                                },
                              },
                              {
                                title: '实体ID',
                                dataIndex: 'target_id',
                                key: 'target_id',
                                width: 280,
                                ellipsis: {
                                  showTitle: true,
                                },
                              },
                              {
                                title: '关系类型',
                                dataIndex: 'type',
                                key: 'type',
                                width: 120,
                                ellipsis: true,
                              },
                            ]}
                          />

                          <h3 style={{ marginTop: 24 }}>{t('entityBrowser.detail.incoming')} ({relationships.incoming.length})</h3>
                          <Table
                            dataSource={relationships.incoming}
                            rowKey={(r, i) => `${r.source_id}-${r.target_id}-${i}`}
                            pagination={false}
                            size="small"
                            columns={[
                              {
                                title: '源实体',
                                key: 'source',
                                width: 180,
                                ellipsis: true,
                                render: (_: any, record: MetadataRelationship) => {
                                  const sourceEntity = relatedEntitiesMap[record.source_id];
                                  if (sourceEntity) {
                                    return (
                                      <a
                                        href="#"
                                        onClick={(e) => {
                                          e.preventDefault();
                                          handleViewDetail(sourceEntity);
                                        }}
                                        title={sourceEntity.name || sourceEntity.id}
                                      >
                                        {sourceEntity.name || sourceEntity.id}
                                      </a>
                                    );
                                  }
                                  return <span title={record.source_id}>{record.source_id}</span>;
                                },
                              },
                              {
                                title: '实体ID',
                                dataIndex: 'source_id',
                                key: 'source_id',
                                width: 280,
                                ellipsis: {
                                  showTitle: true,
                                },
                              },
                              {
                                title: '关系类型',
                                dataIndex: 'type',
                                key: 'type',
                                width: 120,
                                ellipsis: true,
                              },
                            ]}
                          />
                        </div>
                      )}
                    </div>
                  ),
                },
                {
                  key: 'tags',
                  label: `${t('entityBrowser.detail.tags')} (${entityTags.length})`,
                  children: (
                    <div>
                      {entityTags.length > 0 ? (
                        <Space wrap>
                          {entityTags.map((tag: any) => (
                            <Tag
                              key={tag.id || tag.tag_id}
                              color={tag.color || '#1890ff'}
                              style={{ padding: '4px 8px', fontSize: '14px' }}
                            >
                              {tag.name || tag.tag_name}
                            </Tag>
                          ))}
                        </Space>
                      ) : (
                        <Empty description={t('entityBrowser.detail.noTags')} />
                      )}
                    </div>
                  ),
                },
                {
                  key: 'comments',
                  label: `${t('entityBrowser.detail.comments')} (${entityComments.length})`,
                  children: (
                    <div>
                      {entityComments.length > 0 ? (
                        <List
                          dataSource={entityComments}
                          renderItem={(comment) => (
                            <List.Item>
                              <List.Item.Meta
                                title={
                                  <Space>
                                    <span>{comment.user_id || t('common.anonymous')}</span>
                                    <span style={{ color: '#999', fontSize: '12px' }}>
                                      {new Date(comment.created_at).toLocaleString()}
                                    </span>
                                  </Space>
                                }
                                description={comment.content}
                              />
                            </List.Item>
                          )}
                        />
                      ) : (
                        <Empty description={t('entityBrowser.detail.noComments')} />
                      )}
                    </div>
                  ),
                },
                {
                  key: 'annotations',
                  label: `${t('entityBrowser.detail.annotations')} (${entityAnnotations.length})`,
                  children: (
                    <div>
                      {entityAnnotations.length > 0 ? (
                        <List
                          dataSource={entityAnnotations}
                          renderItem={(annotation) => (
                            <List.Item>
                              <List.Item.Meta
                                title={
                                  <Space>
                                    <Tag>{annotation.tag}</Tag>
                                    {annotation.category && <Tag color="blue">{annotation.category}</Tag>}
                                    <span style={{ color: '#999', fontSize: '12px' }}>
                                      {new Date(annotation.created_at).toLocaleString()}
                                    </span>
                                  </Space>
                                }
                                description={annotation.note}
                              />
                            </List.Item>
                          )}
                        />
                      ) : (
                        <Empty description={t('entityBrowser.detail.noAnnotations')} />
                      )}
                    </div>
                  ),
                },
                {
                  key: 'approvals',
                  label: `${t('entityBrowser.detail.approvals')} (${entityApprovals.length})`,
                  children: (
                    <div>
                      {entityApprovals.length > 0 ? (
                        <List
                          dataSource={entityApprovals}
                          renderItem={(approval) => (
                            <List.Item>
                              <List.Item.Meta
                                title={
                                  <Space>
                                    <Tag color={
                                      approval.status === 'approved' ? 'green' :
                                      approval.status === 'rejected' ? 'red' : 'orange'
                                    }>
                                      {approval.status === 'approved' ? t('common.approved') :
                                       approval.status === 'rejected' ? t('common.rejected') : t('common.pending')}
                                    </Tag>
                                    <Tag>{approval.change_type}</Tag>
                                    <Tag>{approval.level}</Tag>
                                    <span style={{ color: '#999', fontSize: '12px' }}>
                                      {new Date(approval.created_at).toLocaleString()}
                                    </span>
                                  </Space>
                                }
                                description={
                                  <div>
                                    <div>{t('common.requester')}: {approval.requester_id}</div>
                                    {approval.approver_id && <div>{t('common.approver')}: {approval.approver_id}</div>}
                                    {approval.comment && <div>{t('common.comment')}: {approval.comment}</div>}
                                  </div>
                                }
                              />
                            </List.Item>
                          )}
                        />
                      ) : (
                        <Empty description={t('entityBrowser.detail.noApprovals')} />
                      )}
                    </div>
                  ),
                },
                {
                  key: 'lineage',
                  label: t('entityBrowser.detail.lineage'),
                  children: (
                    <div>
                      <Space style={{ marginBottom: 16 }} wrap>
                        <Space>
                          <span>{t('entityBrowser.detail.maxDepth')}:</span>
                          <Slider
                            min={1}
                            max={5}
                            value={lineageMaxDepth}
                            onChange={setLineageMaxDepth}
                            style={{ width: 150 }}
                          />
                          <span>{lineageMaxDepth}</span>
                        </Space>
                        <Button
                          type="primary"
                          onClick={() => selectedEntity && loadLineage(selectedEntity.id, lineageMaxDepth)}
                          loading={loadingLineage}
                        >
                          {t('lineage.loadLineage')}
                        </Button>
                      </Space>
                      {lineageData && lineageData.nodes.length > 0 && (
                        <div style={{ marginBottom: 16, padding: '8px', background: '#f5f5f5', borderRadius: '4px' }}>
                          <Space>
                            <span>{t('graphView.legend')}:</span>
                            <Space>
                              <div style={{ display: 'inline-block', width: '20px', height: '2px', background: '#1890ff', verticalAlign: 'middle' }}></div>
                              <span>{t('lineage.upstream')}</span>
                            </Space>
                            <Space>
                              <div style={{ display: 'inline-block', width: '20px', height: '2px', background: '#52c41a', verticalAlign: 'middle' }}></div>
                              <span>{t('lineage.downstream')}</span>
                            </Space>
                            <span style={{ color: '#999', fontSize: '12px' }}>
                              ({t('graphView.nodeTypes')}: {lineageData.nodes.length}, {t('graphView.edgeTypes')}: {lineageData.edges.length})
                            </span>
                          </Space>
                        </div>
                      )}
                      {loadingLineage ? (
                        <div style={{ textAlign: 'center', padding: '50px' }}>
                          <Spin size="large" />
                        </div>
                      ) : lineageData ? (
                        lineageData.nodes.length > 0 ? (
                          <div style={{ height: '500px', border: '1px solid #d9d9d9', borderRadius: '4px' }}>
                            <ForceDirectedGraph
                              data={lineageData}
                              width={750}
                              height={500}
                              onNodeClick={(node) => {
                                // 可以点击节点查看详情
                                console.log('点击节点:', node);
                              }}
                            />
                          </div>
                        ) : (
                          <Empty description={t('entityBrowser.detail.noLineageData')} />
                        )
                      ) : (
                        <Empty description={t('entityBrowser.detail.noLineageData')} />
                      )}
                    </div>
                  ),
                },
              ]}
            />
          </Spin>
        )}
      </Modal>

      <Modal
        title={
          batchActionType === 'tag'
            ? t('entityBrowser.batchAddTags')
            : batchActionType === 'comment'
            ? t('entityBrowser.batchCreateComments')
            : batchActionType === 'annotation'
            ? t('entityBrowser.batchCreateAnnotations')
            : batchActionType === 'approval'
            ? t('entityBrowser.batchCreateApprovals')
            : t('common.actions')
        }
        open={batchModalVisible}
        onOk={handleBatchSubmit}
        onCancel={() => {
          setBatchModalVisible(false);
          batchForm.resetFields();
        }}
        width={600}
      >
        <Alert
          message={`${t('common.selected')} ${selectedRowKeys.length} ${t('common.entities')}`}
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
        <Form form={batchForm} layout="vertical">
          {renderBatchModalContent()}
        </Form>
      </Modal>
    </div>
  );
}
