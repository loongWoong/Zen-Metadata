/**
 * 血缘追踪页面
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Tag,
  Space,
  Tabs,
  Alert,
  Spin,
  Descriptions,
  Statistic,
  Row,
  Col,
  Select,
  Slider,
  Typography,
  Empty,
} from 'antd';
import { SearchOutlined, ArrowUpOutlined, ArrowDownOutlined, WarningOutlined, TableOutlined, ApartmentOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import type { MetadataEntity, GraphData } from '../../types';
import { AutoComplete, message, Switch } from 'antd';
import ForceDirectedGraph from '../../components/ForceDirectedGraph';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface LineagePath {
  path: string[];
  relationships: string[];
  depth: number;
  path_length: number;
  quality_score: number;
  risk_score: number;
}

interface ImpactAnalysis {
  entity_id: string;
  direction: string;
  affected_entities: any[];
  paths: LineagePath[];
  risk_summary: {
    high_risk_count: number;
    medium_risk_count: number;
    low_risk_count: number;
    average_risk: number;
  };
  total_affected: number;
}

const LineageView: React.FC = () => {
  const { t } = useTranslation();
  const [entityId, setEntityId] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [lineageData, setLineageData] = useState<any>(null);
  const [upstreamPaths, setUpstreamPaths] = useState<LineagePath[]>([]);
  const [downstreamPaths, setDownstreamPaths] = useState<LineagePath[]>([]);
  const [impactAnalysis, setImpactAnalysis] = useState<ImpactAnalysis | null>(null);
  const [maxDepth, setMaxDepth] = useState<number>(5);
  const [granularity, setGranularity] = useState<string>('');
  
  // 实体查询相关状态
  const [entityType, setEntityType] = useState<string | undefined>();
  const [entityName, setEntityName] = useState<string>('');
  const [entityOptions, setEntityOptions] = useState<Array<{ value: string; label: string; entity: MetadataEntity }>>([]);
  const [searchingEntities, setSearchingEntities] = useState(false);
  const [entityTypes, setEntityTypes] = useState<string[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<MetadataEntity | null>(null);
  
  // Tab和视图切换（统一视图模式，所有Tab共享）
  const [activeTab, setActiveTab] = useState<string>('discover');
  const [viewMode, setViewMode] = useState<'table' | 'graph'>('table');
  
  // 图数据
  const [discoverGraphData, setDiscoverGraphData] = useState<GraphData | null>(null);
  const [upstreamGraphData, setUpstreamGraphData] = useState<GraphData | null>(null);
  const [downstreamGraphData, setDownstreamGraphData] = useState<GraphData | null>(null);
  const [impactGraphData, setImpactGraphData] = useState<GraphData | null>(null);

  // 加载实体类型列表
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
      setEntityTypes(['file', 'directory', 'function', 'class', 'table', 'column']);
    }
  };

  // 搜索实体
  const searchEntities = async (searchText: string) => {
    if (!searchText || searchText.trim().length < 1) {
      setEntityOptions([]);
      return;
    }

    setSearchingEntities(true);
    try {
      const response = await api.entities.search(searchText, {
        entity_type: entityType,
        limit: 50,
      });
      
      const options = response.data.results.map((entity: MetadataEntity) => ({
        value: entity.id,
        label: `${entity.name || entity.id} (${entity.type || 'unknown'})`,
        entity: entity,
      }));
      setEntityOptions(options);
    } catch (err: any) {
      console.error('搜索实体失败:', err);
      message.error('搜索实体失败');
      setEntityOptions([]);
    } finally {
      setSearchingEntities(false);
    }
  };

  // 搜索防抖定时器
  const searchTimerRef = React.useRef<NodeJS.Timeout | null>(null);

  // 处理实体名称输入变化（带防抖）
  const handleEntityNameChange = (value: string) => {
    setEntityName(value);
    
    // 清除之前的定时器
    if (searchTimerRef.current) {
      clearTimeout(searchTimerRef.current);
    }
    
    if (value && value.trim().length >= 1) {
      // 防抖：延迟300ms后搜索
      searchTimerRef.current = setTimeout(() => {
        searchEntities(value);
      }, 300);
    } else {
      setEntityOptions([]);
    }
  };

  // 清理定时器
  useEffect(() => {
    return () => {
      if (searchTimerRef.current) {
        clearTimeout(searchTimerRef.current);
      }
    };
  }, []);

  // 处理实体选择
  const handleEntitySelect = (value: string, option: any) => {
    const entity = option.entity;
    if (entity) {
      setSelectedEntity(entity);
      setEntityId(entity.id);
      setEntityName(entity.name || entity.id);
    }
  };

  // 初始化加载实体类型
  useEffect(() => {
    loadEntityTypes();
  }, []);

  // 转换血缘数据为图数据格式
  const convertLineageToGraphData = (lineageData: any): GraphData => {
    if (!lineageData?.graph) {
      return { nodes: [], edges: [] };
    }
    
    const graph = lineageData.graph;
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
      direction: edge.direction || 'unknown',
    }));
    
    return { nodes, edges };
  };

  // 转换路径数据为图数据格式
  const convertPathsToGraphData = (paths: LineagePath[], centerEntityId: string): GraphData => {
    const nodeMap = new Map<string, any>();
    const edgeSet = new Set<string>();
    
    // 添加中心节点
    nodeMap.set(centerEntityId, {
      id: centerEntityId,
      label: centerEntityId,
      type: 'unknown',
    });
    
    // 处理所有路径
    paths.forEach((path) => {
      path.path.forEach((nodeId) => {
        if (!nodeMap.has(nodeId)) {
          nodeMap.set(nodeId, {
            id: nodeId,
            label: nodeId,
            type: 'unknown',
          });
        }
      });
      
      // 添加边
      for (let i = 0; i < path.path.length - 1; i++) {
        const source = path.path[i];
        const target = path.path[i + 1];
        const edgeKey = `${source}-${target}`;
        if (!edgeSet.has(edgeKey)) {
          edgeSet.add(edgeKey);
        }
      }
    });
    
    const nodes = Array.from(nodeMap.values());
    const edges = Array.from(edgeSet).map((edgeKey) => {
      const [source, target] = edgeKey.split('-');
      return {
        source,
        target,
        type: 'related_to',
      };
    });
    
    return { nodes, edges };
  };

  // 发现血缘
  const handleDiscover = async () => {
    if (!entityId.trim()) {
      message.warning(t('lineage.inputEntityId'));
      return;
    }

    setLoading(true);
    try {
      const response = await api.lineage.discover(entityId, {
        granularity: granularity || undefined,
        max_depth: maxDepth,
      });
      setLineageData(response.data);
      
      // 转换为图数据
      const graphData = convertLineageToGraphData(response.data);
      setDiscoverGraphData(graphData);
      
      // 自动切换到血缘发现Tab
      setActiveTab('discover');
    } catch (error: any) {
      console.error('发现血缘失败:', error);
      message.error(t('lineage.loadLineageFailed') + ': ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 追踪上游
  const handleTraceUpstream = async () => {
    if (!entityId.trim()) {
      message.warning(t('lineage.inputEntityId'));
      return;
    }

    setLoading(true);
    try {
      const response = await api.lineage.traceUpstream(entityId, maxDepth > 0 ? maxDepth : undefined);
      const paths = response.data.paths || [];
      setUpstreamPaths(paths);
      
      // 转换为图数据
      const graphData = convertPathsToGraphData(paths, entityId);
      setUpstreamGraphData(graphData);
      
      // 自动切换到上游追踪Tab
      setActiveTab('upstream');
    } catch (error: any) {
      console.error('追踪上游失败:', error);
      message.error(t('lineage.loadLineageFailed') + ': ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 追踪下游
  const handleTraceDownstream = async () => {
    if (!entityId.trim()) {
      message.warning(t('lineage.inputEntityId'));
      return;
    }

    setLoading(true);
    try {
      const response = await api.lineage.traceDownstream(entityId, maxDepth > 0 ? maxDepth : undefined);
      const paths = response.data.paths || [];
      setDownstreamPaths(paths);
      
      // 转换为图数据
      const graphData = convertPathsToGraphData(paths, entityId);
      setDownstreamGraphData(graphData);
      
      // 自动切换到下游追踪Tab
      setActiveTab('downstream');
    } catch (error: any) {
      console.error('追踪下游失败:', error);
      message.error(t('lineage.loadLineageFailed') + ': ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 影响分析
  const handleAnalyzeImpact = async (direction: string = 'downstream') => {
    if (!entityId.trim()) {
      message.warning(t('lineage.inputEntityId'));
      return;
    }

    setLoading(true);
    try {
      const response = await api.lineage.analyzeImpact({
        entity_id: entityId,
        direction,
        include_quality: true,
      });
      setImpactAnalysis(response.data);
      
      // 转换为图数据（使用受影响实体和路径）
      const affectedEntities = response.data.affected_entities || [];
      const paths = response.data.paths || [];
      
      const nodeMap = new Map<string, any>();
      const edgeSet = new Set<string>();
      
      // 添加中心节点
      nodeMap.set(entityId, {
        id: entityId,
        label: entityId,
        type: 'unknown',
      });
      
      // 添加受影响实体
      affectedEntities.forEach((entity: any) => {
        nodeMap.set(entity.id, {
          id: entity.id,
          label: entity.name || entity.id,
          type: entity.type || 'unknown',
        });
      });
      
      // 添加路径中的节点和边
      paths.forEach((path: LineagePath) => {
        path.path.forEach((nodeId) => {
          if (!nodeMap.has(nodeId)) {
            nodeMap.set(nodeId, {
              id: nodeId,
              label: nodeId,
              type: 'unknown',
            });
          }
        });
        
        for (let i = 0; i < path.path.length - 1; i++) {
          const source = path.path[i];
          const target = path.path[i + 1];
          const edgeKey = `${source}-${target}`;
          edgeSet.add(edgeKey);
        }
      });
      
      const nodes = Array.from(nodeMap.values());
      const edges = Array.from(edgeSet).map((edgeKey) => {
        const [source, target] = edgeKey.split('-');
        return {
          source,
          target,
          type: 'related_to',
        };
      });
      
      setImpactGraphData({ nodes, edges });
      
      // 自动切换到影响分析Tab
      setActiveTab('impact');
    } catch (error: any) {
      console.error('影响分析失败:', error);
      message.error(t('lineage.impactAnalysisFailed') + ': ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  // 路径表格列
  const pathColumns = [
    {
      title: t('lineage.path'),
      key: 'path',
      render: (record: LineagePath) => (
        <Space>
          {record.path.map((id, idx) => (
            <React.Fragment key={idx}>
              <Tag>{id}</Tag>
              {idx < record.path.length - 1 && (
                <span style={{ color: '#999' }}>
                  {record.relationships[idx] || '→'}
                </span>
              )}
            </React.Fragment>
          ))}
        </Space>
      ),
    },
    {
      title: t('lineage.depth'),
      dataIndex: 'depth',
      key: 'depth',
      width: 80,
    },
    {
      title: t('lineage.pathLength'),
      dataIndex: 'path_length',
      key: 'path_length',
      width: 100,
    },
    {
      title: t('lineage.qualityScore'),
      dataIndex: 'quality_score',
      key: 'quality_score',
      width: 120,
      render: (score: number) => (
        <Tag color={score > 0.8 ? 'green' : score > 0.5 ? 'orange' : 'red'}>
          {(score * 100).toFixed(0)}%
        </Tag>
      ),
    },
    {
      title: t('lineage.riskScore'),
      dataIndex: 'risk_score',
      key: 'risk_score',
      width: 120,
      render: (score: number) => (
        <Tag color={score > 0.7 ? 'red' : score > 0.3 ? 'orange' : 'green'}>
          {(score * 100).toFixed(0)}%
        </Tag>
      ),
    },
  ];

  // 受影响实体表格列
  const affectedEntityColumns = [
    {
      title: t('lineage.entityId'),
      dataIndex: 'id',
      key: 'id',
    },
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
      title: t('lineage.riskScore'),
      dataIndex: 'risk_score',
      key: 'risk_score',
      render: (score: number) => (
        <Tag color={score > 0.7 ? 'red' : score > 0.3 ? 'orange' : 'green'}>
          {((score || 0) * 100).toFixed(0)}%
        </Tag>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>{t('lineage.title')}</Title>

      <Card style={{ marginBottom: '24px' }}>
        {/* 第一行：实体查询条件 */}
        <Space wrap style={{ width: '100%', marginBottom: 12 }}>
          <Text strong style={{ minWidth: '80px' }}>{t('lineage.entityId')}:</Text>
          <Select
            placeholder={t('lineage.entityId')}
            value={entityType}
            onChange={(value) => {
              setEntityType(value);
              if (entityName) {
                searchEntities(entityName);
              }
            }}
            style={{ width: 140 }}
            allowClear
            showSearch
            size="small"
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
          >
            {entityTypes.map((type) => (
              <Select.Option key={type} value={type} label={type}>
                {type}
              </Select.Option>
            ))}
          </Select>
          <AutoComplete
            placeholder={t('lineage.inputEntityId')}
            value={entityName}
            onChange={handleEntityNameChange}
            onSelect={handleEntitySelect}
            options={entityOptions}
            style={{ width: 280 }}
            loading={searchingEntities}
            filterOption={false}
            allowClear
            size="small"
            onClear={() => {
              setEntityName('');
              setEntityId('');
              setSelectedEntity(null);
              setEntityOptions([]);
            }}
          />
          <Text type="secondary" style={{ fontSize: '12px' }}>{t('common.or')} {t('lineage.inputEntityId')}:</Text>
          <Input
            placeholder={t('lineage.inputEntityId')}
            value={entityId}
            onChange={(e) => {
              setEntityId(e.target.value);
              if (e.target.value && selectedEntity?.id !== e.target.value) {
                setSelectedEntity(null);
                setEntityName('');
              }
            }}
            style={{ width: 220 }}
            onPressEnter={handleDiscover}
            size="small"
          />
        </Space>

        {/* 第二行：血缘参数和操作按钮 */}
        <Space wrap style={{ width: '100%' }}>
          <Select
            placeholder={t('lineage.granularity')}
            value={granularity}
            onChange={setGranularity}
            style={{ width: 120 }}
            allowClear
            size="small"
          >
            <Select.Option value="column">{t('lineage.column')}</Select.Option>
            <Select.Option value="table">{t('lineage.table')}</Select.Option>
            <Select.Option value="job">{t('lineage.job')}</Select.Option>
            <Select.Option value="system">{t('lineage.system')}</Select.Option>
          </Select>
          <Space size={4}>
            <Text style={{ fontSize: '12px' }}>{t('lineage.maxDepth')}:</Text>
            <Slider
              min={1}
              max={10}
              value={maxDepth}
              onChange={setMaxDepth}
              style={{ width: 120 }}
              tooltip={{ formatter: (value) => value?.toString() }}
            />
            <Text style={{ fontSize: '12px', minWidth: '20px' }}>{maxDepth}</Text>
          </Space>
          <Button type="primary" icon={<SearchOutlined />} onClick={handleDiscover} loading={loading} size="small">
            {t('lineage.loadLineage')}
          </Button>
          <Button icon={<ArrowUpOutlined />} onClick={handleTraceUpstream} loading={loading} size="small">
            {t('lineage.upstream')}
          </Button>
          <Button icon={<ArrowDownOutlined />} onClick={handleTraceDownstream} loading={loading} size="small">
            {t('lineage.downstream')}
          </Button>
          <Button
            icon={<WarningOutlined />}
            onClick={() => handleAnalyzeImpact('downstream')}
            loading={loading}
            size="small"
          >
            {t('lineage.downstream')} {t('lineage.impact')}
          </Button>
          <Button
            icon={<WarningOutlined />}
            onClick={() => handleAnalyzeImpact('upstream')}
            loading={loading}
            size="small"
          >
            {t('lineage.upstream')} {t('lineage.impact')}
          </Button>
        </Space>
      </Card>

      <Spin spinning={loading}>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane 
            tab={
              <span>
                {t('lineage.discover')}
                {lineageData && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    {lineageData.statistics?.total_entities || 0}
                  </Tag>
                )}
              </span>
            } 
            key="discover"
          >
            {lineageData ? (
              <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <Descriptions title={t('lineage.statistics')} bordered column={2} size="small">
                    <Descriptions.Item label={t('lineage.entityId')}>{lineageData.entity_id}</Descriptions.Item>
                    <Descriptions.Item label={t('lineage.granularity')}>{lineageData.granularity || t('common.all')}</Descriptions.Item>
                    <Descriptions.Item label={t('lineage.upstreamCount')}>{lineageData.statistics?.upstream_count || 0}</Descriptions.Item>
                    <Descriptions.Item label={t('lineage.downstreamCount')}>{lineageData.statistics?.downstream_count || 0}</Descriptions.Item>
                    <Descriptions.Item label={t('lineage.totalEntities')}>{lineageData.statistics?.total_entities || 0}</Descriptions.Item>
                    <Descriptions.Item label={t('lineage.maxDepth')}>{lineageData.statistics?.max_depth || 0}</Descriptions.Item>
                  </Descriptions>
                  <Space>
                    <Text>{t('common.view')}:</Text>
                    <Switch
                      checkedChildren={<ApartmentOutlined />}
                      unCheckedChildren={<TableOutlined />}
                      checked={viewMode === 'graph'}
                      onChange={(checked) => setViewMode(checked ? 'graph' : 'table')}
                    />
                  </Space>
                </div>

                {viewMode === 'table' ? (
                  <>
                    {lineageData.upstream_paths && lineageData.upstream_paths.length > 0 && (
                      <div style={{ marginTop: '24px' }}>
                        <Title level={4}>{t('lineage.upstream')} {t('lineage.path')}</Title>
                        <Table
                          dataSource={lineageData.upstream_paths}
                          columns={pathColumns}
                          rowKey={(record, index) => `upstream-${index}`}
                          pagination={{ pageSize: 10 }}
                          size="small"
                        />
                      </div>
                    )}

                    {lineageData.downstream_paths && lineageData.downstream_paths.length > 0 && (
                      <div style={{ marginTop: '24px' }}>
                        <Title level={4}>{t('lineage.downstream')} {t('lineage.path')}</Title>
                        <Table
                          dataSource={lineageData.downstream_paths}
                          columns={pathColumns}
                          rowKey={(record, index) => `downstream-${index}`}
                          pagination={{ pageSize: 10 }}
                          size="small"
                        />
                      </div>
                    )}
                  </>
                ) : (
                  <div style={{ height: '600px', border: '1px solid #d9d9d9', borderRadius: '4px', width: '100%' }}>
                    {discoverGraphData && discoverGraphData.nodes.length > 0 ? (
                      <ForceDirectedGraph
                        data={discoverGraphData}
                        width={1200}
                        height={600}
                        onNodeClick={(node) => {
                          console.log('点击节点:', node);
                        }}
                      />
                    ) : (
                      <Empty description={t('lineage.noLineageData')} style={{ marginTop: 200 }} />
                    )}
                  </div>
                )}
              </Card>
            ) : (
              <Alert message={t('lineage.discoverFirst')} type="info" />
            )}
          </TabPane>

          <TabPane 
            tab={
              <span>
                {t('lineage.upstream')} {t('lineage.trace')}
                {upstreamPaths.length > 0 && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    {upstreamPaths.length}
                  </Tag>
                )}
              </span>
            } 
            key="upstream"
          >
            {upstreamPaths.length > 0 ? (
              <Card>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
                  <Space>
                    <Text>{t('common.view')}:</Text>
                    <Switch
                      checkedChildren={<ApartmentOutlined />}
                      unCheckedChildren={<TableOutlined />}
                      checked={viewMode === 'graph'}
                      onChange={(checked) => setViewMode(checked ? 'graph' : 'table')}
                    />
                  </Space>
                </div>
                {viewMode === 'table' ? (
                  <Table
                    dataSource={upstreamPaths}
                    columns={pathColumns}
                    rowKey={(record, index) => `upstream-path-${index}`}
                    pagination={{ pageSize: 10 }}
                    size="small"
                  />
                ) : (
                  <div style={{ height: '600px', border: '1px solid #d9d9d9', borderRadius: '4px', width: '100%' }}>
                    {upstreamGraphData && upstreamGraphData.nodes.length > 0 ? (
                      <ForceDirectedGraph
                        data={upstreamGraphData}
                        width={1200}
                        height={600}
                        onNodeClick={(node) => {
                          console.log('点击节点:', node);
                        }}
                      />
                    ) : (
                      <Empty description={t('lineage.noLineageData')} style={{ marginTop: 200 }} />
                    )}
                  </div>
                )}
              </Card>
            ) : (
              <Alert message={t('lineage.noUpstreamData')} type="info" />
            )}
          </TabPane>

          <TabPane 
            tab={
              <span>
                {t('lineage.downstream')} {t('lineage.trace')}
                {downstreamPaths.length > 0 && (
                  <Tag color="blue" style={{ marginLeft: 8 }}>
                    {downstreamPaths.length}
                  </Tag>
                )}
              </span>
            } 
            key="downstream"
          >
            {downstreamPaths.length > 0 ? (
              <Card>
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 16 }}>
                  <Space>
                    <Text>{t('common.view')}:</Text>
                    <Switch
                      checkedChildren={<ApartmentOutlined />}
                      unCheckedChildren={<TableOutlined />}
                      checked={viewMode === 'graph'}
                      onChange={(checked) => setViewMode(checked ? 'graph' : 'table')}
                    />
                  </Space>
                </div>
                {viewMode === 'table' ? (
                  <Table
                    dataSource={downstreamPaths}
                    columns={pathColumns}
                    rowKey={(record, index) => `downstream-path-${index}`}
                    pagination={{ pageSize: 10 }}
                    size="small"
                  />
                ) : (
                  <div style={{ height: '600px', border: '1px solid #d9d9d9', borderRadius: '4px', width: '100%' }}>
                    {downstreamGraphData && downstreamGraphData.nodes.length > 0 ? (
                      <ForceDirectedGraph
                        data={downstreamGraphData}
                        width={1200}
                        height={600}
                        onNodeClick={(node) => {
                          console.log('点击节点:', node);
                        }}
                      />
                    ) : (
                      <Empty description={t('lineage.noLineageData')} style={{ marginTop: 200 }} />
                    )}
                  </div>
                )}
              </Card>
            ) : (
              <Alert message={t('lineage.noDownstreamData')} type="info" />
            )}
          </TabPane>

          <TabPane 
            tab={
              <span>
                {t('lineage.impactAnalysis')}
                {impactAnalysis && (
                  <Tag color="red" style={{ marginLeft: 8 }}>
                    {impactAnalysis.total_affected}
                  </Tag>
                )}
              </span>
            } 
            key="impact"
          >
            {impactAnalysis ? (
              <Card>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <Row gutter={16} style={{ flex: 1 }}>
                    <Col span={6}>
                      <Statistic
                        title={t('lineage.totalAffected')}
                        value={impactAnalysis.total_affected}
                        prefix={<WarningOutlined />}
                        valueStyle={{ fontSize: '20px' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={t('lineage.highRisk')}
                        value={impactAnalysis.risk_summary.high_risk_count}
                        valueStyle={{ color: '#cf1322', fontSize: '20px' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={t('lineage.mediumRisk')}
                        value={impactAnalysis.risk_summary.medium_risk_count}
                        valueStyle={{ color: '#fa8c16', fontSize: '20px' }}
                      />
                    </Col>
                    <Col span={6}>
                      <Statistic
                        title={t('lineage.lowRisk')}
                        value={impactAnalysis.risk_summary.low_risk_count}
                        valueStyle={{ color: '#3f8600', fontSize: '20px' }}
                      />
                    </Col>
                  </Row>
                  <Space>
                    <Text>{t('common.view')}:</Text>
                    <Switch
                      checkedChildren={<ApartmentOutlined />}
                      unCheckedChildren={<TableOutlined />}
                      checked={viewMode === 'graph'}
                      onChange={(checked) => setViewMode(checked ? 'graph' : 'table')}
                    />
                  </Space>
                </div>

                {viewMode === 'table' ? (
                  <>
                    <Title level={4}>{t('lineage.affectedEntities')}</Title>
                    <Table
                      dataSource={impactAnalysis.affected_entities}
                      columns={affectedEntityColumns}
                      rowKey="id"
                      pagination={{ pageSize: 10 }}
                      size="small"
                    />
                  </>
                ) : (
                  <div style={{ height: '600px', border: '1px solid #d9d9d9', borderRadius: '4px', width: '100%' }}>
                    {impactGraphData && impactGraphData.nodes.length > 0 ? (
                      <ForceDirectedGraph
                        data={impactGraphData}
                        width={1200}
                        height={600}
                        onNodeClick={(node) => {
                          console.log('点击节点:', node);
                        }}
                      />
                    ) : (
                      <Empty description={t('lineage.noLineageData')} style={{ marginTop: 200 }} />
                    )}
                  </div>
                )}
              </Card>
            ) : (
              <Alert message={t('lineage.noImpactData')} type="info" />
            )}
          </TabPane>
        </Tabs>
      </Spin>
    </div>
  );
};

export default LineageView;

