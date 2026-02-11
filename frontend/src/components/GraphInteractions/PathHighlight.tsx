/**
 * 路径高亮组件
 * 高亮上下游路径和关键影响路径
 */
import { useState, useMemo } from 'react';
import { Button, Input, Select, Space, message } from 'antd';
import { HighlightOutlined } from '@ant-design/icons';
import { useTranslation } from 'react-i18next';
import type { GraphData, GraphNode } from '../../types';

interface PathHighlightProps {
  data: GraphData;
  onHighlight?: (paths: string[][]) => void;
  onClear?: () => void;
}

export default function PathHighlight({ data, onHighlight, onClear }: PathHighlightProps) {
  const { t } = useTranslation();
  const [sourceNode, setSourceNode] = useState<string>('');
  const [targetNode, setTargetNode] = useState<string>('');
  const [highlightMode, setHighlightMode] = useState<'upstream' | 'downstream' | 'path'>('path');

  const nodeOptions = useMemo(() => {
    return data.nodes.map((node) => ({
      label: node.label || node.id,
      value: node.id,
    }));
  }, [data.nodes]);

  const handleHighlight = () => {
    if (!sourceNode) {
      message.warning(t('pathHighlight.pleaseSelectSourceNode'));
      return;
    }

    let paths: string[][] = [];

    if (highlightMode === 'upstream') {
      paths = findUpstreamPaths(data, sourceNode);
    } else if (highlightMode === 'downstream') {
      paths = findDownstreamPaths(data, sourceNode);
    } else {
      if (!targetNode) {
        message.warning(t('pathHighlight.pleaseSelectTargetNode'));
        return;
      }
      paths = findPath(data, sourceNode, targetNode);
    }

    if (paths.length === 0) {
      message.info(t('pathHighlight.noPathFound'));
      return;
    }

    onHighlight?.(paths);
    message.success(t('pathHighlight.pathsFound', { count: paths.length }));
  };

  const handleClear = () => {
    setSourceNode('');
    setTargetNode('');
    onClear?.();
  };

  return (
    <Space size="small" style={{ flexShrink: 0 }}>
      <Select
        placeholder={t('pathHighlight.sourceNode')}
        value={sourceNode}
        onChange={setSourceNode}
        style={{ width: 150 }}
        size="small"
        showSearch
        options={nodeOptions}
      />
      {highlightMode === 'path' && (
        <Select
          placeholder={t('pathHighlight.targetNode')}
          value={targetNode}
          onChange={setTargetNode}
          style={{ width: 150 }}
          size="small"
          showSearch
          options={nodeOptions}
        />
      )}
      <Select
        value={highlightMode}
        onChange={setHighlightMode}
        style={{ width: 120 }}
        size="small"
      >
        <Select.Option value="upstream">{t('pathHighlight.upstreamPath')}</Select.Option>
        <Select.Option value="downstream">{t('pathHighlight.downstreamPath')}</Select.Option>
        <Select.Option value="path">{t('pathHighlight.shortestPath')}</Select.Option>
      </Select>
      <Button size="small" icon={<HighlightOutlined />} onClick={handleHighlight}>
        {t('pathHighlight.highlightPath')}
      </Button>
      <Button size="small" onClick={handleClear}>{t('pathHighlight.clear')}</Button>
    </Space>
  );
}

function findUpstreamPaths(data: GraphData, nodeId: string, maxDepth: number = 5): string[][] {
  const paths: string[][] = [];
  const visited = new Set<string>();

  const dfs = (current: string, path: string[], depth: number) => {
    if (depth > maxDepth || visited.has(current)) return;

    visited.add(current);
    const newPath = [...path, current];

    // 找到所有指向当前节点的边
    const incomingEdges = data.edges.filter((edge) => edge.target === current);

    if (incomingEdges.length === 0) {
      // 到达根节点
      paths.push(newPath);
    } else {
      incomingEdges.forEach((edge) => {
        dfs(edge.source, newPath, depth + 1);
      });
    }

    visited.delete(current);
  };

  dfs(nodeId, [], 0);
  return paths;
}

function findDownstreamPaths(data: GraphData, nodeId: string, maxDepth: number = 5): string[][] {
  const paths: string[][] = [];
  const visited = new Set<string>();

  const dfs = (current: string, path: string[], depth: number) => {
    if (depth > maxDepth || visited.has(current)) return;

    visited.add(current);
    const newPath = [...path, current];

    // 找到所有从当前节点出发的边
    const outgoingEdges = data.edges.filter((edge) => edge.source === current);

    if (outgoingEdges.length === 0) {
      // 到达叶子节点
      paths.push(newPath);
    } else {
      outgoingEdges.forEach((edge) => {
        dfs(edge.target, newPath, depth + 1);
      });
    }

    visited.delete(current);
  };

  dfs(nodeId, [], 0);
  return paths;
}

function findPath(data: GraphData, sourceId: string, targetId: string): string[][] {
  const paths: string[][] = [];
  const visited = new Set<string>();

  const dfs = (current: string, path: string[]) => {
    if (current === targetId) {
      paths.push([...path, current]);
      return;
    }

    if (visited.has(current)) return;

    visited.add(current);
    const newPath = [...path, current];

    const outgoingEdges = data.edges.filter((edge) => edge.source === current);
    outgoingEdges.forEach((edge) => {
      dfs(edge.target, newPath);
    });

    visited.delete(current);
  };

  dfs(sourceId, []);
  return paths.slice(0, 10); // 限制返回前10条路径
}


