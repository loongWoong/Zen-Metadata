/**
 * 时间轴布局组件
 * 按版本/变更时间展开，用于历史回溯与演进分析
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import * as d3 from 'd3';
import { Select, Space } from 'antd';
import type { GraphData, GraphNode, GraphEdge } from '../../types';

interface TemporalLayoutProps {
  data: GraphData;
  width?: number;
  height?: number;
  maxNodes?: number;
  maxEdges?: number;
  onNodeClick?: (node: GraphNode) => void;
  onNodeHover?: (node: GraphNode | null) => void;
}

type TimeField = 'collected_at' | 'created_at' | 'updated_at';

export default function TemporalLayout({
  data,
  width = 1000,
  height = 600,
  maxNodes,
  maxEdges,
  onNodeClick,
  onNodeHover,
}: TemporalLayoutProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const overviewRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width, height });
  const [timeField, setTimeField] = useState<TimeField>('created_at');
  const [viewBox, setViewBox] = useState({ x: 0, y: 0, width: 0, height: 0 });
  const [contentBounds, setContentBounds] = useState({ minY: 0, maxY: 0 });

  // 自适应大小
  const updateDimensions = useCallback(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setDimensions({
        width: rect.width || width,
        height: rect.height || height,
      });
    }
  }, [width, height]);

  useEffect(() => {
    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    
    // 使用 ResizeObserver 监听容器尺寸变化
    const resizeObserver = new ResizeObserver(() => {
      updateDimensions();
    });
    
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }
    
    return () => {
      window.removeEventListener('resize', updateDimensions);
      resizeObserver.disconnect();
    };
  }, [updateDimensions]);

  useEffect(() => {
    if (!svgRef.current || !data.nodes.length) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    // 设置SVG尺寸为容器尺寸
    const actualWidth = dimensions.width;
    const actualHeight = dimensions.height;
    
    // 应用限制配置（与力导向和层次布局保持一致的数据过滤逻辑）
    const nodeLimit = maxNodes || Infinity;
    const edgeLimit = maxEdges || Infinity;
    
    let displayNodes = data.nodes;
    let displayEdges = data.edges;
    
    // 第一步：限制节点数
    if (data.nodes.length > nodeLimit) {
      displayNodes = data.nodes.slice(0, nodeLimit);
      // 只保留与显示节点相关的边
      const nodeIdSet = new Set(displayNodes.map(n => String(n.id)));
      displayEdges = data.edges.filter(edge => {
        const sourceId = String(edge.source);
        const targetId = String(edge.target);
        return nodeIdSet.has(sourceId) && nodeIdSet.has(targetId);
      });
      
      if (import.meta.env.DEV) {
        console.warn(`时间轴布局数据已截断: 节点 ${data.nodes.length} -> ${displayNodes.length}, 边 ${data.edges.length} -> ${displayEdges.length}`);
      }
    }
    
    // 第二步：限制边数（在节点过滤后的基础上）
    if (displayEdges.length > edgeLimit) {
      displayEdges = displayEdges.slice(0, edgeLimit);
      // 只保留与显示边相关的节点
      const edgeNodeIds = new Set<string>();
      displayEdges.forEach(edge => {
        edgeNodeIds.add(String(edge.source));
        edgeNodeIds.add(String(edge.target));
      });
      displayNodes = displayNodes.filter(n => edgeNodeIds.has(String(n.id)));
      
      if (import.meta.env.DEV) {
        console.warn(`时间轴布局边数据已截断: ${displayEdges.length} 条边`);
      }
    }
    
    // 按时间分组节点
    const timeGroups = groupByTime(displayNodes, timeField);
    const groupCount = Math.max(timeGroups.length, 1);
    const groupWidth = Math.max((actualWidth - 200) / groupCount, 150); // 最小宽度150px

    // 计算所有节点的总高度（移除显示限制，显示所有节点）
    const minNodeSpacing = 60; // 最小节点间距
    let totalContentHeight = 0;
    const groupHeights: number[] = [];
    
    timeGroups.forEach((group) => {
      const groupHeight = Math.max(100, group.nodes.length * minNodeSpacing);
      groupHeights.push(groupHeight);
      totalContentHeight = Math.max(totalContentHeight, groupHeight);
    });
    
    // 设置SVG的实际高度为内容高度，但至少为容器高度
    const svgHeight = Math.max(actualHeight, totalContentHeight + 100);
    svg.attr('width', actualWidth).attr('height', svgHeight);

    const g = svg.append('g');

    // 创建缩放和平移
    let currentTransform = d3.zoomIdentity;
    
    // 更新鹰眼视图函数（需要在 zoom 定义之前声明）
    const updateOverview = () => {
      if (!overviewRef.current || nodePositions.size === 0) return;
      
      const overviewSvg = d3.select(overviewRef.current);
      overviewSvg.selectAll('*').remove();
      
      const overviewWidth = 200;
      const overviewHeight = 150;
      const scaleX = overviewWidth / actualWidth;
      const scaleY = overviewHeight / svgHeight;
      
      // 绘制缩略图背景
      overviewSvg
        .append('rect')
        .attr('width', overviewWidth)
        .attr('height', overviewHeight)
        .attr('fill', '#f5f5f5')
        .attr('stroke', '#d9d9d9');
      
      // 绘制所有节点（简化版）
      const overviewG = overviewSvg.append('g');
      nodePositions.forEach((pos) => {
        overviewG
          .append('circle')
          .attr('cx', pos.x * scaleX)
          .attr('cy', pos.y * scaleY)
          .attr('r', 1.5)
          .attr('fill', '#1890ff')
          .attr('opacity', 0.6);
      });
      
      // 计算当前视图框在鹰眼中的位置和尺寸
      const viewBoxWidth = (actualWidth / currentTransform.k) * scaleX;
      const viewBoxHeight = (actualHeight / currentTransform.k) * scaleY;
      
      // 计算视图框在鹰眼中的位置
      let viewBoxX = -currentTransform.x * scaleX;
      let viewBoxY = -currentTransform.y * scaleY;
      
      // 确保视图框不超出鹰眼边界
      viewBoxX = Math.max(0, Math.min(viewBoxX, overviewWidth - viewBoxWidth));
      viewBoxY = Math.max(0, Math.min(viewBoxY, overviewHeight - viewBoxHeight));
      
      // 确保宽度和高度都是正值
      const finalWidth = Math.max(0, Math.min(viewBoxWidth, overviewWidth - viewBoxX));
      const finalHeight = Math.max(0, Math.min(viewBoxHeight, overviewHeight - viewBoxY));
      
      // 只有当视图框有效时才绘制
      if (finalWidth > 0 && finalHeight > 0) {
        const viewBoxRect = overviewG
          .append('rect')
          .attr('x', viewBoxX)
          .attr('y', viewBoxY)
          .attr('width', finalWidth)
          .attr('height', finalHeight)
          .attr('fill', 'rgba(255, 77, 79, 0.2)')
          .attr('stroke', '#ff4d4f')
          .attr('stroke-width', 2)
          .style('cursor', 'move');
        
        // 添加拖动功能来移动视图
        let dragStartX = 0;
        let dragStartY = 0;
        let dragStartTransform = currentTransform;
        
        viewBoxRect.call(
          d3.drag<SVGRectElement, unknown>()
            .on('start', (event) => {
              // 记录拖动开始时的位置和变换
              const point = d3.pointer(event, overviewRef.current);
              dragStartX = point[0];
              dragStartY = point[1];
              dragStartTransform = currentTransform;
            })
            .on('drag', (event) => {
              // 计算拖动距离（在鹰眼坐标系中）
              const point = d3.pointer(event, overviewRef.current);
              const deltaX = point[0] - dragStartX;
              const deltaY = point[1] - dragStartY;
              
              // 将拖动距离转换为主视图的平移量
              const deltaMainX = -deltaX / scaleX;
              const deltaMainY = -deltaY / scaleY;
              
              // 计算新的变换
              const newTransform = d3.zoomIdentity
                .translate(
                  dragStartTransform.x + deltaMainX,
                  dragStartTransform.y + deltaMainY
                )
                .scale(dragStartTransform.k);
              
              // 应用新变换
              svg.call(zoom.transform, newTransform);
            })
        );
      }
    };
    
    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        currentTransform = event.transform;
        g.attr('transform', event.transform);
        updateOverview();
      });

    svg.call(zoom);

    // 存储节点位置信息，用于绘制边和鹰眼
    const nodePositions = new Map<string, { x: number; y: number }>();

    // 绘制时间轴和所有节点（不再限制显示）
    timeGroups.forEach((group, i) => {
      const x = 100 + i * groupWidth + groupWidth / 2;
      const groupHeight = groupHeights[i];
      const startY = 50;
      const nodeSpacing = Math.max(minNodeSpacing, groupHeight / Math.max(group.nodes.length, 1));

      // 绘制时间标签线（延伸到整个内容高度）
      g.append('line')
        .attr('x1', x)
        .attr('y1', 20)
        .attr('x2', x)
        .attr('y2', svgHeight - 20)
        .attr('stroke', '#d9d9d9')
        .attr('stroke-width', 1)
        .attr('stroke-dasharray', '5,5');

      g.append('text')
        .attr('x', x)
        .attr('y', 15)
        .attr('text-anchor', 'middle')
        .attr('font-size', '12px')
        .attr('fill', '#666')
        .attr('font-weight', 'bold')
        .text(group.timeLabel);

      // 绘制该时间段的所有节点（不再限制显示）
      group.nodes.forEach((node, j) => {
        const nodeY = startY + j * nodeSpacing;
        nodePositions.set(node.id, { x, y: nodeY });
        
        const nodeG = g
          .append('g')
          .attr('class', 'node')
          .attr('transform', `translate(${x},${nodeY})`)
          .style('cursor', 'pointer')
          .on('click', () => onNodeClick?.(node))
          .on('mouseenter', (event) => {
            d3.select(event.currentTarget)
              .select('circle')
              .attr('r', 10)
              .attr('stroke-width', 3);
            onNodeHover?.(node);
          })
          .on('mouseleave', (event) => {
            d3.select(event.currentTarget)
              .select('circle')
              .attr('r', 8)
              .attr('stroke-width', 2);
            onNodeHover?.(null);
          });

        nodeG
          .append('circle')
          .attr('r', 8)
          .attr('fill', '#1890ff')
          .attr('stroke', '#fff')
          .attr('stroke-width', 2);

        // 节点文本，使用背景矩形防止重叠
        const textGroup = nodeG
          .append('g')
          .attr('class', 'text-group');

        const text = node.label || node.id;
        const textWidth = Math.min(text.length * 6 + 8, 120);

        textGroup
          .append('rect')
          .attr('x', 12)
          .attr('y', -8)
          .attr('width', textWidth)
          .attr('height', 16)
          .attr('fill', 'rgba(255, 255, 255, 0.9)')
          .attr('stroke', '#d9d9d9')
          .attr('stroke-width', 1)
          .attr('rx', 2);

        textGroup
          .append('text')
          .attr('dx', 16)
          .attr('dy', 5)
          .text(text.length > 18 ? text.substring(0, 18) + '...' : text)
          .attr('font-size', '11px')
          .attr('fill', '#333')
          .attr('pointer-events', 'none');
      });
    });

    // 绘制边（连接不同时间段的节点）
    displayEdges.forEach((edge) => {
      const sourcePos = nodePositions.get(String(edge.source));
      const targetPos = nodePositions.get(String(edge.target));

      if (!sourcePos || !targetPos) return;

      g.append('line')
        .attr('x1', sourcePos.x)
        .attr('y1', sourcePos.y)
        .attr('x2', targetPos.x)
        .attr('y2', targetPos.y)
        .attr('stroke', '#999')
        .attr('stroke-width', 1)
        .attr('stroke-opacity', 0.5)
        .attr('marker-end', 'url(#arrowhead)');
    });

    // 创建箭头标记
    const defs = svg.append('defs');
    defs
      .append('marker')
      .attr('id', 'arrowhead')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 8)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', '#999');

    // 更新内容边界
    setContentBounds({ minY: 0, maxY: svgHeight });
    
    // 更新视图框
    setViewBox({ x: 0, y: 0, width: actualWidth, height: actualHeight });
    
    // 初始更新鹰眼（延迟一下确保DOM已渲染）
    setTimeout(() => {
      updateOverview();
    }, 100);
  }, [data, dimensions, timeField, maxNodes, maxEdges, onNodeClick, onNodeHover]);

  return (
    <div ref={containerRef} style={{ width: '100%', height: '100%', position: 'relative', overflow: 'hidden' }}>
      {/* 时间字段选择器 */}
      <div style={{ 
        position: 'absolute', 
        top: 8, 
        right: 8, 
        zIndex: 10,
        background: 'rgba(255, 255, 255, 0.9)',
        padding: '4px 8px',
        borderRadius: '4px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
      }}>
        <Space size="small">
          <span style={{ fontSize: '12px', color: '#666' }}>时间字段:</span>
          <Select
            value={timeField}
            onChange={setTimeField}
            size="small"
            style={{ width: 120 }}
          >
            <Select.Option value="created_at">创建时间</Select.Option>
            <Select.Option value="collected_at">采集时间</Select.Option>
            <Select.Option value="updated_at">更新时间</Select.Option>
          </Select>
        </Space>
      </div>
      
      {/* 主SVG - 使用d3.zoom处理缩放和平移，内容超出时自动滚动 */}
      <div style={{ 
        width: '100%', 
        height: '100%', 
        overflow: 'auto',
        position: 'relative'
      }}>
        <svg 
          ref={svgRef} 
          width={dimensions.width} 
          height={Math.max(dimensions.height, contentBounds.maxY)} 
          style={{ 
            border: '1px solid #d9d9d9',
            display: 'block'
          }} 
        />
      </div>
      
      {/* 鹰眼视图（预览区域控制） */}
      {contentBounds.maxY > dimensions.height && (
        <div style={{
          position: 'absolute',
          bottom: 8,
          right: 8,
          zIndex: 10,
          background: 'rgba(255, 255, 255, 0.95)',
          padding: '8px',
          borderRadius: '4px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
          border: '1px solid #d9d9d9'
        }}>
          <div style={{ fontSize: '11px', color: '#666', marginBottom: '4px', fontWeight: 'bold' }}>
            鹰眼视图
          </div>
          <svg
            ref={overviewRef}
            width={200}
            height={150}
            style={{ display: 'block', border: '1px solid #e8e8e8', borderRadius: '2px' }}
          />
        </div>
      )}
    </div>
  );
}

function groupByTime(nodes: GraphNode[], timeField: TimeField = 'created_at'): Array<{ timeLabel: string; nodes: GraphNode[]; timeValue: number }> {
  // 按指定时间字段分组
  const groups = new Map<string, { nodes: GraphNode[]; timeValue: number }>();

  nodes.forEach((node) => {
    // 优先使用指定的时间字段，如果不存在则尝试其他字段
    let time: string | undefined;
    if (timeField === 'collected_at') {
      time = node.collected_at || node.properties?.collected_at;
    } else if (timeField === 'created_at') {
      // 优先使用properties中的created_at（文件创建时间），否则使用节点的created_at
      time = node.properties?.created_at || node.created_at;
    } else if (timeField === 'updated_at') {
      time = node.updated_at || node.properties?.modified_at;
    }
    
    // 如果仍然没有时间，尝试从properties中查找
    if (!time && node.properties) {
      time = node.properties.created_at || node.properties.collected_at || node.properties.modified_at;
    }
    
    // 如果还是没有，使用unknown
    if (!time) {
      time = 'unknown';
    }
    
    let timeLabel: string;
    let timeValue: number;
    
    if (time === 'unknown') {
      timeLabel = 'Unknown';
      timeValue = 0;
    } else {
      try {
        const date = new Date(time);
        if (isNaN(date.getTime())) {
          timeLabel = 'Invalid Date';
          timeValue = 0;
        } else {
          // 按日期分组（忽略时间部分）
          timeLabel = date.toLocaleDateString('zh-CN', { 
            year: 'numeric', 
            month: '2-digit', 
            day: '2-digit' 
          });
          timeValue = date.getTime();
        }
      } catch (e) {
        timeLabel = 'Invalid Date';
        timeValue = 0;
      }
    }
    
    if (!groups.has(timeLabel)) {
      groups.set(timeLabel, { nodes: [], timeValue });
    }
    groups.get(timeLabel)!.nodes.push(node);
  });

  return Array.from(groups.entries())
    .map(([timeLabel, { nodes, timeValue }]) => ({ timeLabel, nodes, timeValue }))
    .sort((a, b) => {
      if (a.timeLabel === 'Unknown' || a.timeLabel === 'Invalid Date') return 1;
      if (b.timeLabel === 'Unknown' || b.timeLabel === 'Invalid Date') return -1;
      return a.timeValue - b.timeValue;
    });
}


