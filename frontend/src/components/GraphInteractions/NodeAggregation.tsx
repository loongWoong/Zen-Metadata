/**
 * 节点聚合组件
 * 按类型、标签、系统自动聚合节点
 */
import { useMemo } from 'react';
import { Button, Space, Tag, Select } from 'antd';
import { ApartmentOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { GraphData, GraphNode } from '../../types';

interface NodeAggregationProps {
  data: GraphData;
  onAggregate?: (aggregatedData: GraphData) => void;
  onReset?: () => void;
}

export default function NodeAggregation({ data, onAggregate, onReset }: NodeAggregationProps) {
  const { t } = useTranslation();
  const aggregationOptions = useMemo(() => {
    const types = new Set<string>();
    const sources = new Set<string>();
    const tags = new Set<string>();

    data.nodes.forEach((node) => {
      types.add(node.type || 'unknown');
      if (node.source) sources.add(node.source);
      if (node.tags && Array.isArray(node.tags)) {
        node.tags.forEach((tag: any) => {
          tags.add(tag.name || tag.tag_name || tag);
        });
      }
    });

    return {
      types: Array.from(types),
      sources: Array.from(sources),
      tags: Array.from(tags),
    };
  }, [data]);

  const handleAggregateByType = () => {
    const aggregated = aggregateByType(data);
    onAggregate?.(aggregated);
  };

  const handleAggregateBySource = () => {
    const aggregated = aggregateBySource(data);
    onAggregate?.(aggregated);
  };

  const handleReset = () => {
    onReset?.();
  };

  return (
    <Space size="small" style={{ flexShrink: 0 }}>
      <Button size="small" icon={<ApartmentOutlined />} onClick={handleAggregateByType}>
        {t('components.nodeAggregation.aggregateByType')}
      </Button>
      <Button size="small" icon={<ApartmentOutlined />} onClick={handleAggregateBySource}>
        {t('components.nodeAggregation.aggregateBySource')}
      </Button>
      <Button size="small" onClick={handleReset}>{t('components.nodeAggregation.reset')}</Button>
    </Space>
  );
}

function aggregateByType(data: GraphData): GraphData {
  const typeGroups = new Map<string, GraphNode[]>();

  data.nodes.forEach((node) => {
    const type = node.type || 'unknown';
    if (!typeGroups.has(type)) {
      typeGroups.set(type, []);
    }
    typeGroups.get(type)!.push(node);
  });

  const aggregatedNodes: GraphNode[] = [];
  const aggregatedEdges = data.edges;

  typeGroups.forEach((nodes, type) => {
    if (nodes.length > 1) {
      // 创建聚合节点
      aggregatedNodes.push({
        id: `aggregate_${type}`,
        label: `${type} (${nodes.length})`,
        type: 'aggregate',
        properties: {
          original_type: type,
          node_count: nodes.length,
        },
        source: 'aggregation',
      });
    } else {
      aggregatedNodes.push(...nodes);
    }
  });

  return {
    nodes: aggregatedNodes,
    edges: aggregatedEdges,
  };
}

function aggregateBySource(data: GraphData): GraphData {
  const sourceGroups = new Map<string, GraphNode[]>();

  data.nodes.forEach((node) => {
    const source = node.source || 'unknown';
    if (!sourceGroups.has(source)) {
      sourceGroups.set(source, []);
    }
    sourceGroups.get(source)!.push(node);
  });

  const aggregatedNodes: GraphNode[] = [];
  const aggregatedEdges = data.edges;

  sourceGroups.forEach((nodes, source) => {
    if (nodes.length > 1) {
      aggregatedNodes.push({
        id: `aggregate_${source}`,
        label: `${source} (${nodes.length})`,
        type: 'aggregate',
        properties: {
          original_source: source,
          node_count: nodes.length,
        },
        source: 'aggregation',
      });
    } else {
      aggregatedNodes.push(...nodes);
    }
  });

  return {
    nodes: aggregatedNodes,
    edges: aggregatedEdges,
  };
}


