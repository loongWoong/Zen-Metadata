import { useEffect, useState, useMemo } from 'react';
import { Card, Select, Input, Button, Space, Spin, Alert, Slider, Drawer, Tag, Divider, Collapse, Descriptions, Empty, Tabs, InputNumber, Tooltip, Switch } from 'antd';
import { SearchOutlined, ReloadOutlined, UpOutlined, DownOutlined, ApartmentOutlined, SaveOutlined, SettingOutlined } from '@ant-design/icons';
import api from '../../services/api';
import type { GraphData, GraphNode } from '../../types';
import ForceDirectedGraph from '../../components/ForceDirectedGraph';
import HierarchyLayout from '../../components/GraphLayouts/HierarchyLayout';
import TemporalLayout from '../../components/GraphLayouts/TemporalLayout';
import CentralityAnalysis from '../../components/GraphAnalysis/CentralityAnalysis';
import CommunityDetection, { detectCommunities } from '../../components/GraphAnalysis/CommunityDetection';
import NodeAggregation from '../../components/GraphInteractions/NodeAggregation';
import SubgraphExtraction from '../../components/GraphInteractions/SubgraphExtraction';
import PathHighlight from '../../components/GraphInteractions/PathHighlight';
import { graphConfig } from '../../utils/graphConfig';
import { useTranslation } from 'react-i18next';

export default function GraphView() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [entityType, setEntityType] = useState<string>('');
  const [entityId, setEntityId] = useState<string>('');
  const [source, setSource] = useState<string>('');
  const [depth, setDepth] = useState(1);
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], edges: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [legendCollapsed, setLegendCollapsed] = useState(true); // 默认折叠，节省空间
  const [filteredNodeTypes, setFilteredNodeTypes] = useState<Set<string>>(new Set());
  const [filteredEdgeTypes, setFilteredEdgeTypes] = useState<Set<string>>(new Set());
  const [nodeTags, setNodeTags] = useState<any[]>([]);
  const [loadingNodeDetails, setLoadingNodeDetails] = useState(false);
  const [layoutType, setLayoutType] = useState<'force' | 'hierarchy' | 'temporal'>('force');
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [aggregatedData, setAggregatedData] = useState<GraphData | null>(null);
  const [highlightedPaths, setHighlightedPaths] = useState<string[][]>([]);
  const [entityTypes, setEntityTypes] = useState<string[]>([]);
  const [sources, setSources] = useState<string[]>([]);
  const [maxNodes, setMaxNodes] = useState<number>(graphConfig.maxNodes);
  const [maxEdges, setMaxEdges] = useState<number>(graphConfig.maxEdges);
  const [showLimitConfig, setShowLimitConfig] = useState(false);
  const [showNodeLabels, setShowNodeLabels] = useState<boolean>(false); // 默认不显示节点名
  const [showEdgeLabels, setShowEdgeLabels] = useState<boolean>(false); // 默认不显示关系名

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

  const loadGraph = async () => {
    try {
      setLoading(true);
      setError(null);
      // 构建查询参数，确保空字符串被转换为undefined
      const params: {
        entity_id?: string;
        entity_type?: string;
        depth?: number;
        layout?: string;
      } = {
        depth,
        layout: 'spring', // 力引导图不需要后端布局
      };
      
      if (entityId && entityId.trim()) {
        params.entity_id = entityId.trim();
      }
      
      if (entityType && entityType.trim()) {
        params.entity_type = entityType.trim();
      }
      
      const response = await api.visualize.get(params);

      const data = response.data.graph;

      console.log('GraphView - 原始数据:', {
        nodesCount: data.nodes?.length || 0,
        edgesCount: data.edges?.length || 0,
        sampleNode: data.nodes?.[0],
        sampleEdge: data.edges?.[0],
      });

      // 创建节点ID集合，用于验证边的有效性
      const nodeIdSet = new Set(data.nodes.map((node: any) => String(node.id)));

      console.log('GraphView - 节点ID集合:', {
        nodeIds: Array.from(nodeIdSet).slice(0, 10),
        totalNodes: nodeIdSet.size,
      });

      // 过滤并转换边，只保留有效的边
      const validEdges = data.edges
        .map((edge: any) => {
          const source = String(edge.source);
          const target = String(edge.target);
          
          // 验证边的源和目标节点都存在
          const sourceExists = nodeIdSet.has(source);
          const targetExists = nodeIdSet.has(target);
          
          if (!sourceExists || !targetExists) {
            console.warn('GraphView - 无效的边:', {
              source,
              target,
              sourceExists,
              targetExists,
              edge,
            });
          }
          
          if (sourceExists && targetExists) {
            return {
              source,
              target,
              type: edge.type || 'related_to',
              ...edge,
            };
          }
          return null;
        })
        .filter((edge: any): edge is any => edge !== null);

      console.log('GraphView - 处理后的边:', {
        validEdgesCount: validEdges.length,
        originalEdgesCount: data.edges?.length || 0,
        sampleValidEdge: validEdges[0],
      });

      // 确保节点有 label 属性，并加载标签
      const validNodes = data.nodes.map((node: any) => ({
        ...node,
        id: String(node.id),
        label: node.label || node.name || node.id,
        type: node.type || 'unknown',
      }));

      // 先设置没有标签的数据，让图先渲染
      setGraphData({
        nodes: validNodes,
        edges: validEdges,
      });

      // 批量加载节点标签（异步，不阻塞渲染）
      const entityIds = validNodes.map(node => node.id);
      if (entityIds.length > 0) {
        api.governance.batchGetEntityTags(entityIds)
          .then((response) => {
            // 将标签分配到对应的节点
            const tagsMap = response.data.tags_map || {};
            const nodesWithTags = validNodes.map((node) => ({
              ...node,
              tags: tagsMap[node.id] || [],
            }));
            
            // 标签加载完成后更新图数据
            setGraphData({
              nodes: nodesWithTags,
              edges: validEdges,
            });
          })
          .catch((err) => {
            console.error('批量加载标签失败:', err);
            // 如果批量加载失败，为所有节点设置空标签数组
            const nodesWithEmptyTags = validNodes.map((node) => ({
              ...node,
              tags: [],
            }));
            setGraphData({
              nodes: nodesWithEmptyTags,
              edges: validEdges,
            });
          });
      }
    } catch (err: any) {
      setError(err.message || t('graphView.errorLoadingGraph'));
    } finally {
      setLoading(false);
    }
  };

  const handleNodeClick = async (node: GraphNode) => {
    setSelectedNode(node);
    setDrawerVisible(true);
    setLoadingNodeDetails(true);
    try {
      // 加载节点的标签
      const tagsRes = await api.governance.getEntityTags(node.id).catch(() => ({ data: { tags: [], count: 0 } }));
      setNodeTags(tagsRes.data.tags || []);
    } catch (err) {
      console.error('加载节点标签失败:', err);
      setNodeTags([]);
    } finally {
      setLoadingNodeDetails(false);
    }
  };

  const handleNodeHover = (_node: GraphNode | null) => {
    // 可以在这里添加悬停效果，比如显示工具提示
  };

  // 统计节点类型和关系类型
  const legendData = useMemo(() => {
    const nodeTypeCount: Record<string, number> = {};
    const edgeTypeCount: Record<string, number> = {};

    // 统计节点类型
    graphData.nodes.forEach((node) => {
      const type = node.type || 'unknown';
      nodeTypeCount[type] = (nodeTypeCount[type] || 0) + 1;
    });

    // 统计关系类型
    graphData.edges.forEach((edge) => {
      const type = edge.type || 'related_to';
      edgeTypeCount[type] = (edgeTypeCount[type] || 0) + 1;
    });

    return {
      nodeTypes: Object.entries(nodeTypeCount)
        .map(([type, count]) => ({ type, count }))
        .sort((a, b) => b.count - a.count),
      edgeTypes: Object.entries(edgeTypeCount)
        .map(([type, count]) => ({ type, count }))
        .sort((a, b) => b.count - a.count),
    };
  }, [graphData]);

  // 根据过滤条件过滤图数据
  const filteredGraphData = useMemo(() => {
    if (filteredNodeTypes.size === 0 && filteredEdgeTypes.size === 0) {
      return graphData;
    }

    let filteredNodes = graphData.nodes;
    let filteredEdges = graphData.edges;

    // 过滤节点类型
    if (filteredNodeTypes.size > 0) {
      filteredNodes = graphData.nodes.filter((node) => {
        const type = node.type || 'unknown';
        return filteredNodeTypes.has(type);
      });
      
      // 只保留与过滤节点相关的边
      const filteredNodeIds = new Set(filteredNodes.map((n) => String(n.id)));
      filteredEdges = filteredEdges.filter((edge) => {
        return filteredNodeIds.has(String(edge.source)) && filteredNodeIds.has(String(edge.target));
      });
    }

    // 过滤关系类型
    if (filteredEdgeTypes.size > 0) {
      filteredEdges = filteredEdges.filter((edge) => {
        const type = edge.type || 'related_to';
        return filteredEdgeTypes.has(type);
      });
      
      // 只保留与过滤边相关的节点
      const relatedNodeIds = new Set<string>();
      filteredEdges.forEach((edge) => {
        relatedNodeIds.add(String(edge.source));
        relatedNodeIds.add(String(edge.target));
      });
      filteredNodes = filteredNodes.filter((node) => {
        return relatedNodeIds.has(String(node.id));
      });
    }

    return {
      nodes: filteredNodes,
      edges: filteredEdges,
    };
  }, [graphData, filteredNodeTypes, filteredEdgeTypes]);

  // 处理节点类型点击
  const handleNodeTypeClick = (type: string) => {
    setFilteredNodeTypes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(type)) {
        newSet.delete(type);
      } else {
        newSet.add(type);
      }
      return newSet;
    });
    // 清除关系类型过滤（避免冲突）
    setFilteredEdgeTypes(new Set());
  };

  // 处理关系类型点击
  const handleEdgeTypeClick = (type: string) => {
    setFilteredEdgeTypes((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(type)) {
        newSet.delete(type);
      } else {
        newSet.add(type);
      }
      return newSet;
    });
    // 清除节点类型过滤（避免冲突）
    setFilteredNodeTypes(new Set());
  };

  // 清除所有过滤
  const clearFilters = () => {
    setFilteredNodeTypes(new Set());
    setFilteredEdgeTypes(new Set());
  };

  // 处理节点聚合
  const handleAggregate = (aggregated: GraphData) => {
    setAggregatedData(aggregated);
  };

  const handleResetAggregation = () => {
    setAggregatedData(null);
  };

  // 处理路径高亮
  const handleHighlightPaths = (paths: string[][]) => {
    setHighlightedPaths(paths);
  };

  const handleClearHighlight = () => {
    setHighlightedPaths([]);
  };

  // 获取当前显示的图数据
  const displayGraphData = aggregatedData || filteredGraphData;

  useEffect(() => {
    loadEntityTypes();
    loadSources();
    loadGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ height: 'calc(100vh - 112px)', display: 'flex', flexDirection: 'column' }}>
      {/* 紧凑的顶部工具栏 */}
      <Card
        size="small"
        style={{ 
          marginBottom: 8,
          flexShrink: 0
        }}
        styles={{
          body: {
            padding: '8px 12px'
          }
        }}
      >
        <Space wrap size="small" style={{ width: '100%' }}>
          <Input
            placeholder={t('graphView.entityId')}
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
            style={{ width: 180 }}
            size="small"
            allowClear
          />
          <Select
            placeholder={t('graphView.entityType')}
            value={entityType}
            onChange={setEntityType}
            style={{ width: 130 }}
            size="small"
            allowClear
            showSearch
            notFoundContent={entityTypes.length === 0 ? t('common.loading') : t('common.noData')}
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
          <Select
            placeholder={t('graphView.source')}
            value={source}
            onChange={setSource}
            style={{ width: 130 }}
            size="small"
            allowClear
            showSearch
            notFoundContent={sources.length === 0 ? t('common.loading') : t('common.noData')}
            filterOption={(input, option) =>
              (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
          >
            {sources.map((src) => (
              <Select.Option key={src} value={src} label={src}>
                {src}
              </Select.Option>
            ))}
          </Select>
          <Space size={4}>
            <span style={{ fontSize: '12px', color: '#666' }}>{t('graphView.depth')}:</span>
            <Slider
              min={1}
              max={5}
              value={depth}
              onChange={setDepth}
              style={{ width: 80 }}
              tooltip={{ formatter: (value) => value?.toString() }}
            />
            <span style={{ fontSize: '12px', color: '#666', minWidth: '20px' }}>{depth}</span>
          </Space>
          <Select
            value={layoutType}
            onChange={setLayoutType}
            style={{ width: 100 }}
            size="small"
          >
            <Select.Option value="force">{t('graphView.forceDirected')}</Select.Option>
            <Select.Option value="hierarchy">{t('graphView.hierarchy')}</Select.Option>
            <Select.Option value="temporal">{t('graphView.temporal')}</Select.Option>
          </Select>
          <Button icon={<SearchOutlined />} onClick={loadGraph} loading={loading} size="small" type="primary">
            {t('graphView.loadGraph')}
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadGraph} size="small">
            {t('common.refresh')}
          </Button>
          <Button onClick={() => setShowAnalysis(!showAnalysis)} size="small">
            {showAnalysis ? t('graphView.hideAnalysis') : t('graphView.showAnalysis')}
          </Button>
          <Tooltip title={t('graphView.maxNodes')}>
            <Button 
              icon={<SettingOutlined />} 
              onClick={() => setShowLimitConfig(!showLimitConfig)} 
              size="small"
              type={showLimitConfig ? 'primary' : 'default'}
            >
              {t('graphView.filter')}
            </Button>
          </Tooltip>
        </Space>
        {/* 数据限制配置面板 */}
        {showLimitConfig && (
          <div style={{ 
            marginTop: 8, 
            padding: '8px 12px', 
            background: '#f5f5f5', 
            borderRadius: '4px',
            border: '1px solid #d9d9d9'
          }}>
            <Space size="middle" wrap>
              <Space size={4}>
                <span style={{ fontSize: '12px', color: '#666', minWidth: '80px' }}>{t('graphView.maxNodes')}:</span>
                <InputNumber
                  min={100}
                  max={10000}
                  step={100}
                  value={maxNodes}
                  onChange={(value) => value && setMaxNodes(value)}
                  size="small"
                  style={{ width: 100 }}
                />
              </Space>
              <Space size={4}>
                <span style={{ fontSize: '12px', color: '#666', minWidth: '80px' }}>{t('graphView.maxEdges')}:</span>
                <InputNumber
                  min={200}
                  max={20000}
                  step={200}
                  value={maxEdges}
                  onChange={(value) => value && setMaxEdges(value)}
                  size="small"
                  style={{ width: 100 }}
                />
              </Space>
              <Button 
                size="small" 
                type="link" 
                onClick={() => {
                  setMaxNodes(graphConfig.maxNodes);
                  setMaxEdges(graphConfig.maxEdges);
                  setShowNodeLabels(false);
                  setShowEdgeLabels(false);
                }}
              >
                {t('common.reset')}
              </Button>
            </Space>
            <Divider style={{ margin: '8px 0' }} />
            <Space size="middle" wrap>
              <Space size={4}>
                <span style={{ fontSize: '12px', color: '#666', minWidth: '100px' }}>{t('graphView.showNodeLabels')}:</span>
                <Switch
                  checked={showNodeLabels}
                  onChange={setShowNodeLabels}
                  size="small"
                />
                <span style={{ fontSize: '11px', color: '#999', marginLeft: 4 }}>
                  {showNodeLabels ? t('common.enabled') : t('common.disabled')}
                </span>
              </Space>
              <Space size={4}>
                <span style={{ fontSize: '12px', color: '#666', minWidth: '100px' }}>{t('graphView.showEdgeLabels')}:</span>
                <Switch
                  checked={showEdgeLabels}
                  onChange={setShowEdgeLabels}
                  size="small"
                />
                <span style={{ fontSize: '11px', color: '#999', marginLeft: 4 }}>
                  {showEdgeLabels ? t('common.enabled') : t('common.disabled')}
                </span>
              </Space>
            </Space>
            <div style={{ marginTop: 8 }}>
              <span style={{ fontSize: '11px', color: '#999' }}>
                {t('common.current')}: {graphData.nodes.length} {t('graphView.nodeTypes')} / {graphData.edges.length} {t('graphView.edgeTypes')}
                {graphData.nodes.length > maxNodes && (
                  <span style={{ color: '#ff4d4f', marginLeft: 4 }}>
                    ({t('graphView.nodeTypes')} {t('common.limited')}: {maxNodes})
                  </span>
                )}
                {graphData.edges.length > maxEdges && (
                  <span style={{ color: '#ff4d4f', marginLeft: 4 }}>
                    ({t('graphView.edgeTypes')} {t('common.limited')}: {maxEdges})
                  </span>
                )}
              </span>
            </div>
          </div>
        )}
      </Card>

      {/* 主内容区域 */}
      <Card
        style={{ 
          flex: 1,
          display: 'flex', 
          flexDirection: 'column',
          overflow: 'hidden',
          minHeight: 0
        }}
        styles={{ 
          body: {
            flex: 1, 
            display: 'flex', 
            flexDirection: 'column',
            overflow: 'hidden',
            padding: '8px'
          }
        }}
      >
        {error && <Alert message={t('common.error')} description={error} type="error" style={{ marginBottom: 8 }} size="small" />}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '50px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Spin size="large" />
          </div>
        ) : (
          <div style={{ flex: 1, width: '100%', overflow: 'hidden', minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            {/* 紧凑的交互工具栏和图例 */}
            <div style={{ marginBottom: 8, flexShrink: 0 }}>
              {/* 工具栏 - 一行排列 */}
              <div style={{ 
                display: 'flex', 
                flexWrap: 'nowrap', 
                alignItems: 'center', 
                gap: '8px',
                marginBottom: 8,
                overflowX: 'auto',
                overflowY: 'hidden'
              }}>
                <NodeAggregation
                  data={displayGraphData}
                  onAggregate={handleAggregate}
                  onReset={handleResetAggregation}
                />
                <SubgraphExtraction data={displayGraphData} />
                <PathHighlight
                  data={displayGraphData}
                  onHighlight={handleHighlightPaths}
                  onClear={handleClearHighlight}
                />
              </div>
              {/* 紧凑的图例 - 默认折叠 */}
              {(legendData.nodeTypes.length > 0 || legendData.edgeTypes.length > 0) && (
                <Card
                  size="small"
                  style={{ marginBottom: 0 }}
                  styles={{
                    body: {
                      padding: legendCollapsed ? '0' : '8px',
                      display: legendCollapsed ? 'none' : 'block',
                      transition: 'all 0.3s ease',
                      maxHeight: legendCollapsed ? '0' : '200px',
                      overflow: 'auto',
                    }
                  }}
                  title={
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px' }}>
                      <span>{t('graphView.legend')} ({graphData.nodes.length}{t('graphView.nodeTypes')}/{graphData.edges.length}{t('graphView.edgeTypes')})</span>
                      <Space size="small">
                        {(filteredNodeTypes.size > 0 || filteredEdgeTypes.size > 0) && (
                          <Button size="small" onClick={clearFilters} style={{ fontSize: '12px', height: '24px', padding: '0 8px' }}>
                            {t('graphView.clearFilter')}
                          </Button>
                        )}
                        <Button
                          type="text"
                          size="small"
                          icon={legendCollapsed ? <DownOutlined /> : <UpOutlined />}
                          onClick={() => setLegendCollapsed(!legendCollapsed)}
                          style={{ fontSize: '12px', height: '24px', padding: '0 4px' }}
                        />
                      </Space>
                    </div>
                  }
                >
                  {!legendCollapsed && (
                    <Space direction="vertical" style={{ width: '100%' }} size={4}>
                      {/* 节点类型图例 - 紧凑显示 */}
                      {legendData.nodeTypes.length > 0 && (
                        <div>
                          <div style={{ fontWeight: 'bold', marginBottom: 4, fontSize: '12px', color: '#666' }}>
                            {t('graphView.nodeTypes')}
                            {filteredNodeTypes.size > 0 && (
                              <span style={{ color: '#1890ff', marginLeft: 4, fontSize: '11px' }}>
                                ({t('graphView.filter')}: {filteredGraphData.nodes.length})
                              </span>
                            )}
                          </div>
                          <Space wrap size={4}>
                            {legendData.nodeTypes.map(({ type, count }) => {
                              const nodeTypeColors: Record<string, string> = {
                                file: '#1890ff',
                                directory: '#52c41a',
                                function: '#fa8c16',
                                class: '#eb2f96',
                                table: '#722ed1',
                                column: '#13c2c2',
                                database: '#2f54eb',
                                schema: '#faad14',
                                package: '#f5222d',
                                module: '#a0d911',
                                unknown: '#8c8c8c',
                              };
                              const color = nodeTypeColors[type] || nodeTypeColors.unknown;
                              const isFiltered = filteredNodeTypes.has(type);
                              return (
                                <Tag
                                  key={type}
                                  color={color}
                                  onClick={() => handleNodeTypeClick(type)}
                                  style={{
                                    marginBottom: 2,
                                    padding: '2px 6px',
                                    borderRadius: '3px',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    gap: '3px',
                                    cursor: 'pointer',
                                    opacity: isFiltered ? 1 : 0.6,
                                    border: isFiltered ? '2px solid #1890ff' : '1px solid transparent',
                                    fontSize: '11px',
                                    lineHeight: '18px',
                                    transition: 'all 0.2s',
                                  }}
                                >
                                  <span
                                    style={{
                                      display: 'inline-block',
                                      width: '8px',
                                      height: '8px',
                                      borderRadius: '50%',
                                      backgroundColor: color,
                                      border: '1px solid #fff',
                                    }}
                                  />
                                  <span>{type}</span>
                                  <span style={{ opacity: 0.8 }}>({count})</span>
                                </Tag>
                              );
                            })}
                          </Space>
                        </div>
                      )}
                      
                      {/* 关系类型图例 - 紧凑显示 */}
                      {legendData.edgeTypes.length > 0 && (
                        <div>
                          <Divider style={{ margin: '6px 0' }} />
                          <div style={{ fontWeight: 'bold', marginBottom: 4, fontSize: '12px', color: '#666' }}>
                            {t('graphView.edgeTypes')}
                            {filteredEdgeTypes.size > 0 && (
                              <span style={{ color: '#1890ff', marginLeft: 4, fontSize: '11px' }}>
                                ({t('graphView.filter')}: {filteredGraphData.edges.length})
                              </span>
                            )}
                          </div>
                          <Space wrap size={4}>
                            {legendData.edgeTypes.map(({ type, count }) => {
                              const isFiltered = filteredEdgeTypes.has(type);
                              return (
                                <Tag
                                  key={type}
                                  onClick={() => handleEdgeTypeClick(type)}
                                  style={{
                                    marginBottom: 2,
                                    padding: '2px 6px',
                                    borderRadius: '3px',
                                    backgroundColor: isFiltered ? '#e6f7ff' : '#f0f0f0',
                                    border: isFiltered ? '2px solid #1890ff' : '1px solid #d9d9d9',
                                    cursor: 'pointer',
                                    opacity: isFiltered ? 1 : 0.7,
                                    fontSize: '11px',
                                    lineHeight: '18px',
                                    transition: 'all 0.2s',
                                  }}
                                >
                                  <span>{type}</span>
                                  <span style={{ opacity: 0.8, marginLeft: 2 }}>({count})</span>
                                </Tag>
                              );
                            })}
                          </Space>
                        </div>
                      )}
                    </Space>
                  )}
                </Card>
              )}
            </div>
            
            {/* 图可视化和分析 - 最大化图显示区域 */}
            <div style={{ display: 'flex', flex: 1, gap: 8, minHeight: 0 }}>
              <div style={{ flex: showAnalysis ? 3 : 1, overflow: 'hidden', minHeight: 0, position: 'relative' }}>
                {layoutType === 'force' && (
                  <ForceDirectedGraph
                    key={`graph-${displayGraphData.nodes.length}-${displayGraphData.edges.length}-${maxNodes}-${maxEdges}-${showNodeLabels}-${showEdgeLabels}`}
                    data={displayGraphData}
                    maxNodes={maxNodes}
                    maxEdges={maxEdges}
                    showNodeLabels={showNodeLabels}
                    showEdgeLabels={showEdgeLabels}
                    onNodeClick={handleNodeClick}
                    onNodeHover={handleNodeHover}
                  />
                )}
                {layoutType === 'hierarchy' && (
                  <HierarchyLayout
                    key={`hierarchy-${displayGraphData.nodes.length}-${displayGraphData.edges.length}-${maxNodes}-${maxEdges}`}
                    data={displayGraphData}
                    maxNodes={maxNodes}
                    maxEdges={maxEdges}
                    onNodeClick={handleNodeClick}
                    onNodeHover={handleNodeHover}
                  />
                )}
                {layoutType === 'temporal' && (
                  <TemporalLayout
                    key={`temporal-${displayGraphData.nodes.length}-${displayGraphData.edges.length}-${maxNodes}-${maxEdges}`}
                    data={displayGraphData}
                    maxNodes={maxNodes}
                    maxEdges={maxEdges}
                    onNodeClick={handleNodeClick}
                    onNodeHover={handleNodeHover}
                  />
                )}
              </div>
              {showAnalysis && (
                <div style={{ width: 280, overflow: 'auto', flexShrink: 0 }}>
                  <Tabs
                    size="small"
                    items={[
                      {
                        key: 'centrality',
                        label: t('graphView.centrality'),
                        children: (
                          <CentralityAnalysis
                            data={displayGraphData}
                            onNodeSelect={(nodeId) => {
                              const node = displayGraphData.nodes.find((n) => n.id === nodeId);
                              if (node) handleNodeClick(node);
                            }}
                          />
                        ),
                      },
                      {
                        key: 'community',
                        label: t('graphView.community'),
                        children: (
                          <CommunityDetection
                            data={displayGraphData}
                            onCommunitySelect={(communityId) => {
                              const communities = detectCommunities(displayGraphData);
                              const community = communities[communityId];
                              if (community) {
                                const communityNodeIds = new Set(community.nodes.map((n) => n.id));
                              }
                            }}
                          />
                        ),
                      },
                    ]}
                  />
                </div>
              )}
            </div>
          </div>
        )}
      </Card>
      <Drawer
        title={t('graphView.nodeDetails')}
        placement="right"
        onClose={() => {
          setDrawerVisible(false);
          setNodeTags([]);
        }}
        open={drawerVisible}
        size={500}
      >
        {selectedNode && (
          <Spin spinning={loadingNodeDetails}>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label={t('common.name')}>{selectedNode.label}</Descriptions.Item>
              <Descriptions.Item label={t('common.id')}>{selectedNode.id}</Descriptions.Item>
              <Descriptions.Item label={t('common.type')}>
                <Tag color="blue">{selectedNode.type}</Tag>
              </Descriptions.Item>
              {selectedNode.description && (
                <Descriptions.Item label={t('common.description')}>{selectedNode.description}</Descriptions.Item>
              )}
              <Descriptions.Item label={t('graphView.tags')}>
                {nodeTags.length > 0 ? (
                  <Space wrap>
                    {nodeTags.map((tag: any) => (
                      <Tag
                        key={tag.id || tag.tag_id}
                        color={tag.color || '#1890ff'}
                        style={{ margin: 0 }}
                      >
                        {tag.name || tag.tag_name}
                      </Tag>
                    ))}
                  </Space>
                ) : (
                  <span style={{ color: '#999' }}>{t('graphView.noTags')}</span>
                )}
              </Descriptions.Item>
            </Descriptions>
            {Object.keys(selectedNode).length > 0 && (
              <div style={{ marginTop: 16 }}>
                <h4>{t('graphView.nodeInfo')}:</h4>
                <pre style={{ background: '#f5f5f5', padding: '10px', borderRadius: '4px', overflow: 'auto', maxHeight: '300px' }}>
                  {JSON.stringify(selectedNode, null, 2)}
                </pre>
              </div>
            )}
          </Spin>
        )}
      </Drawer>
    </div>
  );
}

