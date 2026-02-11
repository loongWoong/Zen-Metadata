import { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Space,
  Select,
  message,
  Spin,
  Tag,
  Tooltip,
} from 'antd';
import {
  ReloadOutlined,
  DatabaseOutlined,
  LinkOutlined,
  CodeOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import api from '../../services/api';
import ForceDirectedGraph from '../../components/ForceDirectedGraph/index';
import type { GraphNode, GraphEdge, GraphData } from '../../types';

export default function MetamodelGraph() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [graphData, setGraphData] = useState<GraphData>({
    nodes: [],
    edges: [],
  });
  const [statistics, setStatistics] = useState({
    entityCount: 0,
    relationshipCount: 0,
    collectorCount: 0,
  });
  // 版本选择器相关状态
  const [entityModels, setEntityModels] = useState<any[]>([]);
  const [relationshipModels, setRelationshipModels] = useState<any[]>([]);
  const [collectors, setCollectors] = useState<any[]>([]);
  const [versionMap, setVersionMap] = useState<Map<string, string[]>>(new Map()); // 实体类型 -> 版本列表
  const [selectedVersions, setSelectedVersions] = useState<Map<string, string>>(new Map()); // 实体类型 -> 选择的版本

  useEffect(() => {
    loadAllData();
  }, []);

  // 加载所有数据（不进行版本过滤）
  const loadAllData = async () => {
    try {
      setLoading(true);
      
      // 获取所有实体元模型、关系元模型和采集器
      const [entityResponse, relationshipResponse, collectorResponse] = await Promise.all([
        api.metamodel.listEntityModels(),
        api.metamodel.listRelationshipModels(),
        api.metamodel.listCollectorTypes(),
      ]);

      const allEntityModels = entityResponse.data.models || [];
      const allRelationshipModels = relationshipResponse.data.models || [];
      const allCollectors = collectorResponse.data.collector_types || [];

      setEntityModels(allEntityModels);
      setRelationshipModels(allRelationshipModels);
      setCollectors(allCollectors);

      // 分析每个实体类型的版本
      const versionMapTemp = new Map<string, string[]>();
      allEntityModels.forEach((model: any) => {
        const entityType = model.type;
        if (!versionMapTemp.has(entityType)) {
          versionMapTemp.set(entityType, []);
        }
        versionMapTemp.get(entityType)!.push(model.version);
      });

      setVersionMap(versionMapTemp);

      // 为每个实体类型选择最新版本（或第一个版本）
      const selectedVersionsTemp = new Map<string, string>();
      versionMapTemp.forEach((versions, entityType) => {
        if (versions.length > 0) {
          // 选择最新版本（按版本号排序，取最后一个）
          const sortedVersions = [...versions].sort((a, b) => {
            // 简单的版本比较：v1 < v2 < v10
            const aNum = parseInt(a.replace('v', '')) || 0;
            const bNum = parseInt(b.replace('v', '')) || 0;
            return aNum - bNum;
          });
          selectedVersionsTemp.set(entityType, sortedVersions[sortedVersions.length - 1]);
        }
      });
      setSelectedVersions(selectedVersionsTemp);

      // 加载图谱数据
      loadGraphData(allEntityModels, allRelationshipModels, allCollectors, selectedVersionsTemp);
    } catch (err: any) {
      message.error(t('metamodelGraph.loadFailed') + ': ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 根据选择的版本加载图谱数据
  const loadGraphData = (
    allEntityModels: any[] = entityModels,
    allRelationshipModels: any[] = relationshipModels,
    allCollectors: any[] = collectors,
    versions: Map<string, string> = selectedVersions
  ) => {
    try {
      // 根据选择的版本过滤实体元模型
      const filteredEntityModels = allEntityModels.filter((model: any) => {
        const selectedVersion = versions.get(model.type);
        return selectedVersion === model.version;
      });

      // 构建节点（只包含实体元模型和采集器，关系元模型不作为节点）
      const nodes: GraphNode[] = [];
      const nodeMap = new Map<string, GraphNode>();

      // 添加实体元模型节点（每个类型只添加一个版本）
      filteredEntityModels.forEach((model: any) => {
        // 使用类型作为节点ID，而不是包含版本，避免重复
        const nodeId = `entity:${model.type}`;
        const node: GraphNode = {
          id: nodeId,
          label: `${model.label} (${model.type}@${model.version})`,
          type: 'entity',
          properties: model,
        };
        // 如果节点已存在，更新为最新版本
        if (!nodeMap.has(nodeId)) {
          nodes.push(node);
          nodeMap.set(nodeId, node);
        } else {
          // 更新现有节点为当前版本
          const existingNode = nodeMap.get(nodeId)!;
          existingNode.label = `${model.label} (${model.type}@${model.version})`;
          existingNode.properties = model;
        }
      });

      // 添加采集器节点
      allCollectors.forEach((collector: any) => {
        const nodeId = `collector:${collector.collector_type}`;
        const node: GraphNode = {
          id: nodeId,
          label: `${collector.label || collector.collector_type}`,
          type: 'collector',
          properties: collector,
        };
        nodes.push(node);
        nodeMap.set(nodeId, node);
      });

      // 构建边（关系元模型作为连线展示）
      const edges: GraphEdge[] = [];

      // 连接采集器和实体元模型
      allCollectors.forEach((collector: any) => {
        const collectorNodeId = `collector:${collector.collector_type}`;
        // 使用类型而不是完整版本号
        const entityNodeId = `entity:${collector.entity_type}`;
        
        if (nodeMap.has(entityNodeId)) {
          edges.push({
            source: collectorNodeId,
            target: entityNodeId,
            label: '采集',
            type: 'collects',
          });
        }
      });

      // 关系元模型作为连线：根据source_types和target_types在实体之间创建连线
      // 使用Set来避免重复的边
      const edgeSet = new Set<string>();
      
      // 过滤关系元模型：只使用与选择的实体版本匹配的关系元模型
      // 关系元模型可能有多个版本，我们需要选择与实体版本匹配的版本
      const filteredRelationshipModels = allRelationshipModels.filter((relModel: any) => {
        // 检查关系元模型的 source_types 和 target_types 是否与选择的实体版本匹配
        const sourceTypes = relModel.source_types || [];
        const targetTypes = relModel.target_types || [];
        
        // 如果关系元模型没有指定类型，则包含所有版本
        if (sourceTypes.length === 0 && targetTypes.length === 0) {
          return true;
        }
        
        // 检查是否至少有一个源类型或目标类型在过滤后的实体模型中存在
        const hasMatchingSource = sourceTypes.length === 0 || 
          sourceTypes.some((type: string) => filteredEntityModels.some((e: any) => e.type === type));
        const hasMatchingTarget = targetTypes.length === 0 || 
          targetTypes.some((type: string) => filteredEntityModels.some((e: any) => e.type === type));
        
        return hasMatchingSource && hasMatchingTarget;
      });
      
      filteredRelationshipModels.forEach((relModel: any) => {
        const sourceTypes = relModel.source_types || [];
        const targetTypes = relModel.target_types || [];
        
        // 如果source_types和target_types都为空，表示该关系可以连接所有实体类型
        // 这种情况下，我们跳过，因为无法确定具体的连接
        if (sourceTypes.length === 0 && targetTypes.length === 0) {
          return;
        }
        
        // 如果source_types为空，表示可以从任何实体类型连接
        // 如果target_types为空，表示可以连接到任何实体类型
        const effectiveSourceTypes = sourceTypes.length > 0 ? sourceTypes : filteredEntityModels.map((e: any) => e.type);
        const effectiveTargetTypes = targetTypes.length > 0 ? targetTypes : filteredEntityModels.map((e: any) => e.type);
        
        // 为每个源类型和目标类型的组合创建连线
        effectiveSourceTypes.forEach((sourceType: string) => {
          effectiveTargetTypes.forEach((targetType: string) => {
            // 跳过自己连接自己的情况（除非关系类型允许）
            if (sourceType === targetType && sourceTypes.length > 0 && targetTypes.length > 0) {
              return;
            }
            
            // 查找对应版本的实体
            const sourceVersion = versions.get(sourceType);
            const targetVersion = versions.get(targetType);
            const sourceEntity = filteredEntityModels.find((e: any) => e.type === sourceType && e.version === sourceVersion);
            const targetEntity = filteredEntityModels.find((e: any) => e.type === targetType && e.version === targetVersion);
            
            if (sourceEntity && targetEntity) {
              // 使用类型而不是完整版本号
              const sourceNodeId = `entity:${sourceEntity.type}`;
              const targetNodeId = `entity:${targetEntity.type}`;
              
              if (nodeMap.has(sourceNodeId) && nodeMap.has(targetNodeId)) {
                // 使用组合键避免重复边（同一对节点可以有多个关系类型）
                const edgeKey = `${sourceNodeId}-${targetNodeId}-${relModel.type}`;
                if (!edgeSet.has(edgeKey)) {
                  edgeSet.add(edgeKey);
                  edges.push({
                    source: sourceNodeId,
                    target: targetNodeId,
                    label: relModel.label || relModel.type,
                    type: relModel.type,
                  });
                }
              }
            }
          });
        });
      });

      // 连接实体元模型之间的关系（通过relationships配置）
      // 这个逻辑保留，用于展示实体元模型中定义的关系
      filteredEntityModels.forEach((entityModel: any) => {
        const entityNodeId = `entity:${entityModel.type}`;
        (entityModel.relationships || []).forEach((rel: any) => {
          const relType = rel.type || rel.relationship_type;
          const targetType = rel.target_type || rel.targetType;
          
          if (relType && targetType) {
            // 查找目标实体类型（使用选择的版本）
            const targetVersion = versions.get(targetType);
            const targetEntity = filteredEntityModels.find((e: any) => e.type === targetType && e.version === targetVersion);
            if (targetEntity) {
              const targetNodeId = `entity:${targetEntity.type}`;
              if (nodeMap.has(targetNodeId)) {
                // 查找对应的关系元模型
                const matchingRelModel = allRelationshipModels.find((r: any) => r.type === relType);
                const edgeLabel = matchingRelModel ? (matchingRelModel.label || relType) : relType;
                
                // 检查是否已存在相同的边
                const edgeKey = `${entityNodeId}-${targetNodeId}-${relType}`;
                if (!edgeSet.has(edgeKey)) {
                  edgeSet.add(edgeKey);
                  edges.push({
                    source: entityNodeId,
                    target: targetNodeId,
                    label: edgeLabel,
                    type: relType,
                  });
                }
              }
            }
          }
        });
      });

      // 使用稳定的数据结构，避免无限循环
      const newGraphData = { nodes, edges };
      setGraphData(newGraphData);
      setStatistics({
        entityCount: filteredEntityModels.length,
        relationshipCount: allRelationshipModels.length,
        collectorCount: allCollectors.length,
      });
    } catch (err: any) {
      message.error(t('metamodelGraph.loadFailed') + ': ' + err.message);
    }
  };

  // 处理版本选择变化
  const handleVersionChange = (entityType: string, version: string) => {
    const newSelectedVersions = new Map(selectedVersions);
    newSelectedVersions.set(entityType, version);
    setSelectedVersions(newSelectedVersions);
    loadGraphData(entityModels, relationshipModels, collectors, newSelectedVersions);
  };

  const handleNodeClick = (node: GraphNode) => {
    console.log('点击节点:', node);
    // 可以在这里显示节点详情
  };

  const handleNodeHover = (node: GraphNode | null) => {
    // 可以在这里显示节点悬停信息
  };

  return (
    <div style={{ 
      height: 'calc(100vh - 64px - 48px - 48px)', 
      maxHeight: 'calc(100vh - 64px - 48px - 48px)',
      display: 'flex', 
      flexDirection: 'column', 
      overflow: 'hidden',
      boxSizing: 'border-box'
    }}>
      <Space style={{ marginBottom: 16, flexShrink: 0 }}>
        <h1 style={{ margin: 0 }}>{t('metamodelGraph.title')}</h1>
        <Button icon={<ReloadOutlined />} onClick={loadAllData} loading={loading}>
          {t('common.refresh')}
        </Button>
      </Space>

      {/* 统计信息 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16, flexShrink: 0 }}>
        <Col xs={24} sm={8}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <DatabaseOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('metamodelGraph.entityModels')}</span>
              </div>
              <span style={{ fontSize: 20, fontWeight: 600 }}>{statistics.entityCount}</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <LinkOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('metamodelGraph.relationshipModels')}</span>
              </div>
              <span style={{ fontSize: 20, fontWeight: 600 }}>{statistics.relationshipCount}</span>
            </div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card bodyStyle={{ padding: '12px 16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CodeOutlined style={{ fontSize: 18, color: '#1890ff' }} />
                <span style={{ fontSize: 14, color: 'rgba(0,0,0,0.45)' }}>{t('metamodelGraph.collectors')}</span>
              </div>
              <span style={{ fontSize: 20, fontWeight: 600 }}>{statistics.collectorCount}</span>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 图谱可视化 */}
      <Card 
        style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}
        bodyStyle={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', padding: 0, overflow: 'hidden' }}
      >
        {/* 图例和版本选择器 - 浮动在左上角 */}
        <div style={{ 
          position: 'absolute', 
          top: 16, 
          left: 16, 
          zIndex: 10,
          background: 'rgba(255, 255, 255, 0.95)',
          padding: '12px',
          borderRadius: 6,
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          maxWidth: '400px'
        }}>
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            {/* 图例 */}
            <Space size={[8, 8]} wrap>
              <span style={{ fontSize: 12, color: 'rgba(0,0,0,0.65)', fontWeight: 500 }}>{t('graphView.legend')}:</span>
              <Tag color="#1890ff" style={{ margin: 0 }}>
                <DatabaseOutlined /> {t('metamodelGraph.entityModels')}
              </Tag>
              <Tag color="#fa8c16" style={{ margin: 0 }}>
                <CodeOutlined /> {t('metamodelGraph.collectors')}
              </Tag>
              <Tag color="#52c41a" style={{ margin: 0 }}>
                <LinkOutlined /> {t('metamodelGraph.relationshipModels')}
              </Tag>
            </Space>
            
            {/* 版本选择器 - 仅当存在多个版本的实体类型时显示 */}
            {Array.from(versionMap.entries()).some(([_, versions]) => versions.length > 1) && (
              <div style={{ 
                borderTop: '1px solid rgba(0,0,0,0.1)', 
                paddingTop: 12,
                display: 'flex',
                flexDirection: 'column',
                gap: 8
              }}>
                <div style={{ fontSize: 12, color: 'rgba(0,0,0,0.65)', fontWeight: 500 }}>
                  {t('metamodelGraph.versionSelector')}
                </div>
                <Space direction="vertical" size={8} style={{ width: '100%' }}>
                  {Array.from(versionMap.entries())
                    .filter(([_, versions]) => versions.length > 1)
                    .map(([entityType, versions]) => (
                      <div key={entityType} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 12, minWidth: 80, color: 'rgba(0,0,0,0.65)' }}>{entityType}:</span>
                        <Select
                          value={selectedVersions.get(entityType) || versions[0]}
                          onChange={(value) => handleVersionChange(entityType, value)}
                          style={{ flex: 1 }}
                          size="small"
                        >
                          {versions.map((version) => (
                            <Select.Option key={version} value={version}>
                              {version}
                            </Select.Option>
                          ))}
                        </Select>
                      </div>
                    ))}
                </Space>
              </div>
            )}
          </Space>
        </div>
        <Spin spinning={loading} style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
            {graphData.nodes.length > 0 ? (
              <ForceDirectedGraph
                key={`graph-${graphData.nodes.length}-${graphData.edges.length}`}
                data={graphData}
                onNodeClick={handleNodeClick}
                onNodeHover={handleNodeHover}
              />
            ) : (
              <div style={{ textAlign: 'center', padding: '100px 0' }}>
                <ApartmentOutlined style={{ fontSize: 64, color: '#d9d9d9' }} />
                <p style={{ marginTop: 16, color: '#8c8c8c' }}>{t('metamodelGraph.noData')}</p>
              </div>
            )}
          </div>
        </Spin>
      </Card>
    </div>
  );
}

