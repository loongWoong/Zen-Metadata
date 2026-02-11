/**
 * 社区检测组件
 * 使用颜色区分逻辑子系统
 */
import { useMemo } from 'react';
import { Card, Tag, Space } from 'antd';
import type { GraphData } from '../../types';

interface CommunityDetectionProps {
  data: GraphData;
  onCommunitySelect?: (communityId: number) => void;
}

export default function CommunityDetection({ data, onCommunitySelect }: CommunityDetectionProps) {
  const communities = useMemo(() => {
    return detectCommunities(data);
  }, [data]);

  const colors = [
    '#1890ff',
    '#52c41a',
    '#fa8c16',
    '#eb2f96',
    '#722ed1',
    '#13c2c2',
    '#2f54eb',
    '#faad14',
    '#f5222d',
    '#a0d911',
  ];

  return (
    <Card title="社区检测" size="small">
      <Space direction="vertical" style={{ width: '100%' }} size="middle">
        {communities.map((community, index) => (
          <div key={index}>
            <Tag
              color={colors[index % colors.length]}
              style={{ cursor: 'pointer', marginBottom: 8 }}
              onClick={() => onCommunitySelect?.(index)}
            >
              社区 {index + 1} ({community.nodes.length} 个节点)
            </Tag>
            <div style={{ marginLeft: 8, fontSize: '12px', color: '#666' }}>
              {community.nodes.slice(0, 5).map((node) => node.label || node.id).join(', ')}
              {community.nodes.length > 5 && '...'}
            </div>
          </div>
        ))}
      </Space>
    </Card>
  );
}

export function detectCommunities(data: GraphData): Array<{ nodes: any[]; edges: any[] }> {
  // 使用简单的标签传播算法
  const nodes = data.nodes;
  const edges = data.edges;

  // 初始化标签
  const labels = new Map<string, number>();
  nodes.forEach((node, index) => {
    labels.set(node.id, index);
  });

  // 构建邻接表
  const adjacencyList = new Map<string, Set<string>>();
  nodes.forEach((node) => {
    adjacencyList.set(node.id, new Set());
  });

  edges.forEach((edge) => {
    adjacencyList.get(edge.source)?.add(edge.target);
    adjacencyList.get(edge.target)?.add(edge.source);
  });

  // 迭代更新标签
  let changed = true;
  let iterations = 0;
  const maxIterations = 10;

  while (changed && iterations < maxIterations) {
    changed = false;
    iterations++;

    // 随机顺序处理节点
    const shuffledNodes = [...nodes].sort(() => Math.random() - 0.5);

    shuffledNodes.forEach((node) => {
      const neighbors = adjacencyList.get(node.id) || new Set();
      const neighborLabels = new Map<number, number>();

      neighbors.forEach((neighborId) => {
        const label = labels.get(neighborId) || 0;
        neighborLabels.set(label, (neighborLabels.get(label) || 0) + 1);
      });

      // 选择最常见的标签
      let maxCount = 0;
      let mostCommonLabel = labels.get(node.id) || 0;

      neighborLabels.forEach((count, label) => {
        if (count > maxCount) {
          maxCount = count;
          mostCommonLabel = label;
        }
      });

      if (labels.get(node.id) !== mostCommonLabel) {
        labels.set(node.id, mostCommonLabel);
        changed = true;
      }
    });
  }

  // 按标签分组
  const communities = new Map<number, { nodes: any[]; edges: any[] }>();

  nodes.forEach((node) => {
    const label = labels.get(node.id) || 0;
    if (!communities.has(label)) {
      communities.set(label, { nodes: [], edges: [] });
    }
    communities.get(label)!.nodes.push(node);
  });

  edges.forEach((edge) => {
    const sourceLabel = labels.get(edge.source) || 0;
    const targetLabel = labels.get(edge.target) || 0;

    if (sourceLabel === targetLabel) {
      const community = communities.get(sourceLabel);
      if (community) {
        community.edges.push(edge);
      }
    }
  });

  return Array.from(communities.values());
}


