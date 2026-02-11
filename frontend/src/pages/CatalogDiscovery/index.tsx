import { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Input,
  Select,
  Space,
  Tag,
  Button,
  Row,
  Col,
  List,
  Typography,
  Empty,
  Modal,
  Descriptions,
  Spin,
  Tabs,
  message,
  Slider,
} from 'antd';
import {
  SearchOutlined,
  StarOutlined,
  EyeOutlined,
  TagOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import type { MetadataEntity, MetadataRelationship, GraphData } from '../../types';
import ForceDirectedGraph from '../../components/ForceDirectedGraph';

const { Option } = Select;
const { Title, Text } = Typography;

export default function CatalogDiscovery() {
  const { t } = useTranslation();
  const [entities, setEntities] = useState<any[]>([]);
  const [discoveredEntities, setDiscoveredEntities] = useState<any[]>([]);
  const [usageAnalytics, setUsageAnalytics] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [discoverLoading, setDiscoverLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    category: undefined,
    tag_id: undefined,
    entity_type: undefined,
    source: undefined,
  });
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });
  const [selectedEntity, setSelectedEntity] = useState<MetadataEntity | null>(null);
  const [detailVisible, setDetailVisible] = useState(false);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [relationships, setRelationships] = useState<{
    outgoing: MetadataRelationship[];
    incoming: MetadataRelationship[];
  } | null>(null);
  const [entityTags, setEntityTags] = useState<any[]>([]);
  const [entityComments, setEntityComments] = useState<any[]>([]);
  const [entityAnnotations, setEntityAnnotations] = useState<any[]>([]);
  const [entityApprovals, setEntityApprovals] = useState<any[]>([]);
  const [lineageData, setLineageData] = useState<GraphData | null>(null);
  const [loadingLineage, setLoadingLineage] = useState(false);
  const [lineageMaxDepth, setLineageMaxDepth] = useState(3);
  const [relatedEntitiesMap, setRelatedEntitiesMap] = useState<Record<string, MetadataEntity>>({});
  const [sources, setSources] = useState<string[]>([]);
  const [entityTypes, setEntityTypes] = useState<string[]>([]);

  // 加载数据源
  const loadSources = async () => {
    try {
      const entitiesResponse = await api.entities.list({ limit: 1000 });
      const sourcesSet = new Set<string>();
      entitiesResponse.data.entities.forEach((entity: any) => {
        if (entity.source) {
          sourcesSet.add(entity.source);
        }
      });
      setSources(Array.from(sourcesSet).sort());
    } catch (err: any) {
      console.error('加载数据源失败:', err);
      setSources([]);
    }
  };

  // 加载实体类型
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
      setEntityTypes([]);
    }
  };

  useEffect(() => {
    loadSources();
    loadEntityTypes();
    loadCatalog();
    loadUsageAnalytics();
  }, [filters, pagination.current, pagination.pageSize]);

  const loadCatalog = async () => {
    setLoading(true);
    try {
      const response = await api.governance.browseCatalog({
        ...filters,
        limit: pagination.pageSize,
        offset: (pagination.current - 1) * pagination.pageSize,
      });
      setEntities(response.data.entities);
      setPagination((prev) => ({ ...prev, total: response.data.total }));
    } catch (error: any) {
      console.error('加载目录失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadUsageAnalytics = async () => {
    try {
      const response = await api.governance.getUsageAnalytics();
      setUsageAnalytics(response.data);
    } catch (error: any) {
      console.error('加载使用分析失败:', error);
    }
  };

  const handleDiscover = async () => {
    if (!searchQuery.trim()) {
      return;
    }
    setDiscoverLoading(true);
    try {
      const response = await api.governance.discoverEntities({
        q: searchQuery,
        limit: 10,
      });
      setDiscoveredEntities(response.data.entities);
    } catch (error: any) {
      console.error('发现失败:', error);
    } finally {
      setDiscoverLoading(false);
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
      message.error('加载血缘分析失败: ' + (err.response?.data?.detail || err.message));
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
      message.error('加载实体详情失败');
    } finally {
      setLoadingDetails(false);
    }
  };

  const columns = [
    {
      title: t('common.name'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <Space>
          <a
            href="#"
            onClick={(e) => {
              e.preventDefault();
              handleViewDetail(record);
            }}
          >
            {text}
          </a>
          {record.tags && record.tags.length > 0 && (
            <Space size="small">
              {record.tags.slice(0, 3).map((tag: any) => (
                <Tag key={tag.id} color={tag.color}>
                  {tag.name}
                </Tag>
              ))}
            </Space>
          )}
        </Space>
      ),
    },
    {
      title: t('common.type'),
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: t('common.source'),
      dataIndex: 'source',
      key: 'source',
    },
    {
      title: t('common.description'),
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: t('catalog.discoveryScore'),
      dataIndex: 'discovery_score',
      key: 'discovery_score',
      render: (score: number) => score ? `${(score * 100).toFixed(1)}%` : '-',
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <DatabaseOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('catalog.totalEntities')}</span>
              </div>
              <span style={{ fontSize: 20, fontWeight: 600 }}>{pagination.total}</span>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <StarOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('catalog.highUsage')}</span>
              </div>
              <span style={{ fontSize: 20, fontWeight: 600 }}>{usageAnalytics?.high_usage?.length || 0}</span>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <EyeOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('catalog.lowUsage')}</span>
              </div>
              <span style={{ fontSize: 20, fontWeight: 600 }}>{usageAnalytics?.low_usage?.length || 0}</span>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <SearchOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('catalog.discovered')}</span>
              </div>
              <span style={{ fontSize: 20, fontWeight: 600 }}>{discoveredEntities.length}</span>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title={t('catalog.discover')} style={{ marginBottom: 16 }}>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            placeholder={t('catalog.searchPlaceholder')}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onPressEnter={handleDiscover}
            style={{ width: 'calc(100% - 100px)' }}
          />
          <Button
            type="primary"
            icon={<SearchOutlined />}
            onClick={handleDiscover}
            loading={discoverLoading}
          >
            {t('catalog.discover')}
          </Button>
        </Space.Compact>

        {discoveredEntities.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <Title level={5}>{t('catalog.discoverResults')}</Title>
            <List
              dataSource={discoveredEntities}
              renderItem={(item: any) => (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <Space>
                        <a
                          href="#"
                          onClick={(e) => {
                            e.preventDefault();
                            handleViewDetail(item);
                          }}
                        >
                          {item.name}
                        </a>
                        <Tag>{item.type}</Tag>
                        {item.discovery_score && (
                          <Text type="secondary">
                            {t('catalog.score')}: {(item.discovery_score * 100).toFixed(1)}%
                          </Text>
                        )}
                      </Space>
                    }
                    description={item.description}
                  />
                </List.Item>
              )}
            />
          </div>
        )}
      </Card>

      <Card
        title={t('catalog.title')}
        extra={
          <Space>
            <Select
              placeholder={t('catalog.category')}
              allowClear
              style={{ width: 120 }}
              value={filters.category}
              onChange={(value) => setFilters({ ...filters, category: value })}
            >
              <Option value="业务域">{t('catalog.businessDomain')}</Option>
              <Option value="技术栈">{t('catalog.techStack')}</Option>
              <Option value="数据敏感度">{t('catalog.dataSensitivity')}</Option>
              <Option value="生命周期">{t('catalog.lifecycle')}</Option>
            </Select>
            <Select
              placeholder={t('catalog.selectEntityType')}
              allowClear
              style={{ width: 150 }}
              value={filters.entity_type}
              onChange={(value) => setFilters({ ...filters, entity_type: value })}
              showSearch
              notFoundContent={entityTypes.length === 0 ? t('common.loading') : t('common.noData')}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {entityTypes.map((type) => (
                <Option key={type} value={type} label={type}>
                  {type}
                </Option>
              ))}
            </Select>
            <Select
              placeholder={t('catalog.selectSource')}
              allowClear
              style={{ width: 150 }}
              value={filters.source}
              onChange={(value) => setFilters({ ...filters, source: value })}
              showSearch
              notFoundContent={sources.length === 0 ? t('common.loading') : t('common.noData')}
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            >
              {sources.map((src) => (
                <Option key={src} value={src} label={src}>
                  {src}
                </Option>
              ))}
            </Select>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={entities}
          rowKey="id"
          loading={loading}
          pagination={{
            ...pagination,
            showSizeChanger: true,
            showTotal: (total) => `${t('common.all')} ${total}`,
            onChange: (page, pageSize) => {
              setPagination({ ...pagination, current: page, pageSize });
            },
          }}
        />
      </Card>

      {usageAnalytics && (
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={12}>
            <Card title={t('catalog.highUsage')}>
              <List
                dataSource={usageAnalytics.high_usage || []}
                renderItem={(item: any) => (
                  <List.Item>
                    <Space>
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          // 需要先获取完整的实体信息
                          api.entities.get(item.entity_id)
                            .then((res) => {
                              handleViewDetail(res.data.entity);
                            })
                            .catch((err) => {
                              console.error('获取实体失败:', err);
                              message.error(t('catalog.loadEntitiesFailed'));
                            });
                        }}
                      >
                        {item.entity_name}
                      </a>
                      <Tag>{item.entity_type}</Tag>
                      <Text type="secondary">{t('catalog.usageCount')}: {item.usage_count}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card title={t('catalog.lowUsage')}>
              <List
                dataSource={usageAnalytics.low_usage || []}
                renderItem={(item: any) => (
                  <List.Item>
                    <Space>
                      <a
                        href="#"
                        onClick={(e) => {
                          e.preventDefault();
                          // 需要先获取完整的实体信息
                          api.entities.get(item.entity_id)
                            .then((res) => {
                              handleViewDetail(res.data.entity);
                            })
                            .catch((err) => {
                              console.error('获取实体失败:', err);
                              message.error(t('catalog.loadEntitiesFailed'));
                            });
                        }}
                      >
                        {item.entity_name}
                      </a>
                      <Tag>{item.entity_type}</Tag>
                      <Text type="secondary">{t('catalog.usageCount')}: {item.usage_count}</Text>
                    </Space>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>
      )}

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
    </div>
  );
}

