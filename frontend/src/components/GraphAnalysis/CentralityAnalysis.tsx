/**
 * 中心性分析组件
 * 计算并可视化节点的中心性指标
 */
import { useMemo } from 'react';
import { Card, Table, Tag } from 'antd';
import type { GraphData, GraphNode } from '../../types';

interface CentralityAnalysisProps {
  data: GraphData;
  onNodeSelect?: (nodeId: string) => void;
}

export default function CentralityAnalysis({ data, onNodeSelect }: CentralityAnalysisProps) {
  const centralityData = useMemo(() => {
    return calculateCentrality(data);
  }, [data]);

  const columns = [
    {
      title: '节点',
      dataIndex: 'label',
      key: 'label',
      render: (text: string, record: any) => (
        <a onClick={() => onNodeSelect?.(record.id)}>{text}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag color="blue">{type}</Tag>,
    },
    {
      title: '度中心性',
      dataIndex: 'degree',
      key: 'degree',
      sorter: (a: any, b: any) => a.degree - b.degree,
      render: (value: number) => value.toFixed(2),
    },
    {
      title: '介数中心性',
      dataIndex: 'betweenness',
      key: 'betweenness',
      sorter: (a: any, b: any) => a.betweenness - b.betweenness,
      render: (value: number) => value.toFixed(2),
    },
    {
      title: '接近中心性',
      dataIndex: 'closeness',
      key: 'closeness',
      sorter: (a: any, b: any) => a.closeness - b.closeness,
      render: (value: number) => value.toFixed(2),
    },
  ];

  return (
    <Card title="中心性分析" size="small">
      <Table
        columns={columns}
        dataSource={centralityData}
        rowKey="id"
        pagination={{ pageSize: 10 }}
        size="small"
      />
    </Card>
  );
}

function calculateCentrality(data: GraphData) {
  const nodes = data.nodes;
  const edges = data.edges;

  // 构建邻接表
  const adjacencyList = new Map<string, Set<string>>();
  nodes.forEach((node) => {
    adjacencyList.set(node.id, new Set());
  });

  edges.forEach((edge) => {
    adjacencyList.get(edge.source)?.add(edge.target);
    adjacencyList.get(edge.target)?.add(edge.source);
  });

  // 计算度中心性
  const degreeCentrality = new Map<string, number>();
  nodes.forEach((node) => {
    const degree = adjacencyList.get(node.id)?.size || 0;
    degreeCentrality.set(node.id, degree / (nodes.length - 1));
  });

  // 计算介数中心性（简化版）
  const betweennessCentrality = new Map<string, number>();
  nodes.forEach((node) => {
    betweennessCentrality.set(node.id, 0);
  });

  // 计算所有节点对之间的最短路径
  nodes.forEach((source) => {
    const distances = new Map<string, number>();
    const paths = new Map<string, string[]>();
    const queue: string[] = [source.id];
    distances.set(source.id, 0);
    paths.set(source.id, [source.id]);

    while (queue.length > 0) {
      const current = queue.shift()!;
      const neighbors = adjacencyList.get(current) || new Set();

      neighbors.forEach((neighbor) => {
        if (!distances.has(neighbor)) {
          distances.set(neighbor, distances.get(current)! + 1);
          paths.set(neighbor, [...paths.get(current)!, neighbor]);
          queue.push(neighbor);
        }
      });
    }

    // 更新介数中心性
    nodes.forEach((target) => {
      if (target.id !== source.id && paths.has(target.id)) {
        const path = paths.get(target.id)!;
        path.slice(1, -1).forEach((nodeId) => {
          const current = betweennessCentrality.get(nodeId) || 0;
          betweennessCentrality.set(nodeId, current + 1);
        });
      }
    });
  });

  // 归一化介数中心性
  const maxBetweenness = Math.max(...Array.from(betweennessCentrality.values()));
  if (maxBetweenness > 0) {
    betweennessCentrality.forEach((value, key) => {
      betweennessCentrality.set(key, value / maxBetweenness);
    });
  }

  // 计算接近中心性
  const closenessCentrality = new Map<string, number>();
  nodes.forEach((node) => {
    const distances = new Map<string, number>();
    const queue: string[] = [node.id];
    distances.set(node.id, 0);

    while (queue.length > 0) {
      const current = queue.shift()!;
      const neighbors = adjacencyList.get(current) || new Set();

      neighbors.forEach((neighbor) => {
        if (!distances.has(neighbor)) {
          distances.set(neighbor, distances.get(current)! + 1);
          queue.push(neighbor);
        }
      });
    }

    const sumDistances = Array.from(distances.values()).reduce((a, b) => a + b, 0);
    const closeness = sumDistances > 0 ? (nodes.length - 1) / sumDistances : 0;
    closenessCentrality.set(node.id, closeness);
  });

  // 组合结果
  return nodes.map((node) => ({
    id: node.id,
    label: node.label || node.id,
    type: node.type,
    degree: degreeCentrality.get(node.id) || 0,
    betweenness: betweennessCentrality.get(node.id) || 0,
    closeness: closenessCentrality.get(node.id) || 0,
  }));
}


